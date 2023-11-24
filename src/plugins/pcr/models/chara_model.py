from dataclasses import dataclass
from io import BytesIO
from typing import Optional


@dataclass
class Chara:
    id: str
    """角色id"""
    star: int
    """角色星级"""
    equip: int
    """角色装备"""
    name: Optional[str] = None
    """角色名字"""
    icon: Optional[BytesIO | bytes] = None
    """角色头像"""
    card: Optional[BytesIO | bytes] = None
    """角色卡面"""
