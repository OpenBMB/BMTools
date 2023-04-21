#!/usr/bin/env python
# coding=utf-8
from langchain.llms.base import LLM
from typing import Optional, List, Mapping, Any
from transformers import LlamaTokenizer, AutoModelForCausalLM

class LlamaModel(LLM):
    
    model_name: str = ""
    tokenizer: LlamaTokenizer = None
    model: AutoModelForCausalLM = None

    def __init__(self, huggingface_model_name: str) -> None:
        super().__init__()
        self.model_name = huggingface_model_name
        self.tokenizer = LlamaTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(self.model_name)
        if self.tokenizer.pad_token_id == None:
            self.tokenizer.add_special_tokens({"bos_token": "<s>", "eos_token": "</s>", "pad_token": "<pad>"})
        self.model.resize_token_embeddings(len(self.tokenizer))
        
    @property
    def _llm_type(self) -> str:
        return self.model_name
    
    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        inputs = self.tokenizer(
            prompt,
            padding=True,
            max_length=self.tokenizer.model_max_length,
            truncation=True,
            return_tensors="pt"
        )
        inputs_len = inputs["input_ids"].shape[1]
        generated_outputs = self.model.generate(
            input_ids=inputs["input_ids"], #.cuda(),
            attention_mask=inputs["attention_mask"], #.cuda(),
            max_new_tokens=50,
            eos_token_id=self.tokenizer.eos_token_id,
            bos_token_id=self.tokenizer.bos_token_id,
            pad_token_id=self.tokenizer.pad_token_id,
        )
        decoded_output = self.tokenizer.batch_decode(
            generated_outputs[..., inputs_len:], skip_special_tokens=True)
        output = decoded_output[0]
        return output
    
    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        """Get the identifying parameters."""
        return {"model_name": self.model_name}
    
if __name__ == "__main__":
    llm = LlamaModel("decapoda-research/llama-7b-hf")
    print(llm("Who are you?"))