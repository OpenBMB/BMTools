import requests
from pydantic import BaseModel
import numpy as np
from bs4 import BeautifulSoup
import json
from ...tool import Tool
from typing import List, Optional, Union

class GetNameResponse(BaseModel):
    
    """name list"""
    names: List[str]

class GetStructureResponse(BaseModel):
    
    """structure list"""
    state : int
    content : Optional[str] = None

class GetIDResponse(BaseModel):
    state : int
    content : Union[str, List[str]]


def build_tool(config) -> Tool:
    tool = Tool(
        "Chemical Property Plugin",
        description="looking up a chemical's property",
        name_for_model="Chemical Property",
        description_for_model="Plugin for looking up a chemical's property using a chemical knowledge base. All input should be a json like {'input': 'some input'}. Please use the provided questions and search step by step.",
        logo_url="https://your-app-url.com/.well-known/logo.png",
        contact_email="hello@contact.com",
        legal_info_url="hello@legal.com",
    )
    QRY = 'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/'

    @tool.get("/get_name")
    def get_name( cid: str ):
        """prints the possible 3 synonyms of the queried compound ID"""
        html_doc = requests.get(QRY+'cid/'+str(cid)+'/synonyms/XML').text
        soup = BeautifulSoup(html_doc,"html.parser",from_encoding="utf-8")
        syns = soup.find_all('synonym')
        ans = []
        kk = 3
        for syn in syns[:kk]:
            ans.append(syn.text)

        js = {'names':ans}
        return js

    @tool.get("/get_allname")
    def get_allname( cid: str ):
        """prints all the possible synonyms (might be too many, use this function carefully).
        """
        html_doc = requests.get(QRY+'cid/'+str(cid)+'/synonyms/XML').text
        soup = BeautifulSoup(html_doc,"html.parser",from_encoding="utf-8")
        syns = soup.find_all('synonym')
        ans = []
        for syn in syns:
            ans.append(syn.text)

        js = {'names':ans}
        return js

    @tool.get("/get_id_by_struct")
    def get_id_by_struct(smiles : str):
        """prints the ID of the queried compound SMILES. This should only be used if smiles is provided or retrieved in the previous step. The input should not be a string, but a SMILES formula.
        """
        html_doc = requests.get(QRY+'smiles/'+smiles+'/cids/XML').text
        soup = BeautifulSoup(html_doc,"html.parser",from_encoding="utf-8")
        cids = soup.find_all('cid')
        if cids is not None:#len(cids)==1:
            if len(cids)==1:
                ans = cids[0].text
                js = {'state': 'matched', 'content': ans}
                return js
        js = {'state': 'no result'}
        return js

    @tool.get("/get_id")
    def get_id(name : str):
        """prints the ID of the queried compound name, and prints the possible 5 names if the queried name can not been precisely matched,
        """

        html_doc = requests.get(QRY+'name/'+name+'/cids/XML').text
        soup = BeautifulSoup(html_doc,"html.parser",from_encoding="utf-8")
        cids = soup.find_all('cid')
        if cids is not None:#len(cids)==1:
            if len(cids)>0:
                ans = cids[0].text
                js = {'state':'precise', 'content':ans}
                return js
        html_doc = requests.get(QRY+'name/'+name+'/cids/XML?name_type=word').text
        soup = BeautifulSoup(html_doc,"html.parser",from_encoding="utf-8")
        cids = soup.find_all('cid')
        if len(cids) > 0:
            if name in get_name(cids[0].text, ifprint=0):
                ans = cids[0].text
                js = {'state':'precise', 'content':ans}
                return js
        ans = []
        seq = np.arange(len(cids))
        np.random.shuffle(seq)
        for sq in seq[:5]:
            cid = cids[sq]
            nms = get_name(cid.text, ifprint=0)
            ans.append(nms)
        js = {'state':'not precise', 'content':ans}
        print(js)
        return js

    @tool.get("/get_prop")
    def get_prop(cid : str):
        """prints the properties of the queried compound ID
        """
        html_doc = requests.get(QRY+'cid/'+cid+'/property/MolecularFormula,MolecularWeight,CanonicalSMILES,IsomericSMILES,IUPACName,XLogP,ExactMass,MonoisotopicMass,TPSA,Complexity,Charge,HBondDonorCount,HBondAcceptorCount,RotatableBondCount,HeavyAtomCount,CovalentUnitCount/json').text
        js = json.loads(html_doc)['PropertyTable']['Properties'][0]
        return js
    return tool
