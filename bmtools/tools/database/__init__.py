from bmtools.tools import register

@register("database")
def database():
    from .api import build_database_tool
    return build_database_tool