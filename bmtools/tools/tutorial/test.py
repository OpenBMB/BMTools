
from bmtools.agent.singletool import load_single_tools, STQuestionAnswerer

tool_name, tool_url = 'tutorial',  "http://127.0.0.1:8079/tools/tutorial/"
tools_name, tools_config = load_single_tools(tool_name, tool_url)
print(tools_name, tools_config)

qa =  STQuestionAnswerer()
print(tools_config)
agent = qa.load_tools(tools_name, tools_config)

answer = agent("I want to cook pizza.")
print(answer)