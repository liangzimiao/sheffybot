from pathlib import Path

from pydantic import BaseModel, Extra

from ...config import pcr_config


class Config(BaseModel, extra=Extra.ignore):
    """Plugin Config Here"""

    plugin_data_path: Path = pcr_config.pcr_data_path / "guess"
    """插件数据路径"""
    plugin_is_reply: bool = pcr_config.pcr_portune_is_reply
    """Plugin Is Reply"""
    # 猜头像游戏配置
    avatar_patch_size: int = 32
    """猜头像裁剪尺寸"""
    avatar_one_turn_time: int = 20
    """猜头像一轮时间"""
    avatar_blacklist_id: list[int] = [1072, 1908, 4031, 9000]
    """猜头像黑名单"""
    # 猜卡面游戏配置
    card_pic_side_length: int = 180
    """猜卡面裁剪尺寸"""
    card_one_turn_time: int = 20
    """猜卡面一轮时间"""
    card_blacklist_id: list[int] = [
        1000,
        1073,
        1701,
        1907,
        1908,
        1909,
        1910,
        1911,
        1913,
        1914,
        1915,
        1916,
        1917,
        1918,
        1919,
        4031,
        9000,
        9601,
        9602,
        9603,
        9604,
    ]
    """猜卡面黑名单"""


plugin_config = Config()
