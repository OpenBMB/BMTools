from ast import List
from asyncio import Queue
from functools import wraps
import io
import json
import os
import random
import threading
import requests
from ..tool import Tool
from huggingface_hub.inference_api import InferenceApi
import base64
from io import BytesIO
import os
import random
import uuid
import requests
from PIL import Image, ImageDraw
from diffusers.utils import load_image
from pydub import AudioSegment
from huggingface_hub.inference_api import InferenceApi
from huggingface_hub.inference_api import ALL_TASKS
from huggingface_hub.utils._errors import RepositoryNotFoundError
# from langchain.prompts import PromptTemplate
# from langchain.chains import LLMChain
# from langchain.llms import OpenAI

DIRPATH = os.path.dirname(os.path.abspath(__file__))

# ENDPOINT	MODEL NAME	
# /v1/chat/completions	gpt-4, gpt-4-0314, gpt-4-32k, gpt-4-32k-0314, gpt-3.5-turbo, gpt-3.5-turbo-0301	
# /v1/completions	text-davinci-003, text-davinci-002, text-curie-001, text-babbage-001, text-ada-001, davinci, curie, babbage, ada

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

MODELS = [json.loads(line) for line in open(f"{DIRPATH}/p0_models.jsonl", "r").readlines()]
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

def get_model_status(model_id, url, headers):
    # endpoint_type = "huggingface" if "huggingface" in url else "local"
    if "huggingface" in url:
        r = requests.get(url + f"/{model_id}", headers=headers, proxies=PROXY)
    else:
        r = requests.get(url)
    return r.status_code == 200 and "loaded" in r.json() and r.json()["loaded"]

def image_to_bytes(img_url):
    img_byte = io.BytesIO()
    type = img_url.split(".")[-1]
    load_image(img_url).save(img_byte, format="png")
    img_data = img_byte.getvalue()
    return img_data

def build_tool(conf) -> Tool:
    l = []
    tool = Tool(
        tool_name="hugging_tools",
        description="API interface for HuggingGPT-like applications.",
        name_for_model="hugging_tools", 
        description_for_model='''This API interface provides easy access to popular models available on the Huggingface model hub. You MUST check model_docs to fetch the available models FIRST: 
            Action: model_docs
            Action Input: {"task" : <task_name>}
            After that you can choose an available models. ''' ,
        logo_url="https://your-app-url.com/.well-known/logo.png",
        contact_email="test@123.com",
        legal_info_url="hello@legal.com"
    )

    # in order to get the api list when initializing the route.
    # default to set the route to / + func name
    def get_in_list(func):
        func.__doc__ = '''You MUST check model_docs to fetch the available models FIRST: 
            Action: model_docs
            Action Input: {"task" : "%s"}
            After that you can choose an available models in the list. 
        ''' % func.__name__
        name = func.__name__
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except RepositoryNotFoundError as e:
                return '''The model with model_id you input is not available. Plese check the model_docs to get other available models:
                    Action: model_docs
                    Action Input: {"task" : "%s"}
                    After that you can choose an available models in the list. 
                '''
        path = "/" + func.__name__
        wrapper.route = path
        l.append(func.__name__)
        return tool.get(path)(wrapper)

    def format_string(str: tuple):
        def wrap1(func):
            func.__doc__ = func.__doc__ % str
            @wraps(func)
            def wrap2(*args, **kwargs):
                return func(*args, **kwargs)
            return wrap2
        return wrap1
        
    # def debug(func):
    #     @wraps(func)
    #     def wrap1(*args, **kwargs):
    #         return func(*args, **kwargs)
    #     print(func.__doc__)
    #     return wrap1

    @get_in_list
    def question_answering(model_id: str, question: str, context: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["huggingface"]["token"])
        return str(inference({"question": question, "context" : (context if context else "")}))

    @get_in_list
    def sentence_similarity(model_id: str, text: str, context: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["huggingface"]["token"])
        return str(inference({"source_sentence": text, "sentences" : [(context if context else "")]}))
    #  ['ProsusAI/finbert', 'distilbert-base-uncased-finetuned-sst-2-english', 'cardiffnlp/twitter-roberta-base-sentiment']
    @get_in_list
    def text_classification(model_id: str, text: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["huggingface"]["token"])
        return str(inference(text))
    #  ['dslim/bert-base-NER', 'Jean-Baptiste/camembert-ner', 'oliverguhr/fullstop-punctuation-multilang-large']
    @get_in_list
    def token_classification(model_id: str, text: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["huggingface"]["token"])
        return str(inference(text))
    #  ['google/flan-t5-xxl', 'bigscience/T0pp', 'google/flan-ul2']
    @get_in_list
    def text2text_generation(model_id: str,text: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["huggingface"]["token"])
        return str(inference(text))
    # ['facebook/bart-large-cnn', 'philschmid/bart-large-cnn-samsum', 'sshleifer/distilbart-cnn-12-6']
    @get_in_list
    def summarization(model_id: str, text: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["huggingface"]["token"])
        return str(inference(text))
    @get_in_list
    def translation(model_id: str, text: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["huggingface"]["token"])
        return str(inference(text))
    @get_in_list
    def conversational(model_id: str, text: str, past_user_inputs: str, generated_responses: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["huggingface"]["token"])
        input = {
            "past_user_inputs": [past_user_inputs],
            "generated_responses": [generated_responses],
            "text": text,
        }
        return str(inference(input))
    # ['bigscience/bloom', 'EleutherAI/gpt-j-6B', 'gpt2']
    @get_in_list
    def text_generation(model_id: str, text: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["huggingface"]["token"])
        return str(inference(text))
    # CV tasks
    # ['dandelin/vilt-b32-finetuned-vqa', 'azwierzc/vilt-b32-finetuned-vqa-pl', 'Bingsu/temp_vilt_vqa', 'tufa15nik/vilt-finetuned-vqasi']
    @get_in_list
    def visual_question_answering(model_id: str, image_file_name: str, text: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["huggingface"]["token"])
        img_data = image_to_bytes(image_file_name)
        img_base64 = base64.b64encode(img_data).decode("utf-8")
        return str(inference({"question": text, "image": img_base64}))
    # ['impira/layoutlm-document-qa', 'tiennvcs/layoutlmv2-base-uncased-finetuned-infovqa', 'pardeepSF/layoutlm-vqa', 'jinhybr/OCR-DocVQA-Donut', 'impira/layoutlm-invoices', 'faisalraza/layoutlm-invoices', 'xhyi/layoutlmv3_docvqa_t11c5000', 'tiennvcs/layoutlmv2-large-uncased-finetuned-infovqa', 'tiennvcs/layoutlmv2-large-uncased-finetuned-vi-infovqa', 'tiennvcs/layoutlmv2-base-uncased-finetuned-vi-infovqa', 'naver-clova-ix/donut-base-finetuned-docvqa', 'tiennvcs/layoutlmv2-base-uncased-finetuned-docvqa', 'MariaK/layoutlmv2-base-uncased_finetuned_docvqa_v2']
    @get_in_list
    def document_question_answering(model_id: str, image: str, text: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["huggingface"]["token"])
        img_data = image_to_bytes(image)
        img_base64 = base64.b64encode(img_data).decode("utf-8")
        return str(inference({"question": text, "image": img_base64}))
    # ['lambdalabs/sd-image-variations-diffusers']
    @get_in_list
    def image_to_image(model_id: str, image: str) -> str:
        img_data = image_to_bytes(image)
        # result = inference(data=img_data) # not support
        HUGGINGFACE_HEADERS["Content-Length"] = str(len(img_data))
        task_url = f"https://api-inference.huggingface.co/models/{model_id}"
        r = requests.post(task_url, headers=HUGGINGFACE_HEADERS, data=img_data)
        name = str(uuid.uuid4())[:4]
        result = f"{name}.jpeg"
        with open(f"{DIRPATH}/{result}", "wb") as f:
            f.write(r.content)
        return result
    # ['prompthero/openjourney-v4', 'hakurei/waifu-diffusion', 'gsdf/Counterfeit-V2.0', 'runwayml/stable-diffusion-v1-5', 'wavymulder/Analog-Diffusion', 'andite/pastel-mix', 'andite/anything-v4.0', 'gsdf/Counterfeit-V2.5', 'CompVis/stable-diffusion-v1-4', 'prompthero/openjourney', 'stabilityai/stable-diffusion-2', 'stabilityai/stable-diffusion-2-1', 'nitrosocke/Ghibli-Diffusion', 'nitrosocke/Arcane-Diffusion', 'nitrosocke/mo-di-diffusion', 'DGSpitzer/Cyberpunk-Anime-Diffusion', 'dreamlike-art/dreamlike-diffusion-1.0', 'riffusion/riffusion-model-v1', 'Linaqruf/anything-v3.0', 'Envvi/Inkpunk-Diffusion', 'hassanblend/hassanblend1.4', 'nitrosocke/redshift-diffusion']
    @get_in_list
    def text_to_image(model_id: str, text: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["huggingface"]["token"])
        img = inference(text)
        name = str(uuid.uuid4())[:4]
        img.save(f"{DIRPATH}/{name}.png")
        result = f"{name}.png"
        return result
    # ['nvidia/segformer-b5-finetuned-ade-640-640', 'nvidia/segformer-b1-finetuned-cityscapes-1024-1024', 'facebook/detr-resnet-50-panoptic', 'facebook/maskformer-swin-base-coco', 'nvidia/segformer-b0-finetuned-ade-512-512']
    @get_in_list
    def image_segmentation(model_id: str, image: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["huggingface"]["token"])
        img_data = image_to_bytes(image)
        image = Image.open(BytesIO(img_data))
        predicted = inference(data=img_data)
        colors = []
        for i in range(len(predicted)):
            colors.append((random.randint(100, 255), random.randint(100, 255), random.randint(100, 255), 155))
        for i, pred in enumerate(predicted):
            mask = pred.pop("mask").encode("utf-8")
            mask = base64.b64decode(mask)
            mask = Image.open(BytesIO(mask), mode='r')
            mask = mask.convert('L')

            layer = Image.new('RGBA', mask.size, colors[i])
            image.paste(layer, (0, 0), mask)
        name = str(uuid.uuid4())[:4]
        image.save(f"{DIRPATH}/{name}.jpg")
        result = {}
        result["generated image"] = f"{name}.jpg"
        result["predicted"] = predicted
        return str(result)
    # ['facebook/detr-resnet-50', 'hustvl/yolos-tiny']
    @get_in_list
    def object_detection(model_id: str, image: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["huggingface"]["token"])
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
        image.save(f"{DIRPATH}/{name}.jpg")
        result = {}
        result["generated image"] = f"{name}.jpg"
        result["predicted"] = predicted
        return str(result)
    # ['google/vit-base-patch16-224', 'facebook/deit-base-distilled-patch16-224', 'microsoft/dit-base-finetuned-rvlcdip']
    @get_in_list
    def image_classification(model_id: str, image: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["huggingface"]["token"])
        img_data = image_to_bytes(image)
        result = inference(data=img_data)
        return str(result)
    # ['nlpconnect/vit-gpt2-image-captioning', 'ydshieh/vit-gpt2-coco-en', 'microsoft/trocr-small-handwritten', 'Salesforce/blip-image-captioning-large', 'microsoft/trocr-small-printed', 'microsoft/trocr-large-printed', 'kha-white/manga-ocr-base', 'microsoft/trocr-base-handwritten', 'microsoft/trocr-base-printed', 'microsoft/trocr-large-handwritten', 'naver-clova-ix/donut-base']
    @get_in_list
    def image_to_text(model_id: str, image: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["huggingface"]["token"])
        img_data = image_to_bytes(image)
        result = inference(data=img_data)
        return str(result)
    # AUDIO tasks
    @get_in_list
    def text_to_speech(model_id: str, text: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["huggingface"]["token"])
        response = inference(text, raw_response=True)
        name = str(uuid.uuid4())[:4]
        with open(f"{DIRPATH}/{name}.flac", "wb") as f:
            f.write(response.content)
        result = f"{name}.flac"
        return result
    #['openai/whisper-large-v2', 'openai/whisper-base', 'jonatasgrosman/wav2vec2-large-xlsr-53-english', 'openai/whisper-medium', 'facebook/wav2vec2-base-960h', 'facebook/wav2vec2-large-960h-lv60-self', 'facebook/s2t-small-librispeech-asr', 'openai/whisper-tiny', 'openai/whisper-tiny.en']
    @get_in_list
    def automatic_speech_recognition(model_id: str, audio_file_name: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["huggingface"]["token"])
        with open(f"{DIRPATH}/{audio_file_name}", "rb") as f:
            audio = f.read()
            response = inference(data=audio, raw_response=True)
        # response = inference(data=audio_data, raw_response=True)
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
        audio.export(f"{DIRPATH}/{name}.{type}", format=type)
        result = f"{name}.{type}"
        return result
    # ['ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition', 'harshit345/xlsr-wav2vec-speech-emotion-recognition', 'speechbrain/lang-id-voxlingua107-ecapa', 'anton-l/sew-mid-100k-ft-keyword-spotting', 'anton-l/wav2vec2-base-lang-id', 'anton-l/wav2vec2-random-tiny-classifier', 'superb/wav2vec2-base-superb-er', 'superb/hubert-large-superb-er', 'superb/wav2vec2-base-superb-sid', 'speechbrain/spkrec-xvect-voxceleb', 'MIT/ast-finetuned-audioset-10-10-0.4593', 'audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim', 'TalTechNLP/voxlingua107-epaca-tdnn', 'speechbrain/lang-id-commonlanguage_ecapa', 'speechbrain/urbansound8k_ecapa', 'sahita/language-identification', 'bookbot/wav2vec2-adult-child-cls', 'anton-l/wav2vec2-base-ft-keyword-spotting', 'hackathon-pln-es/wav2vec2-base-finetuned-sentiment-mesd', 'superb/wav2vec2-base-superb-ks', 'superb/hubert-base-superb-er', 'hackathon-pln-es/wav2vec2-base-finetuned-sentiment-classification-MESD']
    @get_in_list
    def audio_classification(model_id: str, audio: str) -> str:
        inference = InferenceApi(repo_id=model_id, token=config["huggingface"]["token"])
        with open(f"./output.flac", "rb") as f:
            audio = f.read()
            response = inference(data=audio, raw_response=True)
        result = response.json()
        return str(result)
    
    @tool.get("/model_docs")
    @format_string(str(l))
    def model_docs(task: str) -> str:
        '''returns a document about the usage, examples, and available models of existing API.

        Every time before you use the API, you should get the document of EXISTING API ONLY and ONLY use the available models in the document.

        task: the name of API, includes %s
        
        return the document of the API.

        example:
        Action: model_docs
        Action Input: {"task" : "question_answering"}
        Observation: "question_answering is a function that uses a pre-trained language model to answer questions based on a given context.\n        You can choose one model from: 'distilbert-base-uncased-distilled-squad', 'deepset/minilm-uncased-squad2', 'etalab-ia/camembert-base-squadFR-fquad-piaf'.\n\n        Action Input: {\"model_id\" : \"distilbert-base-uncased-distilled-squad\", \"question\" : \"When did the first moon landing occur?\", \"context\" : \"The first manned moon landing was achieved by the United States on July 20, 1969, in the Apollo 11 mission.\"}\n        "
        '''
        with open(f'{DIRPATH}/docs.json', 'r') as f:
            docs = json.load(f)
        if task in docs.keys():
            return docs[task]
        else:
            return "The function doesn't exist. Please input the valid function name."
        
    return tool
