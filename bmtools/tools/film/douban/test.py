
from bmtools.agent.singletool import load_single_tools, STQuestionAnswerer

tool_name, tool_url = 'douban',  "http://127.0.0.1:8079/tools/douban-film/"
# tools_name, tools_config = load_single_tools(tool_name, tool_url)
tools_name, tools_config = load_single_tools()
print(tools_name, tools_config)

qa =  STQuestionAnswerer()

agent = qa.load_tools(tools_name, tools_config)

agent("帮我介绍下《深海》这部电影")
agent("铃芽之旅是什么样的电影？")
agent("电影流浪地球2怎么样？")
agent("了不起的夜晚是什么电影？")
agent("宇宙探索编辑部讲的什么？")