
from bmtools.agent.singletool import load_single_tools, STQuestionAnswerer

tool_name, tool_url = 'hugging_tools',  "http://127.0.0.1:8079/tools/hugging_tools/"
tools_name, tools_config = load_single_tools(tool_name, tool_url)
print(tools_name, tools_config)

qa =  STQuestionAnswerer()
print(tools_config)
agent = qa.load_tools(tools_name, tools_config)

answer = agent("Please generate a picture of a cat.")
print(answer)


answer = agent("What does the picture a.jpg shows?")
print(answer)


answer = agent("What does the man say in the audio b.mp3?")
print(answer)


answer = agent("Generate a audio for the animal in the picture.")
print(answer)


answer = agent("Generate a picture of the animal whose voice is recorded in this audio: b.mp3.")
print(answer)