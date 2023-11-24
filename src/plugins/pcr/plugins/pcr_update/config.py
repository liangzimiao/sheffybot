from pydantic import BaseModel, Extra

from ...config import pcr_config


class Config(BaseModel, extra=Extra.ignore):
    """Plugin Config Here"""

    plugin_is_auto: bool = pcr_config.pcr_update_is_auto
    """是否自动更新卡池"""
    plugin_is_notice: bool = pcr_config.pcr_update_is_notice
    """是否通知卡池更新"""


plugin_config = Config()
