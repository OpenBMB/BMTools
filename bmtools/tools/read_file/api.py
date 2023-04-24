from pathlib import Path
from ..tool import Tool


def build_tool(config) -> Tool:
    tool = Tool(
        "read_file",
        "Read file from disk",
        name_for_model="read_file",
        description_for_model="Plugin for reading file from disk",
        logo_url=None,
        contact_email=None,
        legal_info_url=None
    )
        
    @tool.get("/read_file")
    def read_file(file_path: str) -> str:
        '''read file from disk
        '''
        read_path = (
            Path(file_path)
        )
        try:
            with read_path.open("r", encoding="utf-8") as f:
                content = f.read()
            return content
        except Exception as e:
            return "Error: " + str(e)

    return tool
