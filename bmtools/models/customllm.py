#!/usr/bin/env python
# coding=utf-8
from langchain.llms.base import LLM
from typing import Optional, List, Mapping, Any

class CustomLLM(LLM):
    
    n: int = 0

    @property
    def _llm_type(self) -> str:
        return "custom"
    
    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        output = "your customized response"

        return output
    
    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        """Get the identifying parameters."""
        return {"n": self.n}
    
if __name__ == "__main__":
    llm = CustomLLM()
    print(llm("You are an task creation AI that uses the result of an execution agent to create new tasks with the following objective: What's the weather in Shanghai today? Should I bring an umbrella?, The last completed task has the result: According to the weather report, it is sunny in Shanghai today and there is no precipitation, so you do not need to bring an umbrella.. This result was based on this task description: Make a todo list about this objective: What's the weather in Shanghai today? Should I bring an umbrella?. These are incomplete tasks: . Based on the result, create new tasks to be completed by the AI system that do not overlap with incomplete tasks. Do not generate repetitive tasks (e.g., tasks that have already been completed). If there is not futher task needed to complete the objective, only return NO TASK. Now return the tasks as an array."))