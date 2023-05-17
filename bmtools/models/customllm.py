#!/usr/bin/env python
# coding=utf-8
from langchain.llms.base import LLM
from typing import Optional, List, Mapping, Any
import requests, json

class CustomLLM(LLM):
    
    n: int = 0

    @property
    def _llm_type(self) -> str:
        return "custom"
    
    def _call(self, prompt, stop: Optional[List[str]] = None) -> str:
        headers = {
            "Content-Type": "application/json"
        }

        # Assume this is an url providing your customized LLM service, we use the openai api as an example.
        url = "http://47.254.22.102:8989/chat"
        
        if isinstance(prompt, str):
            message = [
                {"role": "system", "content": "You are a user what to consult the assistant."},
                {"role": "user", "content": prompt},
            ]
        else:
            message = prompt

        payload = {
            "model": "gpt-3.5-turbo",
            "messages": message,
            "max_tokens": 512,
            "frequency_penalty": 0,
            "presence_penalty": 0,
            "temperature": 0.0,
            "best_of": 3,
            "stop": stop,
        }
        try_times = 10
        while(try_times > 0):
            try:
                response = requests.post(url, json=payload, headers=headers)
                if isinstance(prompt, str):
                    output = json.loads(response.text)["choices"][0]["message"]["content"]
                else:
                    output = response.text
                break
            except:
                try_times -= 1
                continue
        if try_times == 0:
            raise RuntimeError("Your LLM service is not available.")

        print("\n--------------------")
        print(prompt)
        print("\n********************")
        print(output)
        print("\n--------------------")
        input()

        return output
    
    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        """Get the identifying parameters."""
        return {"n": self.n}
    
if __name__ == "__main__":
    llm = CustomLLM()
    print(llm("You are an task creation AI that uses the result of an execution agent to create new tasks with the following objective: What's the weather in Shanghai today? Should I bring an umbrella?, The last completed task has the result: According to the weather report, it is sunny in Shanghai today and there is no precipitation, so you do not need to bring an umbrella.. This result was based on this task description: Make a todo list about this objective: What's the weather in Shanghai today? Should I bring an umbrella?. These are incomplete tasks: . Based on the result, create new tasks to be completed by the AI system that do not overlap with incomplete tasks. Do not generate repetitive tasks (e.g., tasks that have already been completed). If there is not futher task needed to complete the objective, only return NO TASK. Now return the tasks as an array."))