from bmtools.agent.singletool import load_single_tools, STQuestionAnswerer

# Langchain
tool_name, tool_url = 'database',  "http://127.0.0.1:8079/tools/database/"
tool_name, tool_config = load_single_tools(tool_name, tool_url)
print(tool_name, tool_config)
stqa =  STQuestionAnswerer()

agent = stqa.load_tools(tool_name, tool_config, prompt_type="react-with-tool-description")

''' 
# rewrite_sql
agent("Rewrite the input query: select * from customer limit 2")
'''

# select_database_data
agent(""" 
Fetch the results from a postgresql database based on the following description: 

\"Retrieve all the data from the 'customer' table and limit the output to only the first 2 rows.\"
""")