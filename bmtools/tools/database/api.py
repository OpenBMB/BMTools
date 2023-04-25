import json
import os

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
    
    @tool.get("/select_database_data")
    def select_database_data(query : str='select * from customer limit 2;'):
        '''Read the data storaged in database
        '''

        print("==========query:", query)

        # load db settings
        script_path = os.path.abspath(__file__)
        script_dir = os.path.dirname(script_path)
        config = get_conf(script_dir + '/my_config.ini', 'postgresql')
        dbargs = DBArgs("postgresql", config=config)  # todo assign database name

        # send request to database
        db = Database(dbargs, timeout=-1)

        res_completion = db.pgsql_results(query) # list format


        print("========res_completion:", res_completion)

        if res_completion == "<fail>":
            raise RuntimeError("Database query failed")

        #data = json.loads(str(res_completion).strip())
        data = res_completion

        """ 
        # process the request result 
        output = {}
        output["overall"]= f"{data['current']['condition']['text']},\n"
        output["name"]= f"{data['location']['name']},\n"
        output["region"]= f"{data['location']['region']},\n"
        output["country"]= f"{data['location']['country']},\n"
        output["localtime"]= f"{data['location']['localtime']},\n"
        output["temperature"]= f"{data['current']['temp_c']}(C), {data['current']['temp_f']}(F),\n"
        output["percipitation"]= f"{data['current']['precip_mm']}(mm), {data['current']['precip_in']}(inch),\n"
        output["pressure"]= f"{data['current']['pressure_mb']}(milibar),\n"
        output["humidity"]= f"{data['current']['humidity']},\n"
        output["cloud"]= f"{data['current']['cloud']},\n"
        output["body temperature"]= f"{data['current']['feelslike_c']}(C), {data['current']['feelslike_f']}(F),\n"
        output["wind speed"]= f"{data['current']['gust_kph']}(kph), {data['current']['gust_mph']}(mph),\n"
        output["visibility"]= f"{data['current']['vis_km']}(km), {data['current']['vis_miles']}(miles),\n"
        output["UV index"]= f"{data['current']['uv']},\n"         
        """
        
        text_output = f"The query result is:\n"+"".join(str(res_completion))

        return text_output

    return tool
