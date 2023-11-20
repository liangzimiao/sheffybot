from pydantic import BaseModel, Extra
from pathlib import Path
from nonebot import get_driver


class Config(BaseModel, extra=Extra.ignore):
    """Plugin Config Here"""

    # PCR资源数据配置
    pcr_data_path: Path = Path(__file__).resolve().parent / "data"
    pcr_resources_path: Path = Path(__file__).resolve().parent / "resources"
    # PCR运势配置
    pcr_portune_limit: int = 5
    pcr_portune_is_reply: bool = False
    # PCR更新配置
    pcr_update_is_auto: bool = True
    pcr_update_is_notice: bool = True
    # PCR抽卡配置
    pcr_gacha_cd: int = 0
    pcr_gacha_limit: int = 0


global_config = get_driver().config
pcr_config = Config.parse_obj(global_config)
