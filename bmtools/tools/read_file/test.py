from bmtools.agent.singletool import load_single_tools, STQuestionAnswerer

tool_name, tool_url = 'read_file',  "http://127.0.0.1:8079/tools/read_file/"
tool_name, tool_config = load_single_tools(tool_name, tool_url)
print(tool_name, tool_config)
stqa =  STQuestionAnswerer()

agent = stqa.load_tools(tool_name, tool_config)
agent("read content from test.txt")