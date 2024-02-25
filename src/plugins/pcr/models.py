from dataclasses import dataclass, field
from io import BytesIO
from typing import Any, Optional, TypedDict


@dataclass
class Chara:
    """PCR角色"""

    id: str
    """角色id"""
    star: int
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


class GachaTenjouResult(TypedDict):
    """PCR一井抽卡结果"""

    s3: list[Chara]
    """3星角色"""
    s2: list[Chara]
    """2星角色"""
    s1: list[Chara]
    """1星角色"""
    first_up_pos: int
    """第一次UP的位置"""
    up_num: int
    """UP次数"""
    hiishi: int
    """秘石数"""


class CollectionResult(TypedDict):
    """PCR收藏结果"""

    collection_img: BytesIO
    """收藏图片"""
    ranking_desc: str
    """排名"""
    rank_text: str
    """排名文字"""
    cards_num: str
    """卡片数"""
