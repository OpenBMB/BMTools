from pathlib import Path
from ..tool import Tool


def build_tool(config) -> Tool:
    tool = Tool(
        "write_file",
        "Write file to disk",
        name_for_model="write_file",
        description_for_model="Plugin for writing file to disk",
        logo_url=None,
        contact_email=None,
        legal_info_url=None
    )
        
    @tool.get("/wrile_file")
    def write_file(file_path: str, text: str) -> str:
        '''write file to disk
        '''
        write_path = (
            Path(file_path)
        )
        try:
            write_path.parent.mkdir(exist_ok=True, parents=False)
            with write_path.open("w", encoding="utf-8") as f:
                f.write(text)
            return f"File written successfully to {file_path}."
        except Exception as e:
            return "Error: " + str(e)

    return tool
