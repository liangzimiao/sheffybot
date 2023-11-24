from dataclasses import dataclass

from ..models import Chara


@dataclass
class WhoIsGuessResult:
    score: int
    """匹配度"""
    guess_name: str
    """匹配到的名字"""
    guess_chara: Chara
    """匹配到的角色"""
