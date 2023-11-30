# -*- coding: utf-8 -*-

import asyncio
import difflib
from io import BytesIO
from pathlib import Path
from typing import Literal, Optional, overload

import httpx
from fuzzywuzzy import fuzz
from loguru import logger
from PIL import Image

from ...config import pcr_config
from ...models import Chara
from .pcr_data_service import pcr_data
from .util import normalize_str

pcr_data_path: Path = pcr_config.pcr_data_path
"""PCR数据存放路径"""
pcr_res_path: Path = pcr_config.pcr_resources_path
"""PCR资源存放路径"""

UnavailableChara = {
    "1000",  # 未知
    "1069",  # 霸瞳
    "1072",  # 可萝爹
    "1073",  # 拉基拉基
    "1102",  # 泳装大眼
    "1183",  # 星弓星
    "1184",  # 星弓栞
    "1194",
    "1195",
    "1196",
    "1197",
    "1200",
    "1201",
    "1202",
    "1203",  # (未实装)
    "1204",  # "美美(小小甜心)"
    "1205",  # "禊(小小甜心)"
    "1206",  # "镜华(小小甜心)"
}


class CharaDataService:
    """CHARA数据服务"""

    UNKNOWN = "1000"

    def __init__(self):
        self.card_path = pcr_res_path / "priconne" / "card"
        self.icon_path = pcr_res_path / "priconne" / "icon"
        self.voice_path = pcr_res_path / "priconne" / "voice"
        self.card_path.mkdir(parents=True, exist_ok=True)
        self.icon_path.mkdir(parents=True, exist_ok=True)
        self.voice_path.mkdir(parents=True, exist_ok=True)

    def get_chara_from_id(
        self,
        id_: str,
        star: Literal[1, 3, 6] = 3,
        equip: int = 0,
    ) -> Chara:
        """
        根据提供的ID、星级和装备等级创建一个新的Chara实例。

        参数:
            id_ (str): 角色的ID。
            star (int, 可选): 角色的星级。默认为3。
            equip (int, 可选): 角色的装备等级。默认为0。
        返回值:
            Chara: 具有指定ID、星级和装备等级的Chara类的新实例。
        """
        c = Chara(id_, star, equip, name=pcr_data.CHARA_NAME[id_][0])
        return c

    def get_chara_from_name(
        self,
        name,
        star: Literal[1, 3, 6] = 3,
        equip: int = 0,
    ) -> Chara:
        """
        根据角色名称、星级和装备等级创建一个新的角色实例。

        参数:
            name (str): 角色的名称。
            star (int): 角色的星级。默认为3。
            equip (int): 角色的装备等级。默认为0。

        返回值:
            Chara: 具有指定名称、星级和装备等级的角色实例。
        """
        id_ = self.name2id(name)
        return self.get_chara_from_id(id_, star, equip)

    # 将上面两种生成角色的方法合并

    @overload
    async def get_chara_icon(self, id: str) -> BytesIO:
        """
        获取给定ID的角色图标。

        参数:
            id (str): 角色的ID。

        返回:
            BytesIO: 角色图标作为BytesIO对象。
        """
        ...

    @overload
    async def get_chara_icon(self, id: str, star: Literal[1, 3, 6]) -> BytesIO:
        """
        获取指定ID和星级的角色图标。

        参数:
            id (str): 角色的ID。
            star (int): 角色的星级。

        返回:
            BytesIO: 角色图标的字节流对象。
        """
        ...

    async def get_chara_icon(
        self, id: str, star: Optional[Literal[1, 3, 6]] = None
    ) -> BytesIO:
        if star is None:
            icon_path = self.icon_path / f"icon_unit_{id}61.png"
            if not icon_path.exists():
                icon_path = self.icon_path / f"icon_unit_{id}31.png"
            if not icon_path.exists():
                icon_path = self.icon_path / f"icon_unit_{id}11.png"
            if not icon_path.exists():
                await asyncio.gather(
                    self.download_chara_img(id=id, star=6, type_="icon"),
                    self.download_chara_img(id=id, star=3, type_="icon"),
                    self.download_chara_img(id=id, star=1, type_="icon"),
                )
                icon_path = self.icon_path / f"icon_unit_{id}61.png"
            if not icon_path.exists():
                icon_path = self.icon_path / f"icon_unit_{id}31.png"
            if not icon_path.exists():
                icon_path = self.icon_path / f"icon_unit_{id}11.png"
            if not icon_path.exists():
                icon_path = self.icon_path / f"icon_unit_{self.UNKNOWN}.png"
            with open(icon_path, "rb") as f:
                return BytesIO(f.read())
        else:
            icon_path = self.icon_path / f"icon_unit_{id}{star}1.png"
            if icon_path.exists():
                with open(icon_path, "rb") as f:
                    return BytesIO(f.read())
            else:
                await self.download_chara_img(id=id, star=star, type_="icon")
                if not icon_path.exists():
                    return await self.get_chara_icon(id=id)
            return await self.get_chara_icon(id=id, star=star)

    async def get_chara_card(self, id: str, star: Literal[3, 6]) -> BytesIO:
        card_path = self.card_path / f"card_full_{id}{star}1.png"
        # 检查图片是否已经下载
        if card_path.exists():
            # 打开图片并返回BytesIO
            with open(card_path, "rb") as f:
                return BytesIO(f.read())
        else:
            # 如果没有下载,则先下载再返回
            await self.download_chara_img(id=id, star=star, type_="card")
            if not card_path.exists():
                return await self.get_chara_card(id=id, star=3)
            # 重新打开图片并返回BytesIO
            return await self.get_chara_card(id=id, star=star)

    @staticmethod
    async def download_chara_img(id: str, star: int, type_: Literal["card", "icon"]):
        """
        从指定的URL下载角色图像并将其保存到本地。

        参数:
            id (str): 角色的ID。
            star (int): 角色的星级。
            type_ (Literal["card", "icon"]): 要下载的图像类型，可以是"card"或"icon"。

        异常:
            Exception: 如果下载过程中出现错误。
        """
        if type_ == "icon":
            url = f"https://redive.estertion.win/icon/unit/{id}{star}1.webp"
            save_path = (
                pcr_res_path / "priconne" / "icon" / f"icon_unit_{id}{star}1.png"
            )
        elif type_ == "card":
            url = f"https://redive.estertion.win/card/full/{id}{star}1.webp"
            save_path = (
                pcr_res_path / "priconne" / "card" / f"card_full_{id}{star}1.png"
            )

        if save_path.exists():
            logger.debug(f"Chara {id} {type_}已存在")
            return
        logger.debug(f"Downloading Chara {type_} from {url}")
        try:
            async with httpx.AsyncClient(verify=False) as client:
                rsp = await client.get(url, timeout=10)
            if 200 == rsp.status_code:
                img = Image.open(BytesIO(rsp.content))
                img.save(save_path)
                logger.info(f"Saved to {save_path}")
            else:
                logger.error(f"Failed to download {url}. HTTP {rsp.status_code}")
        except Exception as e:
            logger.error(f"Failed to download {url}. {type(e)}")

    @staticmethod
    async def download_chara_voice(id: str, star):
        """
        下载角色声音
        """
        url = f"https://redive.estertion.win/voice/chara/{id}{star}1.webm"
        save_path = pcr_res_path / "priconne" / "voice" / f"chara_{id}{star}1.webm"
        if save_path.exists():
            logger.debug(f"Chara {id} voice 已存在")
            return
        logger.debug(f"Downloading Chara voice from {url}")
        try:
            async with httpx.AsyncClient(verify=False) as client:
                rsp = await client.get(url, timeout=10)
                if 200 == rsp.status_code:
                    with open(save_path, "wb") as f:
                        f.write(rsp.content)
                    logger.info(f"Saved to {save_path}")
                else:
                    logger.error(f"Failed to download {url}. HTTP {rsp.status_code}")
        except Exception as e:
            logger.error(f"Failed to download {url}. {type(e)}")

    @staticmethod
    def is_npc(id_: str) -> bool:
        """
        判断给定的id是否为NPC角色

        参数：
        id_ (str): 角色的id

        返回值：
        bool: 如果是NPC角色则返回True，否则返回False
        """
        if id_ in UnavailableChara:
            return True
        else:
            return not ((1000 < int(id_) < 1214) or (1700 < int(id_) < 1900))

    @staticmethod
    def match(
        query: str, choices: list[str] = list(pcr_data.CHARA_NAME_ID.keys())
    ) -> tuple[str, int]:
        """
        匹配给定的查询字符串和选项列表，并返回最佳匹配项及其相似度评分。

        参数：
            query (str)：要匹配的查询字符串。
            choices (list)：要与之匹配的选项列表。

        返回：
            tuple：包含最佳匹配项（str）和相似度评分（int）的元组。
        """
        if not choices:
            choices = list(pcr_data.CHARA_NAME_ID.keys())
        query = normalize_str(query)
        match = difflib.get_close_matches(query, choices, 1, cutoff=0.6)
        if match:
            match = match[0]
        else:
            match = choices[0]
        score = fuzz.ratio(query, match)
        logger.debug(f"匹配结果 {match} 相似度{score}")
        return match, score

    @staticmethod
    def name2id(name) -> str:
        """
        根据给定的名称转换成对应的ID。
        """
        name = normalize_str(name)
        return (
            pcr_data.CHARA_NAME_ID[name]
            if name in pcr_data.CHARA_NAME_ID
            else CharaDataService.UNKNOWN
        )


chara_data = CharaDataService()
