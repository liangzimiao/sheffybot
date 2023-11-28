from dataclasses import dataclass
from io import BytesIO
from typing import Any, Optional

from .chara_model import Chara


@dataclass
class GuessGame:
    gid: int | str
    """参加游戏的小组ID"""
    winner: Optional[int | str] = None
    """胜利者ID"""
    answer: Optional[Chara] = None
    """答案角色"""


@dataclass
class AvatarGuessGame(GuessGame):
    """猜头像游戏"""

    image: Optional[BytesIO] = None
    """题目图片"""


@dataclass
class CardGuessGame(GuessGame):
    """猜卡牌游戏"""

    image: Optional[BytesIO] = None
    """题目图片"""


@dataclass
class CharaGuessGame(GuessGame):
    """猜角色游戏"""

    profile: Optional[Any] = None
    """题目档案"""


@dataclass
class VoiceGuessGame(GuessGame):
    """猜语音游戏"""

    voice: Optional[BytesIO] = None
    """题目语音"""
