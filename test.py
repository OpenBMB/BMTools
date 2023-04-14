from bmtools.agent.singletool import load_single_tools, STQuestionAnswerer

tool_name, tool_url = 'wikipedia',  "http://127.0.0.1:8079/tools/wikipedia/"
tool_name, tool_config = load_single_tools(tool_name, tool_url)
print(tool_name, tool_config)
stqa =  STQuestionAnswerer()

agent = stqa.load_tools(tool_name, tool_config, prompt_type="babyagi")
# agent = stqa.load_tools(tool_name, tool_config, prompt_type="react-with-tool-description")# prompt_type="babyagi")
agent("Where is Yaoming Born?")