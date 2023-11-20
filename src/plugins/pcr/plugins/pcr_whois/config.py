from pydantic import BaseModel, Extra

from ...config import pcr_config


class Config(BaseModel, extra=Extra.ignore):
    """Plugin Config Here"""

    plugin_is_auto: bool = pcr_config.pcr_update_is_auto
    plugin_is_notice: bool = pcr_config.pcr_update_is_notice


plugin_config = Config()
