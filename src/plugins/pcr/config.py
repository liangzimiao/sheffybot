from pathlib import Path

from nonebot import get_driver
from pydantic import BaseModel, Extra


class Config(BaseModel, extra=Extra.ignore):
    """Plugin Config Here"""

    # PCR 资源数据配置
    pcr_data_path: Path = Path(__file__).resolve().parent / "data"
    pcr_resources_path: Path = Path(__file__).resolve().parent / "resources"
    # PCR 运势配置
    pcr_portune_limit: int = 5
    pcr_portune_is_reply: bool = False
    # PCR 更新配置
    pcr_update_is_auto: bool = True
    pcr_update_is_notice: bool = True
    # PCR 抽卡配置
    pcr_gacha_cd: int = 0
    pcr_gacha_limit: int = 0
    # PCR WHOIS配置
    pcr_whois_is_reply: bool = False
    pcr_whois_cd: int = 0
    # PCR GUESS配置
    pcr_guess_is_reply: bool = False


global_config = get_driver().config
pcr_config = Config.parse_obj(global_config)
