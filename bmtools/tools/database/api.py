import json
import os
import requests

from ..tool import Tool
from bmtools.tools.database.database import DBArgs
from bmtools.tools.database.utils.db_parser import get_conf
from bmtools.tools.database.utils.database import DBArgs, Database

def build_database_tool(config) -> Tool:
    tool = Tool(
        "Data in a database",
        "Look up user data",
        name_for_model="Database",
        description_for_model="Plugin for querying the data in a database",
        logo_url="https://commons.wikimedia.org/wiki/File:Postgresql_elephant.svg",
        contact_email="hello@contact.com",
        legal_info_url="hello@legal.com"
    )

    #URL_CURRENT_WEATHER= "http://api.weatherapi.com/v1/current.json"
    #URL_FORECAST_WEATHER = "http://api.weatherapi.com/v1/forecast.json"

    URL_REWRITE= "http://8.131.229.55:5114/rewrite"

    # load db settings
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    config = get_conf(script_dir + '/my_config.ini', 'postgresql')
    dbargs = DBArgs("postgresql", config=config)  # todo assign database name

    # send request to database
    db = Database(dbargs, timeout=-1)

    @tool.get("/get_database_schema")
    def get_database_schema(): # query : str='select * from customer limit 2;'

        #todo simplify the schema based on the query
        schema = db.compute_table_schema()

        print("========schema:", schema)

        text_output = f"The database schema is:\n" + "".join(str(schema))

        return text_output

    @tool.get("/select_database_data")
    def select_database_data(query : str='select * from customer limit 2;', schema : str=None):
        '''Read the data stored in database
        '''

        res_completion = db.pgsql_results(query) # list format

        if res_completion == "<fail>":
            raise RuntimeError("Database query failed")

        #data = json.loads(str(res_completion).strip())

        text_output = f"The query result is:\n"+"".join(str(res_completion))

        return text_output

    @tool.get("/rewrite_sql")
    def rewrite_sql(sql: str="select distinct l_orderkey, sum(l_extendedprice + 3 + (1 - l_discount)) as revenue, o_orderkey, o_shippriority from customer, orders, lineitem where c_mktsegment = 'BUILDING' and c_custkey = o_custkey and l_orderkey = o_orderkey and o_orderdate < date '1995-03-15' and l_shipdate > date '1995-03-15' group by l_orderkey, o_orderkey, o_shippriority order by revenue desc, o_orderkey;"):

        '''Get rewritten sql from rewriter
        '''
        param = {
            "sql": sql
        }
        print("Rewriter param:", param)
        headers = {'Content-Type': 'application/json'}
        res_completion = requests.post(URL_REWRITE, data=json.dumps(param), headers=headers)

        print("============ res_completion", res_completion.text)

        data = json.loads(res_completion.text.strip())
        data = data.get('data')
        text_output = f"Rewritten sql is:\n"+data.get('rewritten_sql')
        
        return text_output


    return tool
