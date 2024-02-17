from dataclasses import dataclass, field
from io import BytesIO
from typing import Any, Literal, Optional


@dataclass
class Chara:
    """PCR角色"""

    id: str
    """角色id"""
    star: Literal[1, 3, 6]
    """角色星级"""
    equip: int
    """角色装备"""
    name: str
    """角色名字"""
    icon: Optional[BytesIO | bytes] = field(default=None, repr=False)
    """角色头像"""
    card: Optional[BytesIO | bytes] = field(default=None, repr=False)
    """角色卡面"""

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Chara):
            return self.id == other.id and self.name == other.name
        return False


@dataclass
class GuessGame:
    """PCR GUESS游戏"""

    gid: str
    """参加游戏的群组GID"""
    winner: Optional[str]
    """胜利者ID"""
    question: Any = field(repr=False)
    """题目内容"""
    answer: Chara
    """答案角色"""


@dataclass
class WhoIsGuessResult:
    """角色猜测结果"""

    is_guess: bool
    """是否是猜测结果"""
    guess_name: str
    """匹配到的名字"""
    guess_chara: Chara
    """匹配到的角色"""
    score: int
    """匹配度"""
