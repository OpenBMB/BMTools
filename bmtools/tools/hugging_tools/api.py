from ast import List
from asyncio import Queue
import io
import json
import os
import random
import threading
from langchain import LLMChain, OpenAI, PromptTemplate
import requests
from ..tool import Tool
from huggingface_hub.inference_api import InferenceApi
import base64
from io import BytesIO
import os
import random
import traceback
import uuid
import requests
from PIL import Image, ImageDraw
from diffusers.utils import load_image
from pydub import AudioSegment
from huggingface_hub.inference_api import InferenceApi
from huggingface_hub.inference_api import ALL_TASKS
import logging
# from langchain.prompts import PromptTemplate
# from langchain.chains import LLMChain
# from langchain.llms import OpenAI


# ENDPOINT	MODEL NAME	
# /v1/chat/completions	gpt-4, gpt-4-0314, gpt-4-32k, gpt-4-32k-0314, gpt-3.5-turbo, gpt-3.5-turbo-0301	
# /v1/completions	text-davinci-003, text-davinci-002, text-curie-001, text-babbage-001, text-ada-001, davinci, curie, babbage, ada

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
parse_task = '''The chat log [ {{context}} ] may contain the resources I mentioned. Now I input { {{input}} }. Pay attention to the input and output types of tasks and the dependencies between tasks.'''
choose_model = '''Please choose the most suitable model from {{metas}} for the task {{task}}. The output must be in a strict JSON format: {"id": "id", "reason": "your detail reasons for the choice"}.'''
response_results = '''Yes. Please first think carefully and directly answer my request based on the inference results. Some of the inferences may not always turn out to be correct and require you to make careful consideration in making decisions. Then please detail your workflow including the used models and inference results for my request in your friendly tone. Please filter out information that is not relevant to my request. Tell me the complete path or urls of files in inference results. If there is nothing in the results, please tell me you can't make it. }'''
config = {
    "debug": False,
    "log_file": None,
    "huggingface": {
        "token":os.environ.get("HUGGINGFACE_API_KEY")
    },
    "proxy": None,
    "inference_mode": "huggingface",
    "local_inference_endpoint": {
        "host": "localhost",
        "port": 8005
    },
    "huggingface_inference_endpoint": {
        "host": "api-inference.huggingface.co",
        "port": 443
    },
}

if not config["debug"]:
    handler.setLevel(logging.CRITICAL)
logger.addHandler(handler)

log_file = config["log_file"]
if log_file:
    filehandler = logging.FileHandler(log_file)
    filehandler.setLevel(logging.DEBUG)
    filehandler.setFormatter(formatter)
    logger.addHandler(filehandler)

HUGGINGFACE_HEADERS = {}
if config["huggingface"]["token"] and config["huggingface"]["token"].startswith("hf_"):  # Check for valid huggingface token in config file
    HUGGINGFACE_HEADERS = {
        "Authorization": f"Bearer {config['huggingface']['token']}",
    }
elif "HUGGINGFACE_ACCESS_TOKEN" in os.environ and os.getenv("HUGGINGFACE_API_KEY").startswith("hf_"):  # Check for environment variable HUGGINGFACE_ACCESS_TOKEN
    HUGGINGFACE_HEADERS = {
        "Authorization": f"Bearer {os.getenv('HUGGINGFACE_API_KEY')}",
    }
else:
    raise ValueError(f"Incrorrect HuggingFace token. Please check your file.")

PROXY = None
if config["proxy"]:
    PROXY = {
        "https": config["proxy"],
    }

inference_mode = config["inference_mode"]

MODELS = [json.loads(line) for line in open("data/p0_models.jsonl", "r").readlines()]
MODELS_MAP = {}
for model in MODELS:
    tag = model["task"]
    if tag not in MODELS_MAP:
        MODELS_MAP[tag] = []
    MODELS_MAP[tag].append(model)

# check the local_inference_endpoint
Model_Server = None
if inference_mode!="huggingface":
    Model_Server = "http://" + config["local_inference_endpoint"]["host"] + ":" + str(config["local_inference_endpoint"]["port"])
    message = f"The server of local inference endpoints is not running, please start it first. (or using `inference_mode: huggingface` in for a feature-limited experience)"
    try:
        r = requests.get(Model_Server + "/running")
        if r.status_code != 200:
            raise ValueError(message)
    except:
        raise ValueError(message)


def get_model_status(model_id, url, headers, queue = None):
    endpoint_type = "huggingface" if "huggingface" in url else "local"
    if "huggingface" in url:
        r = requests.get(url, headers=headers, proxies=PROXY)
    else:
        r = requests.get(url)
    if r.status_code == 200 and "loaded" in r.json() and r.json()["loaded"]:
        if queue:
            queue.put((model_id, True, endpoint_type))
        return True
    else:
        if queue:
            queue.put((model_id, False, None))
        return False


def get_avaliable_models(candidates, topk=5):
    all_available_models = {"local": [], "huggingface": []}
    threads = []
    result_queue = Queue()

    for candidate in candidates:
        model_id = candidate

        if inference_mode != "local":
            huggingfaceStatusUrl = f"https://api-inference.huggingface.co/status/{model_id}"
            thread = threading.Thread(target=get_model_status, args=(model_id, huggingfaceStatusUrl, HUGGINGFACE_HEADERS, result_queue))
            threads.append(thread)
            thread.start()
        
        if inference_mode != "huggingface" and config["local_deployment"] != "minimal":
            localStatusUrl = f"{Model_Server}/status/{model_id}"
            thread = threading.Thread(target=get_model_status, args=(model_id, localStatusUrl, {}, result_queue))
            threads.append(thread)
            thread.start()
        
    result_count = len(threads)
    while result_count:
        model_id, status, endpoint_type = result_queue.get()
        if status and model_id not in all_available_models:
            all_available_models[endpoint_type].append(model_id)
        if len(all_available_models["local"] + all_available_models["huggingface"]) >= topk:
            break
        result_count -= 1

    for thread in threads:
        thread.join()

    return all_available_models


def image_to_bytes(img_url):
    img_byte = io.BytesIO()
    type = img_url.split(".")[-1]
    load_image(img_url).save(img_byte, format="png")
    img_data = img_byte.getvalue()
    return img_data

def build_tool(config) -> Tool:
    tool = Tool(
        tool_name="hugging_tools",
        description="API interface for HuggingGPT-like applications.",
        name_for_model="hugging_tools",
        description_for_model="API Interface for models on Huggingface hub.",
        logo_url="https://your-app-url.com/.well-known/logo.png",
        contact_email="test@123.com",
        legal_info_url="hello@legal.com"
    )
    # key = os.environ.get("OPENAI_API_KEY")
    # llm = OpenAI(model_name="gpt-3.5-turbo", temperature=0.0, openai_api_key=key)
    @tool.get("/get_models_available")
    def get_models_available(candidates: List[str], top_number: int) -> str:
        return get_avaliable_models(candidates, top_number)
    def huggingface_model_inference(model_id, data, task) -> str:
        task_url = f"https://api-inference.huggingface.co/models/{model_id}" # InferenceApi does not yet support some tasks
        inference = InferenceApi(repo_id=model_id, token=config["huggingface"]["token"])
        
        # NLP tasks
        if task == "question-answering":
            inputs = {"question": data["text"], "context": (data["context"] if "context" in data else "" )}
            result = inference(inputs)
        if task == "sentence-similarity":
            inputs = {"source_sentence": data["text1"], "target_sentence": data["text2"]}
            result = inference(inputs)
        if task in ["text-classification",  "token-classification", "text2text-generation", "summarization", "translation", "conversational", "text-generation"]:
            inputs = data["text"]
            result = inference(inputs)
        
        # CV tasks
        if task == "visual-question-answering" or task == "document-question-answering":
            img_url = data["image"]
            text = data["text"]
            img_data = image_to_bytes(img_url)
            img_base64 = base64.b64encode(img_data).decode("utf-8")
            json_data = {}
            json_data["inputs"] = {}
            json_data["inputs"]["question"] = text
            json_data["inputs"]["image"] = img_base64
            result = requests.post(task_url, headers=HUGGINGFACE_HEADERS, json=json_data).json()
            # result = inference(inputs) # not support

        if task == "image-to-image":
            img_url = data["image"]
            img_data = image_to_bytes(img_url)
            # result = inference(data=img_data) # not support
            HUGGINGFACE_HEADERS["Content-Length"] = str(len(img_data))
            r = requests.post(task_url, headers=HUGGINGFACE_HEADERS, data=img_data)
            result = r.json()
            if "path" in result:
                result["generated image"] = result.pop("path")
        
        if task == "text-to-image":
            inputs = data["text"]
            img = inference(inputs)
            name = str(uuid.uuid4())[:4]
            img.save(f"public/images/{name}.png")
            result = {}
            result["generated image"] = f"/images/{name}.png"

        if task == "image-segmentation":
            img_url = data["image"]
            img_data = image_to_bytes(img_url)
            image = Image.open(BytesIO(img_data))
            predicted = inference(data=img_data)
            colors = []
            for i in range(len(predicted)):
                colors.append((random.randint(100, 255), random.randint(100, 255), random.randint(100, 255), 155))
            for i, pred in enumerate(predicted):
                label = pred["label"]
                mask = pred.pop("mask").encode("utf-8")
                mask = base64.b64decode(mask)
                mask = Image.open(BytesIO(mask), mode='r')
                mask = mask.convert('L')

                layer = Image.new('RGBA', mask.size, colors[i])
                image.paste(layer, (0, 0), mask)
            name = str(uuid.uuid4())[:4]
            image.save(f"public/images/{name}.jpg")
            result = {}
            result["generated image"] = f"/images/{name}.jpg"
            result["predicted"] = predicted

        if task == "object-detection":
            img_url = data["image"]
            img_data = image_to_bytes(img_url)
            predicted = inference(data=img_data)
            image = Image.open(BytesIO(img_data))
            draw = ImageDraw.Draw(image)
            labels = list(item['label'] for item in predicted)
            color_map = {}
            for label in labels:
                if label not in color_map:
                    color_map[label] = (random.randint(0, 255), random.randint(0, 100), random.randint(0, 255))
            for label in predicted:
                box = label["box"]
                draw.rectangle(((box["xmin"], box["ymin"]), (box["xmax"], box["ymax"])), outline=color_map[label["label"]], width=2)
                draw.text((box["xmin"]+5, box["ymin"]-15), label["label"], fill=color_map[label["label"]])
            name = str(uuid.uuid4())[:4]
            image.save(f"public/images/{name}.jpg")
            result = {}
            result["generated image"] = f"/images/{name}.jpg"
            result["predicted"] = predicted

        if task in ["image-classification"]:
            img_url = data["image"]
            img_data = image_to_bytes(img_url)
            result = inference(data=img_data)
    
        if task == "image-to-text":
            img_url = data["image"]
            img_data = image_to_bytes(img_url)
            HUGGINGFACE_HEADERS["Content-Length"] = str(len(img_data))
            r = requests.post(task_url, headers=HUGGINGFACE_HEADERS, data=img_data, proxies=PROXY)
            result = {}
            if "generated_text" in r.json()[0]:
                result["generated text"] = r.json()[0].pop("generated_text")
        
        # AUDIO tasks
        if task == "text-to-speech":
            inputs = data["text"]
            response = inference(inputs, raw_response=True)
            # response = requests.post(task_url, headers=HUGGINGFACE_HEADERS, json={"inputs": text})
            name = str(uuid.uuid4())[:4]
            with open(f"public/audios/{name}.flac", "wb") as f:
                f.write(response.content)
            result = {"generated audio": f"/audios/{name}.flac"}
        if task in ["automatic-speech-recognition", "audio-to-audio", "audio-classification"]:
            audio_url = data["audio"]
            audio_data = requests.get(audio_url, timeout=10).content
            response = inference(data=audio_data, raw_response=True)
            result = response.json()
            if task == "audio-to-audio":
                content = None
                type = None
                for k, v in result[0].items():
                    if k == "blob":
                        content = base64.b64decode(v.encode("utf-8"))
                    if k == "content-type":
                        type = "audio/flac".split("/")[-1]
                audio = AudioSegment.from_file(BytesIO(content))
                name = str(uuid.uuid4())[:4]
                audio.export(f"public/audios/{name}.{type}", format=type)
                result = {"generated audio": f"/audios/{name}.{type}"}
            return result
    '''
    if task == "question-answering":
    inputs = {"question": data["text"], "context": (data["context"] if "context" in data else "" )}
    result = inference(inputs)
    '''
    @tool.get("/question-answering")
    def question_answering(model_id: str, text: str, context: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["hugging"]["token"])
        return inference({"text": text, "context" : (context if context else "")})

    '''
    inputs = {"source_sentence": data["text1"], "target_sentence": data["text2"]}
    result = inference(inputs)
    '''       
    @tool.get("/sentence-similarity")
    def sentence_similarity(model_id: str, text: str, context: str) -> str:
        
        inference = InferenceApi(repo_id=model_id, token=config["hugging"]["token"])
        return inference({"source_sentence": text, "target_sentence" : (context if context else "")})
    @tool.get("/text-classification")
    def text_classification(model_id: str, text: str) -> str:
        
        inference = InferenceApi(repo_id=model_id, token=config["hugging"]["token"])
        return inference(text)
    '''
    if task in ["text-classification",  "token-classification", "text2text-generation", "summarization", "translation", "conversational", "text-generation"]:
            inputs = data["text"]
            result = inference(inputs)
    '''
    @tool.get("/token-classification")
    def token_classification(model_id: str, text: str) -> str:
        
        inference = InferenceApi(repo_id=model_id, token=config["hugging"]["token"])
        return inference(text)
    @tool.get("/text2text-generation")
    def text2text_generation(model_id: str,text: str) -> str:
        
        inference = InferenceApi(repo_id=model_id, token=config["hugging"]["token"])
        return inference(text)
    @tool.get("/summarization")
    def summarization(model_id: str, text: str) -> str:
        
        inference = InferenceApi(repo_id=model_id, token=config["hugging"]["token"])
        return inference(text)
    @tool.get("/translation")
    def translation(model_id: str, text: str) -> str:
        
        inference = InferenceApi(repo_id=model_id, token=config["hugging"]["token"])
        return inference(text)
    @tool.get("/conversational")
    def conversational(model_id: str, text: str) -> str:
        
        inference = InferenceApi(repo_id=model_id, token=config["hugging"]["token"])
        return inference(text)
    @tool.get("/text-generation")
    def text_generation(model_id: str, text: str) -> str:
        
        inference = InferenceApi(repo_id=model_id, token=config["hugging"]["token"])
        return inference(text)
    # CV tasks
    '''
            if task == "visual-question-answering" or task == "document-question-answering":
            img_url = data["image"]
            text = data["text"]
            img_data = image_to_bytes(img_url)
            img_base64 = base64.b64encode(img_data).decode("utf-8")
            json_data = {}
            json_data["inputs"] = {}
            json_data["inputs"]["question"] = text
            json_data["inputs"]["image"] = img_base64
            result = requests.post(task_url, headers=HUGGINGFACE_HEADERS, json=json_data).json()
            # result = inference(inputs) # not support
    '''
    @tool.get("/visual-question-answering")
    def visual_question_answering(model_id: str, image: str, text: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["hugging"]["token"])
        img_data = image_to_bytes(image)
        img_base64 = base64.b64encode(img_data).decode("utf-8")
        return inference({"question": text, "image": img_base64})
    @tool.get("/document-question-answering")
    def document_question_answering(model_id: str, image: str, text: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["hugging"]["token"])
        img_data = image_to_bytes(image)
        img_base64 = base64.b64encode(img_data).decode("utf-8")
        return inference({"question": text, "image": img_base64})
    '''
    
        if task == "image-to-image":
            img_url = data["image"]
            img_data = image_to_bytes(img_url)
            HUGGINGFACE_HEADERS["Content-Length"] = str(len(img_data))
            r = requests.post(task_url, headers=HUGGINGFACE_HEADERS, data=img_data)
            result = r.json()
            if "path" in result:
                result["generated image"] = result.pop("path")
    '''
    @tool.get("/image-to-image")
    def image_to_image(model_id: str, image: str) -> str:
        task_url = f"https://api-inference.huggingface.co/models/{model_id}" # InferenceApi does not yet support some tasks
        image_data = image_to_bytes(image)
        HUGGINGFACE_HEADERS["Content-Length"] = str(len(image_data))
        r = requests.post(task_url, headers=HUGGINGFACE_HEADERS, data=image_data)
        result = r.json()
        if "path" in result:
            result["generated image"] = result.pop("path")
        return result
    '''
    if task == "text-to-image":
        inputs = data["text"]
        img = inference(inputs)
        name = str(uuid.uuid4())[:4]
        img.save(f"public/images/{name}.png")
        result = {}
        result["generated image"] = f"/images/{name}.png"
    '''
    @tool.get("/text-to-image")
    def text_to_image(model_id: str, text: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["hugging"]["token"])
        img = inference(text)
        name = str(uuid.uuid4())[:4]
        img.save(f"public/images/{name}.png")
        result = {}
        result["generated image"] = f"/images/{name}.png"
        return result
    '''
    if task == "image-segmentation":
        img_url = data["image"]
        img_data = image_to_bytes(img_url)
        image = Image.open(BytesIO(img_data))
        predicted = inference(data=img_data)
        colors = []
        for i in range(len(predicted)):
            colors.append((random.randint(100, 255), random.randint(100, 255), random.randint(100, 255), 155))
        for i, pred in enumerate(predicted):
            label = pred["label"]
            mask = pred.pop("mask").encode("utf-8")
            mask = base64.b64decode(mask)
            mask = Image.open(BytesIO(mask), mode='r')
            mask = mask.convert('L')

            layer = Image.new('RGBA', mask.size, colors[i])
            image.paste(layer, (0, 0), mask)
        name = str(uuid.uuid4())[:4]
        image.save(f"public/images/{name}.jpg")
        result = {}
        result["generated image"] = f"/images/{name}.jpg"
        result["predicted"] = predicted
    '''
    @tool.get("/image-segmentation")
    def image_segmentation(model_id: str, image: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["hugging"]["token"])
        img_data = image_to_bytes(image)
        image = Image.open(BytesIO(img_data))
        predicted = inference(data=img_data)
        colors = []
        for i in range(len(predicted)):
            colors.append((random.randint(100, 255), random.randint(100, 255), random.randint(100, 255), 155))
        for i, pred in enumerate(predicted):
            label = pred["label"]
            mask = pred.pop("mask").encode("utf-8")
            mask = base64.b64decode(mask)
            mask = Image.open(BytesIO(mask), mode='r')
            mask = mask.convert('L')

            layer = Image.new('RGBA', mask.size, colors[i])
            image.paste(layer, (0, 0), mask)
        name = str(uuid.uuid4())[:4]
        image.save(f"public/images/{name}.jpg")
        result = {}
        result["generated image"] = f"/images/{name}.jpg"
        result["predicted"] = predicted
        return result
    '''
    if task == "object-detection":
        img_url = data["image"]
        img_data = image_to_bytes(img_url)
        predicted = inference(data=img_data)
        image = Image.open(BytesIO(img_data))
        draw = ImageDraw.Draw(image)
        labels = list(item['label'] for item in predicted)
        color_map = {}
        for label in labels:
            if label not in color_map:
                color_map[label] = (random.randint(0, 255), random.randint(0, 100), random.randint(0, 255))
        for label in predicted:
            box = label["box"]
            draw.rectangle(((box["xmin"], box["ymin"]), (box["xmax"], box["ymax"])), outline=color_map[label["label"]], width=2)
            draw.text((box["xmin"]+5, box["ymin"]-15), label["label"], fill=color_map[label["label"]])
        name = str(uuid.uuid4())[:4]
        image.save(f"public/images/{name}.jpg")
        result = {}
        result["generated image"] = f"/images/{name}.jpg"
        result["predicted"] = predicted
    '''
    @tool.get("/object-detection")
    def object_detection(model_id: str, image: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["hugging"]["token"])
        img_data = image_to_bytes(image)
        predicted = inference(data=img_data)
        image = Image.open(BytesIO(img_data))
        draw = ImageDraw.Draw(image)
        labels = list(item['label'] for item in predicted)
        color_map = {}
        for label in labels:
            if label not in color_map:
                color_map[label] = (random.randint(0, 255), random.randint(0, 100), random.randint(0, 255))
        for label in predicted:
            box = label["box"]
            draw.rectangle(((box["xmin"], box["ymin"]), (box["xmax"], box["ymax"])), outline=color_map[label["label"]], width=2)
            draw.text((box["xmin"]+5, box["ymin"]-15), label["label"], fill=color_map[label["label"]])
        name = str(uuid.uuid4())[:4]
        image.save(f"public/images/{name}.jpg")
        result = {}
        result["generated image"] = f"/images/{name}.jpg"
        result["predicted"] = predicted
        return result
    '''
    if task in ["image-classification"]:
        img_url = data["image"]
        img_data = image_to_bytes(img_url)
        result = inference(data=img_data)
    '''
    @tool.get("/image-classification")
    def image_classification(model_id: str, image: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["hugging"]["token"])
        img_data = image_to_bytes(image)
        result = inference(data=img_data)
        return result
    '''
    
        if task == "image-to-text":
            img_url = data["image"]
            img_data = image_to_bytes(img_url)
            HUGGINGFACE_HEADERS["Content-Length"] = str(len(img_data))
            r = requests.post(task_url, headers=HUGGINGFACE_HEADERS, data=img_data, proxies=PROXY)
            result = {}
            if "generated_text" in r.json()[0]:
                result["generated text"] = r.json()[0].pop("generated_text")
     '''
    @tool.get("/image-to-text")
    def image_to_text(model_id: str, image: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["hugging"]["token"])
        img_data = image_to_bytes(image)
        result = inference(data=img_data)
        return result
    # AUDIO tasks
    '''
    if task == "text-to-speech":
        inputs = data["text"]
        response = inference(inputs, raw_response=True)
        # response = requests.post(task_url, headers=HUGGINGFACE_HEADERS, json={"inputs": text})
        name = str(uuid.uuid4())[:4]
        with open(f"public/audios/{name}.flac", "wb") as f:
            f.write(response.content)
    '''
    @tool.get("/text-to-speech")
    def text_to_speech(model_id: str, text: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["hugging"]["token"])
        response = inference(text, raw_response=True)
        name = str(uuid.uuid4())[:4]
        with open(f"public/audios/{name}.flac", "wb") as f:
            f.write(response.content)
        result = {}
        result["generated audio"] = f"/audios/{name}.flac"
        return result
    '''
    if task in ["automatic-speech-recognition", "audio-to-audio", "audio-classification"]:
        audio_url = data["audio"]
        audio_data = requests.get(audio_url, timeout=10).content
        response = inference(data=audio_data, raw_response=True)
        result = response.json()
        if task == "audio-to-audio":
            content = None
            type = None
            for k, v in result[0].items():
                if k == "blob":
                    content = base64.b64decode(v.encode("utf-8"))
                if k == "content-type":
                    type = "audio/flac".split("/")[-1]
            audio = AudioSegment.from_file(BytesIO(content))
            name = str(uuid.uuid4())[:4]
            audio.export(f"public/audios/{name}.{type}", format=type)
            result = {"generated audio": f"/audios/{name}.{type}"}
        return result
    '''
    @tool.get("/automatic-speech-recognition")
    def automatic_speech_recognition(model_id: str, audio: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["hugging"]["token"])
        audio_data = requests.get(audio, timeout=10).content
        response = inference(data=audio_data, raw_response=True)
        result = response.json()
        return result
    @tool.get("/audio-to-audio")
    def audio_to_audio(model_id: str, audio: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["hugging"]["token"])
        audio_data = requests.get(audio, timeout=10).content
        response = inference(data=audio_data, raw_response=True)
        result = response.json()
        content = None
        type = None
        for k, v in result[0].items():
            if k == "blob":
                content = base64.b64decode(v.encode("utf-8"))
            if k == "content-type":
                type = "audio/flac".split("/")[-1]
        audio = AudioSegment.from_file(BytesIO(content))
        name = str(uuid.uuid4())[:4]
        audio.export(f"public/audios/{name}.{type}", format=type)
        result = {"generated audio": f"/audios/{name}.{type}"}
        return result
    @tool.get("/audio-classification")
    def audio_classification(model_id: str, audio: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["hugging"]["token"])
        audio_data = requests.get(audio, timeout=10).content
        response = inference(data=audio_data, raw_response=True)
        result = response.json()
        return result
    
    return tool
