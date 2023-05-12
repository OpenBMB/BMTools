
from ..registry import register

@register("map")
def map():
    from .api import build_tool
    return build_tool

@register("baidu_map")
def baidu_map():
    from .baidu_api import build_tool
    return build_tool
