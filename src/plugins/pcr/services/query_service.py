import json
from pathlib import Path
from typing import Any

from ..config import pcr_config
from ..logger import PCRLogger as Logger

logger = Logger("PCR_QUERY")
type_list = [
    "rank",
    "activity",
    "equipment",
    "half_month",
    "gocha",
    "dragon",
    "strength",
]

"""
指令：
rank
活动攻略/sp/vh
刷图推荐
半月刊
千里眼
地下城
屯体
更新攻略缓存
"""


class QueryService:
    res_path = pcr_config.pcr_resources_path / "query"

    def __init__(self):
        pass

    async def get_gocha(self) -> tuple[Any, list[Path]]:
        path = self.res_path / "gocha"
        data = self.load_config(path)
        text: str = ""
        image_path_list: list[Path] = []
        for strategy in data:
            if strategy["text"]:
                text += strategy["text"]
            for image in strategy["image"]:
                image_path_list.append(path / image)
        return text, image_path_list

    async def get_rank(self):
        return None

    def load_config(self, path: Path) -> Any:
        try:
            with open(path / "route.json", encoding="utf8") as f:
                data = json.load(f)
                return data
        except Exception as e:
            logger.exception(f"{e}")
            return {}
