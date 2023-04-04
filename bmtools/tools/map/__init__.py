
from ..registry import register

@register("map")
def map():
    from .api import build_tool
    return build_tool
