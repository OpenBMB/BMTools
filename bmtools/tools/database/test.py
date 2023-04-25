from bmtools.agent.singletool import load_single_tools, STQuestionAnswerer

tool_name, tool_url = 'database',  "http://127.0.0.1:8079/tools/database/"
tools_name, tools_config = load_single_tools(tool_name, tool_url)
print(tools_name, tools_config)

qa =  STQuestionAnswerer()

agent = qa.load_tools(tools_name, tools_config)

agent("Retrieve the highest distinct l_orderkey value of lineitem, where there exists a maximum c_custkey of customers that matches the l_orderkey.")