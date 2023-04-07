import bmtools

server = bmtools.ToolServer()
print(server.list_tools())
server.load_tool("chemical-prop")
server.load_tool("douban-film")
server.load_tool("weather")
server.load_tool("wikipedia")
server.load_tool("wolframalpha")
server.load_tool("bing_search")
server.load_tool("office-ppt")
server.load_tool("stock")
server.load_tool("map")
server.serve()
