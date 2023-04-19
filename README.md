# BMTools

*Read this in [English](README_en.md).*

BMTools 是一能让语言模型使用扩展工具的开源仓库，其也是开源社区构建和共享工具的一个平台。在这个仓库中，您可以 (1) 通过编写 Python 函数轻松构建插件，(2) 使用外部的 ChatGPT-Plugins。

本项目受到开源项目[LangChain](https://github.com/hwchase17/langchain/)的启发，针对开源工具的使用（例如[ChatGPT-Plugins](https://openai.com/blog/chatgpt-plugins)）进行了优化，力图实现 ChatGPT-Plugins 的开源学术版本。

当前版本的 BMTools 还有很大的改进空间，我们将继续努力提高它的性能。

## 1. 安装

```bash
git clone git@github.com:OpenBMB/BMTools.git
python setup.py develop
```

## 2. 使用现有工具

### 2.1 配置工具

#### 2.1.1 本地工具

在 secret_keys.sh 中添加 API 密钥，然后启动本地工具：

```bash
source secret_keys.sh
python host_local_tools.py
```

然后将插件的URL设置为 `http://127.0.0.1:8079/tools/{tool_name}/`（记得加上 `/`）。

#### 2.1.2 使用在线的 ChatGPT-Plugins

只需将其加载到指向 `.well-known/ai-plugin.json` 的 URL 中即可。例如， 如果 URL 设置为 `https://www.klarna.com/`，那么`https://www.klarna.com/.well-known/ai-plugin.json`是一个有效的配置。

### 2.2 使用单个工具

```python
from bmtools.agent.singletool import load_single_tools, STQuestionAnswerer

tool_name, tool_url = 'klarna',  'https://www.klarna.com/'
tool_name, tool_config = load_single_tools(tool_name, tool_url)
print(tool_name, tool_config)
stqa =  STQuestionAnswerer()

agent = stqa.load_tools(tool_name, tool_config)
agent("{Your Question}")
```

### 2.3 使用多个工具

我们可以同时使用多个工具。基本上，语言模型会递归地处理它。它会将整个工具视为一个 API，向其发送问题，工具调用其子 API 来解决问题并将其发送回父工具。此功能在即将推出的 Chat 模式中将非常有用。

可以使用以下脚本尝试此功能：

```python
from bmtools.agent.tools_controller import load_valid_tools, MTQuestionAnswerer
tools_mappings = {
    "klarna": "https://www.klarna.com/",
    "chemical-prop": "http://127.0.0.1:8079/tools/chemical-prop/",
    "wolframalpha": "http://127.0.0.1:8079/tools/wolframalpha/",
}

tools = load_valid_tools(tools_mappings)

qa =  MTQuestionAnswerer(openai_api_key='', all_tools=tools)

agent = qa.build_runner()

agent("How many benzene rings are there in 9H-Carbazole-3-carboxaldehyde? and what is sin(x)*exp(x)'s plot, what is it integrated from 0 to 1? ")
```

### 2.4 使用 Web Demo

1. 将您的插件添加到 web_demo.py 文件开头的映射中
2. 启动 webdemo

```bash
python web_demo.py
```

## 3. 使用定制工具

### 3.1 本地开发工具

如果要在本地开发工具，您需要编写一个 Python 函数来构建该工具并将其在注册表中进行注册。

例如，您可以编写一个工具来执行 Python 代码并返回结果。以下为示例代码：

```python
from bmtools.tools import Tool
from pydantic import BaseModel

class ExecutionQuery(BaseModel):
    code: str

class ExecutionResult(BaseModel):
    result: str

def build_python_tool(config) -> Tool:
    tool = Tool(
        "PythonTool",
        "A plugin that can execute python code",
        name_for_model="python",
        description_for_model="A plugin that can execute python code",
        contact_email="your@email",
    )

    @tool.post("/execute")
    def execute_python_code(query : ExecutionQuery) -> ExecutionResult:
        return ExecutionResult(
            result=eval(query.code)
        )
    
    return tool
```

然后，您需要使用以下代码将工具注册到注册表中：

```python
from bmtools.tools import register

@register("python")
def register_python_tool():
    return build_python_tool
```

在这里，我们将工具注册名称定为 “python”。

### 3.2 贡献到 BMTools

当您开发完一个工具后，您可以按照以下步骤将其贡献给 BMTools 仓库：

1. Fork 此存储库
2. 在 `bmtools/tools/{tool_name}` 中创建一个文件夹
3. 在该文件夹下添加 `api.py` 文件：`bmtools/tools/{tool_name}/api.py` 和一个 `__init__.py` 文件：`bmtools/tools/{tool_name}/__init__.py`
4. 使用 3.1 节中的代码在第 3 步创建的 `__init__.py` 文件中注册该工具
5. 在 `bmtools/tools` 的 `__init__.py` 文件中导入您的工具
6. 添加一个 `test.py` 文件以自动测试您的工具
7. 在您的文件夹中添加一个 `readme.md`，包含一个简短的工具介绍、贡献者信息或您想让其他人知道的任何信息。

## 4. 优化工具的提示信息

您编写的函数将被转换为与 OpenAI 插件兼容的接口。AI 模型将读取工具的名称、描述以及该工具所有的 API 的名称和描述。您可以在以下方面进行调整，以使您的 API 能够被 AI 模型更好地理解。

1. `name_for_model`（告诉模型这个工具是什么）

2. `description_for_model`（在调用工具之前将输入给模型，您可以在其中包含有关如何使用 API 的信息）

3. 每个 API 函数的函数名，以及 `@tool.get()` 中的名称。这两个名称最好能够匹配，因为工具名称在模型 API 选择中起着重要作用。

4. 函数的文档字符串（可以向模型建议是否使用此 API）

5. 函数的返回值，可在模型调用出错时为其提供报错信息，以指导其下一步操作，例如重试或指示应首选的下一步操作。

6.  减少 API 函数中的错误。

一个简单的例子是 [Wolfram Alpha API](https://github.com/OpenBMB/BMTools/tree/main/bmtools/tools/wolframalpha)，其可作为工具提示优化的参考。

## Citation

If you use BMTools in your research, please cite:

```bibtex
@misc{qin2023tool,
      title={Tool Learning with Foundation Models}, 
      author={Yujia Qin and Shengding Hu and Yankai Lin and Weize Chen and Ning Ding and Ganqu Cui and Zheni Zeng and Yufei Huang and Chaojun Xiao and Chi Han and Yi Ren Fung and Yusheng Su and Huadong Wang and Cheng Qian and Runchu Tian and Kunlun Zhu and Shihao Liang and Xingyu Shen and Bokai Xu and Zhen Zhang and Yining Ye and Bowen Li and Ziwei Tang and Jing Yi and Yuzhang Zhu and Zhenning Dai and Lan Yan and Xin Cong and Yaxi Lu and Weilin Zhao and Yuxiang Huang and Junxi Yan and Xu Han and Xian Sun and Dahai Li and Jason Phang and Cheng Yang and Tongshuang Wu and Heng Ji and Zhiyuan Liu and Maosong Sun},
      year={2023},
      eprint={2304.08354},
      archivePrefix={arXiv},
      primaryClass={cs.CL}
}
```
=======
<div style="text-align: center;">
    <h1><img src="docs/logo.png" height="28px" /> BMTools</h1>
</div>

BMTools is an open-source repository that extends language models using tools and serves as a platform for the community to build and share tools. In this repository, you can (1) easily build a plugin by writing python functions (2) use external ChatGPT-Plugins. 

This project is inspired by the open-source project [LangChain](https://github.com/hwchase17/langchain/) and optimized for the usage of open-sourced tools like [ChatGPT-Plugins](https://openai.com/blog/chatgpt-plugins), striving to achieve the open-source academic version of ChatGPT-Plugins.

Current version of BMTools is far from perfect, we will continue to improve it. 

## What's New
- 2023/4/14 [BabyAGI](https://github.com/yoheinakajima/babyagi) is supported in BMTools.

## 1. Setup

```bash
git clone git@github.com:OpenBMB/BMTools.git
python setup.py develop
```

## 2. Use existing tools

### 2.1 Set up tools

#### 2.1.1 Local tools
Add your api keys to secret_keys.sh, then start the local tools
```bash
source secret_keys.sh
python host_local_tools.py
```
Then use set the url of plugin to `http://127.0.0.1:8079/tools/{tool_name}/` (Remember the tailing `/`).

#### 2.1.2 Use online ChatGPT-Plugins

Just loaded it with the URL pointed to the `.well-known/ai-plugin.json`
For example, 
Set the url to `https://www.klarna.com/`, where `https://www.klarna.com/.well-known/ai-plugin.json` is a valid configuration. 

### 2.2 Use a single tool 

```python
from bmtools.agent.singletool import load_single_tools, STQuestionAnswerer

tool_name, tool_url = 'klarna',  'https://www.klarna.com/'
tool_name, tool_config = load_single_tools(tool_name, tool_url)
print(tool_name, tool_config)
stqa =  STQuestionAnswerer()

agent = stqa.load_tools(tool_name, tool_config)
agent("{Your Question}")
```

### 2.3 Use multiple tools
We can use multiple tools at the same time. Basically, the language model will do it recursively. It will treat the whole tool as an API, send questions to it, and the tool calls its sub-APIs to solve the question and send it back to parent tools. This functionality will be useful in the upcoming Chat mode.

Try this functionality using scripts like:

```python
from bmtools.agent.tools_controller import load_valid_tools, MTQuestionAnswerer
tools_mappings = {
    "klarna": "https://www.klarna.com/",
    "chemical-prop": "http://127.0.0.1:8079/tools/chemical-prop/",
    "wolframalpha": "http://127.0.0.1:8079/tools/wolframalpha/",
}

tools = load_valid_tools(tools_mappings)

qa =  MTQuestionAnswerer(openai_api_key='', all_tools=tools)

agent = qa.build_runner()

agent("How many benzene rings are there in 9H-Carbazole-3-carboxaldehyde? and what is sin(x)*exp(x)'s plot, what is it integrated from 0 to 1? ")
```

### 2.4 Use the web demo
1. Add your plugin to the mappings at beginning of web_demo.py

2. Start the webdemo
```bash
python web_demo.py
```




## 3. Use customized tools

### 3.1 Develop a tool locally

To develop a tool locally, you need to write a python function to build the tool and register it to the registry.

For example, you can write a tool that can execute python code and return the result. The following is a sample code:

```python
from bmtools.tools import Tool
from pydantic import BaseModel

class ExecutionQuery(BaseModel):
    code: str

class ExecutionResult(BaseModel):
    result: str

def build_python_tool(config) -> Tool:
    tool = Tool(
        "PythonTool",
        "A plugin that can execute python code",
        name_for_model="python", 
        description_for_model="A plugin that can execute python code",
        contact_email="your@email",
    )

    @tool.post("/execute")
    def execute_python_code(query : ExecutionQuery) -> ExecutionResult:
        return ExecutionResult(
            result=eval(query.code)
        )
    
    return tool
```

Then you need to register the tool to the registry using the following code:

```python
from bmtools.tools import register

@register("python")
def register_python_tool():
    return build_python_tool
```

Here we register the tool with the name `python`. 


### 3.2 Contributing to BMTools

After you have developed a tool, you can contribute it to BMTools by following the steps below:
1. Fork this repository
2. Create a folder in `bmtools/tools/{tool_name}`
3. Add an `api.py` to the folder: `bmtools/tools/{tool_name}/api.py` and a `__init__.py` to the folder: `bmtools/tools/{tool_name}/__init__.py`
4. Register the tool in the `__init__.py` file you created in step 3 using the code in section 3.1
5. Import your tool in the `__init__.py` file under bmtools/tools
6. Add a `test.py` to test your tool automatically
7. Add a `readme.md` in your folder containing a brief introduction, contributor information, or anything you want to let others know. 

## 4. Optimize your tool's prompt
The functions you wrote will be converted into an interface compatible with the OpenAI plugin. The AI models will read the name, description of the tools, and the name, descriptions of the APIs of that tools. You can adjust the following aspect to make your API better understood by AI models.

- (1) `name_for_model` (tells the model what the tool is) 
- (2) `description_for_model` (this will be displayed to the model before the tool is called, and you can include information on how to use the APIs) 
- (3) The function name for each API function, as well as the name in `@tool.get()`. It's best if these two names match, as the name plays an important role in the model's API selection. 
- (4) The function's doc string (can suggest to the model whether to use this API or not) 
- (5) The function's return value, which can provide the model with error messages to guide its next steps, such as retrying or indicating a preferred next step 
- (6) Reduce the errors in your API function.

A simple example to refer to is the [Wolfram Alpha API](./bmtools/tools/wolframalpha/).

## Citation

If you use BMTools in your research, please cite:

```bibtex
@misc{qin2023tool,
      title={Tool Learning with Foundation Models}, 
      author={Yujia Qin and Shengding Hu and Yankai Lin and Weize Chen and Ning Ding and Ganqu Cui and Zheni Zeng and Yufei Huang and Chaojun Xiao and Chi Han and Yi Ren Fung and Yusheng Su and Huadong Wang and Cheng Qian and Runchu Tian and Kunlun Zhu and Shihao Liang and Xingyu Shen and Bokai Xu and Zhen Zhang and Yining Ye and Bowen Li and Ziwei Tang and Jing Yi and Yuzhang Zhu and Zhenning Dai and Lan Yan and Xin Cong and Yaxi Lu and Weilin Zhao and Yuxiang Huang and Junxi Yan and Xu Han and Xian Sun and Dahai Li and Jason Phang and Cheng Yang and Tongshuang Wu and Heng Ji and Zhiyuan Liu and Maosong Sun},
      year={2023},
      eprint={2304.08354},
      archivePrefix={arXiv},
      primaryClass={cs.CL}
}
```

