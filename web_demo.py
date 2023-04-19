import gradio as gr
import sys
# sys.path.append('./inference/')
from bmtools.agent.tools_controller import MTQuestionAnswerer, load_valid_tools
from bmtools.agent.singletool import STQuestionAnswerer
from langchain.schema import AgentFinish
import os
import requests

available_models = ["ChatGPT", "GPT-3.5"]
DEFAULTMODEL = "GPT-3.5"

tools_mappings = {
    "klarna": "https://www.klarna.com/",
    "chemical-prop": "http://127.0.0.1:8079/tools/chemical-prop/",
    "wolframalpha": "http://127.0.0.1:8079/tools/wolframalpha/",
    "weather": "http://127.0.0.1:8079/tools/weather/",
    "douban-film": "http://127.0.0.1:8079/tools/douban-film/",
    "wikipedia": "http://127.0.0.1:8079/tools/wikipedia/",
    "office-ppt": "http://127.0.0.1:8079/tools/office-ppt/",
    "bing_search": "http://127.0.0.1:8079/tools/bing_search/",
    "map": "http://127.0.0.1:8079/tools/map/",
    "stock": "http://127.0.0.1:8079/tools/stock/",
    "baidu-translation": "http://127.0.0.1:8079/tools/baidu-translation/",
    "nllb-translation": "http://127.0.0.1:8079/tools/nllb-translation/",
}

valid_tools_info = load_valid_tools(tools_mappings)
print(valid_tools_info)
all_tools_list = sorted(list(valid_tools_info.keys()))

gr.close_all()

MAX_TURNS = 30
MAX_BOXES = MAX_TURNS * 2

def show_avatar_imgs(tools_chosen):
    if len(tools_chosen) == 0:
        tools_chosen = list(valid_tools_info.keys())
    img_template = '<a href="{}" style="float: left"> <img style="margin:5px" src="{}.png" width="24" height="24" alt="avatar" /> {} </a>'
    imgs = [valid_tools_info[tool]['avatar'] for tool in tools_chosen if valid_tools_info[tool]['avatar'] != None]
    imgs = ' '.join([img_template.format(img, img, tool ) for img, tool in zip(imgs, tools_chosen) ])
    return [gr.update(value='<span class="">'+imgs+'</span>', visible=True), gr.update(visible=True)]

return_msg = []
chat_history = ""

def answer_by_tools(question, tools_chosen, model_chosen):
    global return_msg
    return_msg += [(question, None), (None, '...')]
    yield [gr.update(visible=True, value=return_msg), gr.update(), gr.update()]
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    
    if len(tools_chosen) == 0:  # if there is no tools chosen, we use all todo (TODO: What if the pool is too large.)
        tools_chosen = list(valid_tools_info.keys())

    if len(tools_chosen) == 1: 
        answerer = STQuestionAnswerer(OPENAI_API_KEY.strip(), stream_output=True, llm=model_chosen)
        agent_executor = answerer.load_tools(tools_chosen[0], valid_tools_info[tools_chosen[0]], prompt_type="react-with-tool-description", return_intermediate_steps=True)
    else:
        answerer = MTQuestionAnswerer(OPENAI_API_KEY.strip(), load_valid_tools({k: tools_mappings[k] for k in tools_chosen}), stream_output=True, llm=model_chosen)

        agent_executor = answerer.build_runner()

    global chat_history
    chat_history += "Question: " + question + "\n"
    question = chat_history
    for inter in agent_executor(question):
        if isinstance(inter, AgentFinish): continue
        result_str = []
        return_msg.pop()
        if isinstance(inter, dict): 
            result_str.append("<font color=red>Answer:</font> {}".format(inter['output']))
            chat_history += "Answer:" + inter['output'] + "\n"
            result_str.append("...")
        else:
            not_observation = inter[0].log
            if not not_observation.startswith('Thought:'):
                not_observation = "Thought: " + not_observation
            chat_history += not_observation
            not_observation = not_observation.replace('Thought:', '<font color=green>Thought: </font>')
            not_observation = not_observation.replace('Action:', '<font color=purple>Action: </font>')
            not_observation = not_observation.replace('Action Input:', '<font color=purple>Action Input: </font>')
            result_str.append("{}".format(not_observation))
            result_str.append("<font color=blue>Action output:</font>\n{}".format(inter[1]))
            chat_history += "\nAction output:" + inter[1] + "\n"
            result_str.append("...")
        return_msg += [(None, result) for result in result_str]
        yield [gr.update(visible=True, value=return_msg), gr.update(), gr.update()]
    return_msg.pop()
    if return_msg[-1][1].startswith("<font color=red>Answer:</font> "):
        return_msg[-1] = (return_msg[-1][0], return_msg[-1][1].replace("<font color=red>Answer:</font> ", "<font color=green>Final Answer:</font> "))
    yield [gr.update(visible=True, value=return_msg), gr.update(visible=True), gr.update(visible=False)]

def retrieve(tools_search):
    if tools_search == "":
        return gr.update(choices=all_tools_list)
    else:
        url = "http://127.0.0.1:8079/retrieve"
        param = {
            "query": tools_search
        }
        response = requests.post(url, json=param)
        result = response.json()
        retrieved_tools = result["tools"]
        return gr.update(choices=retrieved_tools)

def clear_retrieve():
    return [gr.update(value=""), gr.update(choices=all_tools_list)]

def clear_history():
    global return_msg
    global chat_history
    return_msg = []
    chat_history = ""
    yield gr.update(visible=True, value=return_msg)

with gr.Blocks() as demo:
    with gr.Row():
        with gr.Column(scale=14):
            gr.Markdown("<h1 align='left'> BMTools </h1>")
        with gr.Column(scale=1):
            gr.Markdown('<img src="https://openbmb.cn/openbmb/img/head_logo.e9d9f3f.png" width="140">')
    with gr.Row():
        with gr.Column(scale=4):
            with gr.Row():
                with gr.Column(scale=0.85):
                    txt = gr.Textbox(show_label=False, placeholder="Question here. Use Shift+Enter to add new line.", lines=1).style(container=False)
                with gr.Column(scale=0.15, min_width=0):
                    buttonClear = gr.Button("Clear History")
                    buttonStop = gr.Button("Stop", visible=False)

            chatbot = gr.Chatbot(show_label=False, visible=True).style(height=600)

        with gr.Column(scale=1):
            with gr.Row():
                tools_search = gr.Textbox(
                    lines=1,
                    label="Tools Search",
                    info="Please input some text to search tools.",
                )
                buttonSearch = gr.Button("Clear")
            tools_chosen = gr.CheckboxGroup(
                choices=all_tools_list,
                value=["chemical-prop"],
                label="Tools provided",
                info="Choose the tools to solve your question.",
            )
            model_chosen = gr.Dropdown(
                list(available_models), value=DEFAULTMODEL, multiselect=False, label="Model provided", info="Choose the model to solve your question, Default means ChatGPT."
            )
    tools_search.change(retrieve, tools_search, tools_chosen)
    buttonSearch.click(clear_retrieve, [], [tools_search, tools_chosen])

    txt.submit(lambda : [gr.update(value=''), gr.update(visible=False), gr.update(visible=True)], [], [txt, buttonClear, buttonStop])
    inference_event = txt.submit(answer_by_tools, [txt, tools_chosen, model_chosen], [chatbot, buttonClear, buttonStop])
    buttonStop.click(lambda : [gr.update(visible=True), gr.update(visible=False)], [], [buttonClear, buttonStop], cancels=[inference_event])
    buttonClear.click(clear_history, [], chatbot)

    

demo.queue().launch(share=True, inbrowser=True, server_name="127.0.0.1", server_port=7001)
