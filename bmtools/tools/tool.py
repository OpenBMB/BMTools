import fastapi
from typing import Optional
import copy

class Tool(fastapi.FastAPI):
    """ Tool is inherited from FastAPI class, thus:
    1. It can act as a server
    2. It has get method, you can use Tool.get method to bind a function to an url
    3. It can be easily mounted to another server
    4. It has a list of sub-routes, each route is a function

    Diagram:
    Root API server (ToolServer object)
    │     
    ├───── "./weather": Tool object
    │        ├── "./get_weather_today": function_get_weather(location: str) -> str
    │        ├── "./get_weather_forecast": function_get_weather_forcast(location: str, day_offset: int) -> str
    │        └── "...more routes"
    ├───── "./wikidata": Tool object
    │        ├── "... more routes"
    └───── "... more routes"
    """
    def __init__(
            self,
            tool_name : str,
            description : str,
            name_for_human : Optional[str] = None,
            name_for_model : Optional[str] = None,
            description_for_human : Optional[str] = None,
            description_for_model : Optional[str] = None,
            logo_url : Optional[str] = None,
            author_github : Optional[str] = None,
            contact_email : str = "",
            legal_info_url : str = "",
            version : str = "0.1.0",
        ):
        super().__init__(
            title=tool_name,
            description=description,
            version=version,
        )

        if name_for_human is None:
            name_for_human = tool_name
        if name_for_model is None:
            name_for_model = name_for_human
        if description_for_human is None:
            description_for_human = description
        if description_for_model is None:
            description_for_model = description_for_human
        
        self.api_info = {
            "schema_version": "v1",
            "name_for_human": name_for_human,
            "name_for_model": name_for_model,
            "description_for_human": description_for_human,
            "description_for_model": description_for_model,
            "auth": {
                "type": "none",
            },
            "api": {
                "type": "openapi",
                "url": "/openapi.json",
                "is_user_authenticated": False,
            },
            "author_github": author_github,
            "logo_url": logo_url,
            "contact_email": contact_email,
            "legal_info_url": legal_info_url,
        }

        @self.get("/.well-known/ai-plugin.json", include_in_schema=False)
        def get_api_info(request : fastapi.Request):
            openapi_path =  str(request.url).replace("/.well-known/ai-plugin.json", "/openapi.json")
            info = copy.deepcopy(self.api_info)
            info["api"]["url"] = str(openapi_path)
            return info
