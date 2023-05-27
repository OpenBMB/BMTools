import base64
from huggingface_hub.inference_api import InferenceApi
import threading
import requests
from PIL import Image, ImageDraw
from diffusers.utils import load_image

import io
from io import BytesIO

import jsonlines



# 设置API token
token = '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'
HUGGINGFACE_HEADERS = {
    "Authorization": f"Bearer {token}",
}

def image_to_bytes(img_url):
    img_byte = io.BytesIO()
    type = img_url.split(".")[-1]
    load_image(img_url).save(img_byte, format="png")
    img_data = img_byte.getvalue()
    return img_data


def read_jsonl(file_path, task):
    models = []
    with jsonlines.open(file_path) as reader:
        for obj in reader:
            if "task" in obj:
                if obj['task'] == task :
                    models.append(obj["id"])
    return models


# 定义测试函数
def test_model(model, result_dict):
    # 创建InferenceApi对象
    # 调用接口进行测试
    print(f"test {model}")
    try:
        inference = InferenceApi(repo_id=model, token=token)
        # input = "The answer to the universe is nothing."
        text = "The answer to the universe is nothing."
        context = "The answer to the universe is 42."
        input = {"source_sentence": text, "sentences" : [(context if context else "")]}
        result = inference(input, raw_response=True)
        # with open(f"./output.flac", "rb") as f:
        #     audio = f.read()
        #     result = inference(data=audio, raw_response=True)
            # print(result.content)
        # inference = InferenceApi(repo_id=model, token=token)
        # img_data = image_to_bytes("./boat.png")
        # img_base64 = base64.b64encode(img_data).decode("utf-8")
        # result = str(inference({"question": "What is it?", "image": img_base64}))
        # img_data = image_to_bytes("./boat.png")
        # result = inference(data=img_data) # not support
        # HUGGINGFACE_HEADERS["Content-Length"] = str(len(img_data))
        # task_url = f"https://api-inference.huggingface.co/models/{model}"
        # r = requests.post(task_url, headers=HUGGINGFACE_HEADERS, data=img_data)
        # result = r.json()
        # if "path" in result:
        #     result["generated image"] = result.pop("path")
        # img_data = image_to_bytes("boat.png")
        # image = Image.open(BytesIO(img_data))
        # result = inference(data=img_data, raw_response=True)
        if 'error' in str(result) or (not result.ok):
            result_dict[model] = False
            print(f'Model {model} failed with error: {result.content}')
        else:
            result_dict[model] = True
    except Exception as e:
        result_dict[model] = False
        print(f'Model {model} failed with error: {e}')
    # 打印测试结果
    print(f'Model {model} returns: {result}')

# 'text-classification', 'token-classification', 'text2text-generation', 'summarization', 'translation', 
tasks = ['sentence-similarity']

for task in tasks:
    print(f"======================================={task}======================================")
    # 创建线程列表
    threads = []
    # 创建结果词典
    result_dict = {}
    models = read_jsonl("p0_models.jsonl", task=task)
    # 遍历每个模型，为其创建一个线程
    for model in models:
        t = threading.Thread(target=test_model, args=(model, result_dict))
        threads.append(t)

    # 启动所有线程
    for t in threads:
        t.start()

    # 等待所有线程执行完毕
    for t in threads:
        t.join()

    # 输出失败的模型
    failed_models = [model for model, result in result_dict.items() if not result]
    # 输出成功的模型
    succeeded_models = [model for model, result in result_dict.items() if result]
    if failed_models:
        print(f'The following models failed\n{failed_models}')
    else:
        print('All models passed the test!')
    print(f"succeeded_models\n{task}: {succeeded_models}")
    # 输出到文件中，追加模式
    with open('nlp_models.txt', 'a') as f:
        f.write(f"{task}: {succeeded_models}\n")
    # from huggingface_hub.inference_api import InferenceApi

    # inference = InferenceApi(repo_id="philschmid/bart-large-cnn-samsum", token="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")

    # print(inference("My name is Li Hua. I'm a football player in my high school."))