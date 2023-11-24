import json
from pathlib import Path
from typing import TypedDict, Dict, List, NamedTuple, Union
from .chara_model import Chara


class GachaData(TypedDict):
    up_character: Chara
    name: str
    six_per: float
    five_per: float
    four_per: float

    up_limit: List[str]
    up_alert_limit: List[str]
    up_six_list: List[str]
    up_five_list: List[str]
    up_four_list: List[str]
