from dataclasses import dataclass

from ..models import Chara


@dataclass
class WhoIsGuessResult:
    score: int
    """匹配度"""
    is_guess: bool
    """是否是猜测结果"""
    guess_name: str
    """匹配到的名字"""
    guess_chara: Chara
    """匹配到的角色"""
