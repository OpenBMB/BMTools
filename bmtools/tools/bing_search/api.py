
import requests
from bs4 import BeautifulSoup
from ..tool import Tool
import os
from enum import Enum

subscription_key = os.getenv("BING_SUBSCRIPT_KEY", None)
if subscription_key is None:
    raise Exception("BING_SUBSCRIPT_KEY is not set")

endpoint = "https://api.bing.microsoft.com/v7.0/search"
mkt = 'en-US'
headers = { 'Ocp-Apim-Subscription-Key': subscription_key }

#  search result list chunk size
SEARCH_RESULT_LIST_CHUNK_SIZE = 3
#  result target page text chunk content length
RESULT_TARGET_PAGE_PER_TEXT_COUNT = 500

class Operation(Enum):
    PAGE_DOWN = 'A'
    PAGE_UP = 'B'
    GO_BACK = 'C'
    ADD_DIGEST = 'D'
    MERGE = 'E'
    LOAD_PAGE_1 = 'F'
    LOAD_PAGE_2 = 'G'
    LOAD_PAGE_3 = 'H'
    END = 'I'
    SEARCH = 'J'
    START = 'K'
    REJECT = 'L'
    TO_TOP = 'M'

class CONTENT_TYPE(Enum):
    SEARCH_RESULT = 0
    RESULT_TARGET_PAGE = 1

class ContentItem:
    def __init__(self, type: CONTENT_TYPE, data):
        self.type = type
        self.data = data

class DigestData:
    title: str
    desc: str
    chunkIndex: int

class Digest:
    datas: list
    checked: bool
    
class SessionData:
    topic = None
    content = []
    digests = []
    curResultChunk = 0
    curTargetPageResultChunk = 0
    
data = SessionData()

def build_tool(config) -> Tool:
    tool = Tool(
        "Bing_search",
        "Bing_search",
        name_for_model="Bing_search",
        name_for_human="Bing_search",
        description_for_model="""Perform Search on Bing Search engine.
Use search_top3(key: str) to get top 3 search results after input the key to search.
Use load_page_index(idx: int) to load the detailed page of the search result.""",
        description_for_human="Bing search API for browsing the internet and search for results.",
        logo_url="https://your-app-url.com/.well-known/logo.png",
        contact_email="hello@contact.com",
        legal_info_url="hello@legal.com"
    )

    @tool.get("/search_top3")
    def search_top3(key_words: str) -> str:
        """Search key words, return top 3 search results.
        """
        top3 = search_all(key_words)[:3]
        output = ""
        for idx, item in enumerate(top3):
            output += "page: " + str(idx+1) + "\n"
            output += "title: " + item['name'] + "\n"
            output += "summary: " + item['snippet'] + "\n"
        return output

    def search_all(key_words: str, data: SessionData = data) -> list:
        """Search key_words, return a list of class SearchResult.
        Keyword arguments:
        key_words -- key words want to search
        """
        try:
            result = requests.get(endpoint, headers=headers, params={'q': key_words, 'mkt': mkt }, timeout=10)
        except Exception:
            result = requests.get(endpoint, headers=headers, params={'q': key_words, 'mkt': mkt }, timeout=10)
        if result.status_code == 200:
            result = result.json()
            data.content = []
            data.content.append(ContentItem(CONTENT_TYPE.SEARCH_RESULT, result))
            data.curResultChunk = 0
        else:
            result = requests.get(endpoint, headers=headers, params={'q': key_words, 'mkt': mkt }, timeout=10)
            if result.status_code == 200:
                result = result.json()
                data.content = []
                data.content.append(ContentItem(CONTENT_TYPE.SEARCH_RESULT, result))
                data.curResultChunk = 0
            else:
                raise Exception('Platform search error.')
        # print(f'search time:{time.time() - start_time}s')
        return data.content[-1].data["webPages"]["value"]

    @tool.get("/load_page_index")
    def load_page_index(idx: str) -> str:
        """Load page detail of the search result indexed as 'idx', and return the content of the page.
        """
        idx = int(idx)
        href, text = load_page(idx-1)
        if len(text) > 500:
            return text[:500]
        else:
            return text

    def load_page(idx:int, data: SessionData = data):
        try:
            top = data.content[-1].data["webPages"]["value"]
            res = requests.get(top[idx]['url'], timeout=15)
            if res.status_code == 200:
                res.raise_for_status()
                res.encoding = res.apparent_encoding
                content = res.text
                soup = BeautifulSoup(content, 'html.parser')
                paragraphs = soup.find_all('p')
                page_detail = ""
                for p in paragraphs:
                    text = p.get_text().strip()
                    page_detail += text
                # trafilatura may be used to extract the main content of the page
                # import trafilatura
                # page_detail = trafilatura.extract(soup, timeout=60)
                return top[idx]['url'], page_detail
            else:
                return " ", "Timeout for loading this page, Please try to load another one or search again."
        except:
            return " ", "Timeout for loading this page, Please try to load another one or search again."
    
    return tool