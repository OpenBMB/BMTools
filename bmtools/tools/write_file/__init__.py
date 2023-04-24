
from ..registry import register

@register("write_file")
def write_file():
    from .api import build_tool
    return build_tool
