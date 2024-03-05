from pathlib import Path
from typing import Optional

from nonebot import get_driver
from pydantic import BaseModel, Extra


class Config(BaseModel, extra=Extra.ignore):
    """PCR Plugin Config Here"""

    # PCR 数据资源配置
    pcr_data_path: Path = Path(__file__).resolve().parent / "data"
    pcr_resources_path: Path = Path(__file__).resolve().parent / "resources"
    # PCR 代理配置
    pcr_proxy: Optional[str] = None
    # PCR 运势配置
    pcr_portune_limit: int = 1
    """每日限制次数"""
    pcr_portune_is_reply: bool = True
    """是否启用回复"""
    # PCR 更新配置
    pcr_update_is_auto: bool = True
    """是否自动更新卡池"""
    pcr_update_is_notice: bool = True
    """是否通知卡池更新"""
    # PCR 抽卡配置
    pcr_gacha_cd: int = 0
    """抽卡间隔时间"""
    pcr_gacha_limit: int = 0
    """每日限制次数"""
    # PCR WHOIS配置
    pcr_whois_is_reply: bool = True
    """是否启用回复"""
    pcr_whois_cd: int = 0
    """花名册间隔时间"""
    # PCR GUESS配置
    pcr_guess_is_reply: bool = False
    """是否启用回复"""
    pcr_avatar_patch_size: int = 32
    """猜头像裁剪尺寸"""
    pcr_avatar_one_turn_time: int = 20
    """猜头像一轮时间"""
    pcr_card_pic_side_length: int = 180
    """猜卡面裁剪尺寸"""
    pcr_card_one_turn_time: int = 20
    """猜卡面一轮时间"""
    pcr_desc_prepare_time: int = 5
    """准备时间"""
    pcr_desc_one_turn_time: int = 12
    """每轮间隔时间"""
    pcr_desc_turn_number: int = 5  # [<9]
    """单次游戏轮数"""
    # PCR 签到配置
    pcr_sign_is_preload: bool = False
    """是否预加载图片"""
    pcr_sign_col_num: int = 11
    """每行卡片数"""
    pcr_sign_bg_mode: int = 0  # 0: 下载好的背景 1: 随机网络背景
    """签到背景模式"""


global_config = get_driver().config
pcr_config = Config.parse_obj(global_config)
