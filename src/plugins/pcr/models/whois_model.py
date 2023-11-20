from dataclasses import dataclass


@dataclass
class WhoIsGuessResult:
    is_guess: bool
    """是否为猜测结果"""
    probability: int
    """可能性"""
    guess_name: str
    """匹配到的名字"""
