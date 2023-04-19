from langchain.llms import OpenAI
from langchain import OpenAI, LLMChain, PromptTemplate, SerpAPIWrapper
from langchain.agents import ZeroShotAgent, AgentExecutor, initialize_agent, Tool
import importlib
import json
import os
import requests
import yaml
from bmtools.agent.apitool import RequestTool
from bmtools.agent.executor import Executor, AgentExecutorWithTranslation
from bmtools import get_logger
from bmtools.agent.BabyagiTools import BabyAGI
# from bmtools.models.customllm import CustomLLM


logger = get_logger(__name__)


def import_all_apis(tool_json):
    '''import all apis that is a tool
    '''
    doc_url = tool_json['api']['url']
    response = requests.get(doc_url)

    logger.info("Doc string URL: {}".format(doc_url))
    if doc_url.endswith('yaml') or doc_url.endswith('yml'):
        plugin = yaml.safe_load(response.text)
    else:
        plugin = json.loads(response.text)

    server_url = plugin['servers'][0]['url']
    if server_url.startswith("/"):
        server_url = "http://127.0.0.1:8079" + server_url
    logger.info("server_url {}".format(server_url))
    all_apis = []
    for key in plugin['paths']:
        value = plugin['paths'][key]
        api = RequestTool(root_url=server_url, func_url=key, method='get', request_info=value)
        all_apis.append(api)
    return all_apis

def load_single_tools(tool_name, tool_url):
    
    # tool_name, tool_url = "datasette", "https://datasette.io/"
    # tool_name, tool_url = "klarna", "https://www.klarna.com/"
    # tool_name, tool_url =  'chemical-prop',  "http://127.0.0.1:8079/tools/chemical-prop/"
    # tool_name, tool_url =  'douban-film',  "http://127.0.0.1:8079/tools/douban-film/"
    # tool_name, tool_url =  'weather',  "http://127.0.0.1:8079/tools/weather/"
    # tool_name, tool_url =  'wikipedia',  "http://127.0.0.1:8079/tools/wikipedia/"
    # tool_name, tool_url =  'wolframalpha',  "http://127.0.0.1:8079/tools/wolframalpha/"
    # tool_name, tool_url =  'klarna',  "https://www.klarna.com/"


    get_url = tool_url +".well-known/ai-plugin.json"
    response = requests.get(get_url)

    if response.status_code == 200:
        tool_config_json = response.json()
    else:
        raise RuntimeError("Your URL of the tool is invalid.")

    return tool_name, tool_config_json
    


class STQuestionAnswerer:
    def __init__(self, openai_api_key = "", stream_output=False, llm='ChatGPT'):
        if len(openai_api_key) < 3: # not valid key (TODO: more rigorous checking)
            openai_api_key = os.environ.get('OPENAI_API_KEY')

        self.openai_api_key = openai_api_key
        self.llm_model = llm

        self.set_openai_api_key(openai_api_key)
        self.stream_output = stream_output
        
     
    
    def set_openai_api_key(self, key):
        logger.info("Using {}".format(self.llm_model))
        if self.llm_model == "GPT-3.5":
            self.llm = OpenAI(temperature=0.0, openai_api_key=key)  # use text-darvinci
        elif self.llm_model == "ChatGPT":
            self.llm = OpenAI(model_name="gpt-3.5-turbo", temperature=0.0, openai_api_key=key)  # use chatgpt
        else:
            raise RuntimeError("Your model is not available.")

    def load_tools(self, name, meta_info, prompt_type="react-with-tool-description", return_intermediate_steps=True):

        self.all_tools_map = {}
        
        self.all_tools_map[name] = import_all_apis(meta_info)

        logger.info("Tool [{}] has the following apis: {}".format(name, self.all_tools_map[name]))

        if prompt_type == "zero-shot-react-description":
            subagent = initialize_agent(self.all_tools_map[name], self.llm, agent="zero-shot-react-description", verbose=True, return_intermediate_steps=return_intermediate_steps)
        elif prompt_type == "react-with-tool-description":
            description_for_model = meta_info['description_for_model'].replace("{", "{{").replace("}", "}}").strip()

            prefix = f"""Answer the following questions as best you can. General instructions are: {description_for_model}. Specifically, you have access to the following APIs:"""
            suffix = """Begin! Remember: (1) Follow the format, i.e,\nThought:\nAction:\nAction Input:\nObservation:\nFinal Answer:\n (2) Provide as much as useful information in your Final Answer. (3) YOU MUST INCLUDE all relevant IMAGES in your Final Answer using format ![img](url), and include relevant links. (3) Do not make up anything, and if your Observation has no link, DO NOT hallucihate one. (4) If you have enough information, please use \nThought: I have got enough information\nFinal Answer: \n\nQuestion: {input}\n{agent_scratchpad}"""
            prompt = ZeroShotAgent.create_prompt(
                self.all_tools_map[name], 
                prefix=prefix, 
                suffix=suffix, 
                input_variables=["input", "agent_scratchpad"]
            )
            llm_chain = LLMChain(llm=self.llm, prompt=prompt)
            logger.info("Full prompt template: {}".format(prompt.template))
            tool_names = [tool.name for tool in self.all_tools_map[name] ]
            agent = ZeroShotAgent(llm_chain=llm_chain, allowed_tools=tool_names)
            if self.stream_output:
                agent_executor = Executor.from_agent_and_tools(agent=agent, tools=self.all_tools_map[name] , verbose=True, return_intermediate_steps=return_intermediate_steps)
            else:
                agent_executor = AgentExecutorWithTranslation.from_agent_and_tools(agent=agent, tools=self.all_tools_map[name], verbose=True, return_intermediate_steps=return_intermediate_steps)
            return agent_executor
        elif prompt_type == "babyagi":
            # customllm = CustomLLM()
            tool_str = "; ".join([t.name for t in self.all_tools_map[name]] + ["TODO"])
            prefix = """You are an AI who performs one task based on the following objective: {objective}. Take into account these previously completed tasks: {context}.\n You have access to the following APIs:"""
            suffix = """YOUR CONSTRAINTS: (1) YOU MUST follow this format:
            \nThought:\nAction:\nAction Input: \n or \nThought:\nFinal Answer:\n (2) Do not make up anything, and if your Observation has no link, DO NOT hallucihate one. (3) The Action: MUST be one of the following: """ + tool_str + """\nQuestion: {task}\n Agent scratchpad (history actions): {agent_scratchpad}."""

            # tool_str = "; ".join([t.name for t in self.all_tools_map[name]])
            # todo_prompt = PromptTemplate.from_template("You are a planner who is an expert at coming up with a todo list for a given objective. For a simple objective, do not generate a complex todo list. Generate a todo list that can largely be completed by the following APIs: " + tool_str + ". Come up with a todo list for this objective: {objective}")

            # # todo_chain = LLMChain(llm=self.llm, prompt=todo_prompt)
            # todo_chain = LLMChain(llm=customllm, prompt=todo_prompt)

            # todo_tool = Tool(
            #     name = "TODO",
            #     func=todo_chain.run,
            #     description="useful for when you need to come up with todo lists. Input: an objective to create a todo list for. Output: a todo list for that objective. Please be very clear what the objective is!"
            # )
            # self.all_tools_map[name].append(todo_tool)

            prompt = ZeroShotAgent.create_prompt(
                self.all_tools_map[name], 
                prefix=prefix, 
                suffix=suffix, 
                input_variables=["objective", "task", "context","agent_scratchpad"]
            )

            logger.info("Full prompt template: {}".format(prompt.template))

            # specify the maximum number of iterations you want babyAGI to perform
            max_iterations = 10
            baby_agi = BabyAGI.from_llm(
                llm=self.llm,
                # llm=customllm,
                prompt=prompt,
                verbose=False,
                tools=self.all_tools_map[name],
                stream_output=self.stream_output,
                return_intermediate_steps=return_intermediate_steps,
                max_iterations=max_iterations,
            )

            return baby_agi


if __name__ == "__main__":

    tools_name, tools_config = load_single_tools()
    print(tools_name, tools_config)
    
    qa =  STQuestionAnswerer()

    agent = qa.load_tools(tools_name, tools_config)

    agent("Calc integral of sin(x)+2x^2+3x+1 from 0 to 1")