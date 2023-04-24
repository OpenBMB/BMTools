
from ..registry import register

@register("read_file")
def read_file():
    from .api import build_tool
    return build_tool
