from dataclasses import dataclass
from typing import Literal


@dataclass
class UpdateResult:
    is_success: bool
    """是否更新成功"""
    type_name: Literal["strategy", "pool", "chara"]
    """更新类型"""
    message: str
    """更新消息"""
