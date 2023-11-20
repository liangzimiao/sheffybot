from pydantic import BaseModel, Extra

from ...config import pcr_config


class Config(BaseModel, extra=Extra.ignore):
    """Plugin Config Here"""

    plugin_cd: int = pcr_config.pcr_gacha_cd
    """抽卡cd 单位s"""
    plugin_limit: int = pcr_config.pcr_gacha_limit
    """抽卡限制次数"""


plugin_config = Config()
