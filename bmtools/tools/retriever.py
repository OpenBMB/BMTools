from langchain.embeddings import OpenAIEmbeddings
from typing import List, Dict
from queue import PriorityQueue
import os

class Retriever:
    def __init__(self,
                 openai_api_key: str = None,
                 model: str = "text-embedding-ada-002"):
        if openai_api_key is None:
            openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.embed = OpenAIEmbeddings(openai_api_key=openai_api_key, model=model)
        self.documents = dict()

    def add_tool(self, tool_name: str, api_info: Dict) -> None:
        if tool_name in self.documents:
            return
        document = api_info["name_for_model"] + ". " + api_info["description_for_model"]
        document_embedding = self.embed.embed_documents([document])
        self.documents[tool_name] = {
            "document": document,
            "embedding": document_embedding[0]
        }

    def query(self, query: str, topk: int = 3) -> List[str]:
        query_embedding = self.embed.embed_query(query)

        queue = PriorityQueue()
        for tool_name, tool_info in self.documents.items():
            tool_embedding = tool_info["embedding"]
            tool_sim = self.similarity(query_embedding, tool_embedding)
            queue.put([-tool_sim, tool_name])

        result = []
        for i in range(min(topk, len(queue.queue))):
            tool = queue.get()
            result.append(tool[1])

        return result

    def similarity(self, query: List[float], document: List[float]) -> float:
        return sum([i * j for i, j in zip(query, document)])

if __name__ == "__main__":
    openai_api_key = "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"
    model = "text-embedding-ada-002"

    retriever = Retriever(openai_api_key=openai_api_key, model=model)

    tool_set = {
        "douban": {
            "schema_version": "v1",
            "name_for_human": "Film Search Plugin",
            "name_for_model": "Film Search",
            "description_for_human": "search for up-to-date film information.",
            "description_for_model": "Plugin for search for up-to-date film information.",
        },
        "baidu": {
            "schema_version": "v1",
            "name_for_human": "Translator Info",
            "name_for_model": "Translator",
            "description_for_human": "Translate a given text from one language to another.",
            "description_for_model": "Plugin for translating text from one language to another.",
        }
    }

    query = "I need some films."

    for tool_name, tool_info in tool_set.items():
        retriever.add_tool(tool_name, tool_info)

    result = retriever.query(query)
    print(result)