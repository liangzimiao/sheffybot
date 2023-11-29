from dataclasses import dataclass, field
from io import BytesIO
from typing import Literal, Optional


@dataclass
class Chara:
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
