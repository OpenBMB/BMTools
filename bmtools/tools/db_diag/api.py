import json
import os
import requests
import numpy as np
import openai
import paramiko


from ..tool import Tool
from bmtools.tools.database.utils.db_parser import get_conf
from bmtools.tools.database.utils.database import DBArgs, Database
from bmtools.models.customllm import CustomLLM
from bmtools.tools.db_diag.anomaly_detection import detect_anomalies
from bmtools.tools.db_diag.anomaly_detection import prometheus


def obtain_values_of_metrics(start_time, end_time, metrics):

    required_values = {}

    for metric in metrics:
        metric_values = prometheus('api/v1/query_range', {'query': metric, 'start': start_time, 'end': end_time, 'step': '3'})
        if metric_values["data"]["result"] != []:
            metric_values = metric_values["data"]["result"][0]["values"]
        else:
            raise Exception("No metric values found for the given time range")

        # compute the average value of the metric
        max_value = np.max(np.array([float(value) for _, value in metric_values]))

        required_values[metric] = max_value

    return required_values


def build_db_diag_tool(config) -> Tool:
    tool = Tool(
        "Database Diagnosis",
        "Diagnose the bottlenecks of a database based on relevant metrics",
        name_for_model="db_diag",
        description_for_model="Plugin for diagnosing the bottlenecks of a database based on relevant metrics",
        logo_url="https://commons.wikimedia.org/wiki/File:Postgresql_elephant.svg",
        contact_email="hello@contact.com",
        legal_info_url="hello@legal.com"
    )

    #URL_CURRENT_WEATHER= "http://api.weatherapi.com/v1/current.json"
    #URL_FORECAST_WEATHER = "http://api.weatherapi.com/v1/forecast.json"

    URL_PROMETHEUS = 'http://8.131.229.55:9090/'
    prometheus_metrics = {"cpu_usage": "avg(rate(process_cpu_seconds_total{instance=\"123.56.63.105:9187\"}[5m]) * 1000)", 
                          "cpu_metrics": ["node_load1{instance=\"123.56.63.105:9100\"}", "node_load5{instance=\"123.56.63.105:9100\"}", "node_load15{instance=\"123.56.63.105:9100\"}"], 
                          "memory_usage": "node_memory_MemTotal_bytes{instance=~\"123.56.63.105:9100\"} - (node_memory_Cached_bytes{instance=~\"123.56.63.105:9100\"} + node_memory_Buffers_bytes{instance=~\"123.56.63.105:9100\"} + node_memory_MemFree_bytes{instance=~\"123.56.63.105:9100\"})",
                          "memory_metrics": ["pg_stat_activity_count{datname=~\"(imdbload|postgres|sysbench|template0|template1|tpcc|tpch)\", instance=~\"123.56.63.105:9187\", state=\"active\"} !=0"]}

    # load db settings
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    config = get_conf(script_dir + '/my_config.ini', 'postgresql')
    dbargs = DBArgs("postgresql", config=config)  # todo assign database name

    # send request to database
    db = Database(dbargs, timeout=-1)

    server_config = get_conf(script_dir + '/my_config.ini', 'benchserver')


    @tool.get("/obtain_start_and_end_time_of_anomaly")
    def obtain_start_and_end_time_of_anomaly():
        # Create SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        start_time = 0
        end_time = 0

        try:
            # Connect to the remote server
            ssh.connect(server_config["server_address"], username=server_config["username"], password=server_config["password"])

            # Create an SFTP client
            sftp = ssh.open_sftp()

            # Change to the remote directory
            sftp.chdir(server_config["remote_directory"])

            # Get a list of files in the directory
            files = sftp.listdir()

            required_file_name = ""
            required_tp = -1
            # Read the contents of each file
            for filename in files:
                remote_filepath = server_config["remote_directory"] + '/' + filename
                
                tp = filename.split("_")[0]
                
                if tp.isdigit():
                    tp = int(tp)
                    if required_tp < tp:
                        required_tp = tp
                        required_file_name = filename
                        
            file_content = sftp.open(server_config["remote_directory"] + '/' + required_file_name).read()
            file_content = file_content.decode()
            tps = file_content.split("\n")[0]
            start_time = tps.split(";")[0]
            end_time = tps.split(";")[1]

        finally:
            # Close the SFTP session and SSH connection
            sftp.close()
            ssh.close()

        return {"start_time": start_time, "end_time": end_time}

    @tool.get("/whether_is_abnormal_metric")
    def whether_is_abnormal_metric(start_time:int, end_time:int, metric_name : str="cpu_usage"):

        interval_time = 5
        metric_values = prometheus('api/v1/query_range', {'query': prometheus_metrics[metric_name], 'start': start_time-interval_time*60, 'end': end_time+interval_time*60, 'step': '3'})
        # prometheus('api/v1/query_range', {'query': '100 - (avg(irate(node_cpu_seconds_total{instance=~"123.56.63.105:9100",mode="idle"}[1m])) * 100)', 'start': '1684412385', 'end': '1684413285', 'step': '3'})
        # print(" === metric_values", metric_values)

        if metric_values["data"]["result"] != []:
            metric_values = metric_values["data"]["result"][0]["values"]
        else:
            raise Exception("No metric values found for the given time range")

        is_abnormal = detect_anomalies(np.array([float(value) for _, value in metric_values]))

        if is_abnormal:
            return "The metric is abnormal"
        else:
            return "The metric is normal"


    @tool.get("/cpu_diagnosis_agent")
    def cpu_diagnosis_agent(start_time : int, end_time : int):

        cpu_metrics = prometheus_metrics["cpu_metrics"]

        detailed_cpu_metrics = obtain_values_of_metrics(start_time, end_time, cpu_metrics)

        openai.api_key = os.environ["OPENAI_API_KEY"]

        prompt = """The CPU metric is abnormal. then obtain the three CPU relevant metric values from Prometheus, including the load over the last 1 minutes, the load over the last 5 minutes, and the load over the last 15 minutes.

Next output the analysis of potential causes of the high CPU usage based on the three CPU relevant metric values,

1. If the load over the last 1 minute is greater than 1, the load over the last 5 minutes is less than 1, and the load over the last 15 minutes is less than 1: 
   - Short-term busyness, medium to long-term idle.
   - This could be an indication of "jitter" or a "pre-congestion" state.

2. If the load over the last 1 minute is greater than 1, the load over the last 5 minutes is greater than 1, and the load over the last 15 minutes is less than 1: 
   - Short-term busyness, medium-term tension.
   - It is likely the start of a congestion situation.

3. If the load over the last 1 minute is greater than 1, the load over the last 5 minutes is greater than 1, and the load over the last 15 minutes is greater than 1: 
   - Short-term, medium-term, and long-term busyness.
   - The system is "congested."

4. If the load over the last 1 minute is less than 1, the load over the last 5 minutes is greater than 1, and the load over the last 15 minutes is greater than 1: 
   - Short-term idle, medium to long-term busyness.
   - No need to be alarmed, as the system is "improving congestion."

The three CPU relevant metric values are {}
        """.format(detailed_cpu_metrics)

        # print(prompt)

        # response = openai.Completion.create(
        # model="text-davinci-003",
        # prompt=prompt,
        # temperature=0,
        # max_tokens=1000,
        # top_p=1.0,
        # frequency_penalty=0.0,
        # presence_penalty=0.0,
        # stop=["#", ";"]
        # )
        # output_text = response.choices[0].text.strip()

        # Set up the OpenAI GPT-3 model
        # model_engine = "gpt-3.5-turbo"

        # prompt_response = openai.ChatCompletion.create(
        #     engine="gpt-3.5-turbo",
        #     messages=[
        #         {"role": "assistant", "content": "The table schema is as follows: " + str(schema)},
        #         {"role": "user", "content": str(prompt)}
        #         ]
        # )
        # output_text = prompt_response['choices'][0]['message']['content']

        llm = CustomLLM()
        output_analysis = llm(prompt)

        return output_analysis

    @tool.get("/memory_diagnosis_agent")
    def memory_diagnosis_agent(start_time : int, end_time : int):

        memory_metrics = prometheus_metrics["memory_metrics"]

        detailed_memory_metrics = obtain_values_of_metrics(start_time, end_time, memory_metrics)

        openai.api_key = os.environ["OPENAI_API_KEY"]

        db = Database(dbargs, timeout=-1)
        slow_queries = db.obtain_historical_slow_queries()

        slow_query_state = ""
        for i,query in enumerate(slow_queries):
            slow_query_state += str(i+1) + '. ' + str(query) + "\n"

        print(slow_query_state)

        prompt = """The memory metric is abnormal. The number of active sessions is {}. The slow queries are:
        {}
        
Output the analysis of potential causes of the high memory usage based on the active sessions and slow queries, e.g., 

If there are many active sessions, high-concurrency sessions can consume significant amounts of memory, especially if they execute memory-intensive operations or hold large result sets in memory. This can lead to memory pressure, increased disk I/O, and potential out-of-memory errors if the system does not have enough available memory to handle the workload.

If there are slow queries, they involve large result sets that need to be stored in memory before being sent back to the client application. If the query returns a substantial number of rows or the result set contains large data objects (e.g., images, documents), it can consume a significant amount of memory ...

Note: include the important slow queries in the output.
""".format(detailed_memory_metrics, slow_query_state)

        # print(prompt)

        # response = openai.Completion.create(
        # model="text-davinci-003",
        # prompt=prompt,
        # temperature=0,
        # max_tokens=1000,
        # top_p=1.0,
        # frequency_penalty=0.0,
        # presence_penalty=0.0,
        # stop=["#", ";"]
        # )
        # output_text = response.choices[0].text.strip()

        # Set up the OpenAI GPT-3 model
        # model_engine = "gpt-3.5-turbo"

        # prompt_response = openai.ChatCompletion.create(
        #     engine="gpt-3.5-turbo",
        #     messages=[
        #         {"role": "assistant", "content": "The table schema is as follows: " + str(schema)},
        #         {"role": "user", "content": str(prompt)}
        #         ]
        # )
        # output_text = prompt_response['choices'][0]['message']['content']

        llm = CustomLLM()
        output_analysis = llm(prompt)

        return output_analysis

    return tool
