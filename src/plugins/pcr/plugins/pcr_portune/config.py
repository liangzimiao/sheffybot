from pydantic import BaseModel, Extra

from ...config import pcr_config


class Config(BaseModel, extra=Extra.ignore):
    """Plugin Config Here"""

    plugin_limit: int = pcr_config.pcr_portune_limit
    """Plugin Limit"""
    plugin_is_reply: bool = pcr_config.pcr_portune_is_reply
    """Plugin Is Reply"""


plugin_config = Config()
