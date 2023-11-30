from dataclasses import dataclass, field
from io import BytesIO
from typing import Optional

from .chara_model import Chara


@dataclass
class GuessGame:
    """GUESS游戏"""

    gid: int | str
    """参加游戏的小组ID"""
    winner: Optional[int | str]
    """胜利者ID"""
    answer: Chara
    """答案角色"""


@dataclass
class AvatarGuessGame(GuessGame):
    """猜头像游戏"""

    q_image: BytesIO = field(repr=False)
    """题目图片"""


@dataclass
class CardGuessGame(GuessGame):
    """猜卡面游戏"""

    q_image: BytesIO = field(repr=False)
    """题目图片"""


@dataclass
class DescGuessGame(GuessGame):
    """猜角色游戏"""

    profile: dict[str, str] = field(repr=False)
    """题目档案"""
