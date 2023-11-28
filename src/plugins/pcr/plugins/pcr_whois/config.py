from pydantic import BaseModel, Extra

from ...config import pcr_config


class Config(BaseModel, extra=Extra.ignore):
    """Plugin Config Here"""

    plugin_is_reply: bool = pcr_config.pcr_whois_is_reply
    """是否启用回复"""
    plugin_cd: int = pcr_config.pcr_whois_cd
    """花名册间隔时间"""


plugin_config = Config()
