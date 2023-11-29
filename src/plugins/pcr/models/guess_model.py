from dataclasses import dataclass, field
from io import BytesIO
from typing import Any, Optional

from .chara_model import Chara


@dataclass
class GuessGame:
    gid: int | str
    """参加游戏的小组ID"""
    winner: Optional[int | str]
    """胜利者ID"""


@dataclass
class AvatarGuessGame(GuessGame):
    """猜头像游戏"""

    q_image: BytesIO = field(repr=False)
    """题目图片"""
    answer: Chara
    """答案角色"""


@dataclass
class CardGuessGame(GuessGame):
    """猜卡面游戏"""

    image: BytesIO = field(repr=False)
    """题目图片"""
    answer: Chara
    """答案角色"""


@dataclass
class CharaGuessGame(GuessGame):
    """猜角色游戏"""

    profile: Any = field(repr=False)
    """题目档案"""
    answer: Chara
    """答案角色"""


@dataclass
class VoiceGuessGame(GuessGame):
    """猜语音游戏"""

    voice: BytesIO = field(repr=False)
    """题目语音"""
    answer: Chara
    """答案角色"""
