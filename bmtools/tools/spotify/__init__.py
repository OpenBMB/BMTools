
from ..registry import register

@register("spotify")
def spotify():
    from .api import build_tool
    return build_tool
