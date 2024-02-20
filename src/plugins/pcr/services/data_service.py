# -*- coding: utf-8 -*-

import asyncio
import difflib
import json
from io import BytesIO
from pathlib import Path
from typing import Any, Literal, Optional

import httpx
from fuzzywuzzy import fuzz
from PIL import Image

from ..config import pcr_config
from ..logger import PCRLogger as Logger
from ..models import Chara
from ..utils import merge_dicts, normalize_str

pcr_data_path: Path = pcr_config.pcr_data_path
"""PCR数据存放路径"""
pcr_res_path: Path = pcr_config.pcr_resources_path
"""PCR资源存放路径"""
online_pool_url = "https://api.redive.lolikon.icu/gacha/default_gacha.json"
"""默认UP卡池数据url"""
online_pool_ver_url = "https://api.redive.lolikon.icu/gacha/gacha_ver.json"
"""默认UP池版本号url"""
online_chara_name_url = "https://ghproxy.com/https://github.com/Ice9Coffee/LandosolRoster/blob/master/chara_name.json"
"""默认PCR角色名字数据url"""
online_chara_profile_url = "https://ghproxy.com/https://github.com/Ice9Coffee/LandosolRoster/blob/master/chara_profile.json"
"""默认PCR角色档案数据url"""
online_unavailable_chara_url = "https://ghproxy.com/https://github.com/Ice9Coffee/LandosolRoster/blob/master/unavailable_chara.json"
"""默认PCR不可用角色数据url"""
online_pcr_data_url = {
    "chara_name": online_chara_name_url,  # PCR角色名字数据url
    "chara_profile": online_chara_profile_url,  # PCR角色档案数据url
    "unavailable_chara": online_unavailable_chara_url,  # PCR不可用角色数据url
    "local_pool": online_pool_url,  # 默认UP卡池数据url
    "local_pool_ver": online_pool_ver_url,  # 默认UP池版本号url
}


class PCRDataService:
    """PCR数据服务"""

    CHARA_NAME: dict[str, list[str]] = {}
    """角色名字dict"""
    CHARA_PROFILE: dict[str, dict[str, str]] = {}
    """角色档案dict"""
    UNAVAILABLE_CHARA: list[int] = []
    """不可用角色list"""
    CHARA_ROSTER: dict[str, str] = {}
    """角色花名册dict"""
    LOCAL_POOL: dict[str, dict[str, Any]] = {}
    """本地卡池dict"""
    LOCAL_POOL_VER: dict[str, str] = {}
    """本地卡池版本号dict"""

    def __init__(self) -> None:
        pcr_res_path.mkdir(parents=True, exist_ok=True)
        pcr_data_path.mkdir(parents=True, exist_ok=True)
        self.load_pcr_res()

    def __repr__(self) -> str:
        return f"CHARA_NAME:{len(self.CHARA_NAME)}, PROFILE:{len(self.CHARA_PROFILE)}, ROSTER:{len(self.CHARA_ROSTER)}, POOL_VER:{self.LOCAL_POOL_VER.get('ver')}"

    async def load_pcr_data(self) -> None:
        """
        加载PCR本地数据并执行各种数据操作。
        """
        self._dict = {}
        for key in (
            "chara_name",
            "chara_profile",
            "unavailable_chara",
            "local_pool",
            "local_pool_ver",
        ):
            local_data = await self.get_local_pcr_data(key)
            if not self._dict.get(key) and local_data:
                self._dict[key] = local_data
            else:
                Logger(f"{key.upper()}").info("未检测到本地数据 将重新生成")
                await self.update_pcr_data(key)
                self._dict[key] = await self.get_local_pcr_data(key)
            self.CHARA_NAME = self._dict["chara_name"]
        self.CHARA_PROFILE = self._dict["chara_profile"]
        self.UNAVAILABLE_CHARA = self._dict["unavailable_chara"]
        self.LOCAL_POOL = self._dict["local_pool"]
        self.LOCAL_POOL_VER = self._dict["local_pool_ver"]
        self.CHARA_ROSTER = self.get_chara_roster()
        Logger("PCR_DATA").info(f"{self}")
        Logger("PCR_DATA").success("Succeeded to load PCR_DATA")

    async def get_online_pcr_data(
        self,
        types: Literal[
            "chara_name",
            "chara_profile",
            "local_pool",
            "local_pool_ver",
            "unavailable_chara",
        ],
    ) -> dict:
        """
        获取在线PCR数据
        """
        url = online_pcr_data_url[types]
        Logger(f"{types.upper()}").info(f"开始获取在线PCR数据:{types.upper()}")
        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(url=url, follow_redirects=True, timeout=30)
                if response.status_code == 200:
                    online_pcr_data = response.json()
                    Logger(f"{types.upper()}").info(
                        f"获取在线PCR数据:{types.upper()}成功"
                    )
                    return online_pcr_data
                else:
                    Logger(f"{types.upper()}").error(
                        f"获取在线PCR数据:{types.upper()}时发生错误{response.status_code}"
                    )
                    return {}
        except Exception as e:
            Logger(f"{types.upper()}").error(f"获取在线PCR数据时发生错误 {type(e)}")
            raise e

    async def get_local_pcr_data(
        self,
        types: Literal[
            "chara_name",
            "chara_profile",
            "local_pool",
            "local_pool_ver",
            "unavailable_chara",
        ],
    ) -> Any:
        """
        获取本地PCR数据。
        """
        try:
            with open(pcr_data_path / f"{types}.json", "r", encoding="utf-8") as file:
                # 尝试从指定文件路径读取并解析JSON数据
                data = json.load(file)
        except Exception:
            # 如果出现任何异常，返回空字典
            data = {}
        return data

    async def update_pcr_data(
        self,
        types: Literal[
            "chara_name",
            "chara_profile",
            "local_pool",
            "local_pool_ver",
            "unavailable_chara",
        ],
    ) -> None:
        """
        更新本地PCR数据
        """
        # 新数据
        new_data = {}  # 先定义好，不然可能会复用
        # 获取线上数据
        online_data = await self.get_online_pcr_data(types)
        if not online_data:
            return
        # 获取本地数据
        local_data = await self.get_local_pcr_data(types)
        # 对比数据
        if types == "chara_name":
            Logger(f"{types.upper()}").info("开始对比角色数据")
            new_data = merge_dicts(online_data, local_data)
        elif types == "chara_profile":
            Logger(f"{types.upper()}").info("已开始更新角色档案")
            for id in online_data:
                if (
                    id not in local_data
                    or len(local_data[id]) != len(online_data[id])  # 可能有不足
                ):
                    m = online_data[id]
                    new_data[id] = m
        elif types == "local_pool":
            # 备份本地卡池
            Logger(f"{types.upper()}").info("开始备份本地卡池")
            local_pool_backup = local_data
            with open(
                pcr_data_path / "local_pool_backup.json", "w", encoding="utf-8"
            ) as file:
                json.dump(local_pool_backup, file, indent=4, ensure_ascii=False)
            Logger(f"{types.upper()}").info("PCR_LOCAL_POOL 成功备份至本地")
            # 需要进行id转角色名的键
            ids_list = ["up", "star3", "star2", "star1"]
            # 服务器名称可能的键
            pool_name = {
                "BL": ["BL", "bl", "Bl", "bL", "CN", "cn"],
                "TW": ["TW", "tw", "so-net", "sonet"],
                "JP": ["JP", "jp"],
                "MIX": ["MIX", "mix", "Mix", "All", "all", "ALL"],
            }
            for server in pool_name:
                for online_pool_name in online_data:
                    if online_pool_name in pool_name[server]:
                        # 仅当命中时才更新卡池, 如果网站删除一个卡池, 更新后不会影响本地卡池
                        local_data[server] = online_data[online_pool_name]
                        # 检查UP角色是重复在star3中出现
                        if local_data[server]["up"]:
                            up_chara_id = local_data[server]["up"][0]
                            if up_chara_id in local_data[server]["star3"]:
                                local_data[server]["star3"].remove(up_chara_id)
                        # 角色名转id
                        for star in ids_list:
                            local_data[server][star] = pcr_data.ids2names(
                                local_data[server][star]
                            )
                            if not local_data[server][star]:
                                # MIX池会出现无UP角色的空列表, 然后偷偷换成我老婆
                                local_data[server][star] = ["镜华(万圣节)"]
                                Logger(f"{types.upper()}").debug(
                                    f"{server}卡池{star}列表为空, 已替换为镜华(万圣节)"
                                )
            new_data = local_data
        else:  # local_pool_ver, unavailable_chara
            new_data = online_data

        with open(pcr_data_path / f"{types}.json", "w", encoding="utf-8") as file:
            json.dump(new_data, file, indent=4, ensure_ascii=False)
        Logger(f"{types.upper()}").info(f"PCR_{types.upper()} 更新完成")

    def get_chara_roster(self) -> dict:
        """
        生成chara_roster数据
        """
        data = {}
        result = {"success": 0, "duplicate": 0}
        for idx, names in self.CHARA_NAME.items():
            for n in names:
                n = normalize_str(n)
                if n not in data:
                    data[n] = idx
                    result["success"] += 1
                else:
                    result["duplicate"] += 1
                    # Logger("CHARA_ROSTER").warning(
                    #    f"出现重名{n}于id{idx}与id{data[n]}相同"
                    # )
        Logger("CHARA_ROSTER").info(f"{result}")
        return data

    def load_pcr_res(self):
        """
        加载PCR资源
        """
        try:
            self.gadget_equip = Image.open(f"{pcr_res_path}/priconne/gadget/equip.png")
            self.gadget_star = Image.open(f"{pcr_res_path}/priconne/gadget/star.png")
            self.like = Image.open(f"{pcr_res_path}/priconne/gadget/like.png")
            self.dislike = Image.open(f"{pcr_res_path}/priconne/gadget/dislike.png")
            self.gadget_star_dis = Image.open(
                f"{pcr_res_path}/priconne/gadget/star_disabled.png"
            )
            self.gadget_star_pink = Image.open(
                f"{pcr_res_path}/priconne/gadget/star_pink.png"
            )
            self.unknown_path = f"{pcr_res_path}/priconne/unknown.png"
        except Exception as e:
            Logger("PCR_RES").error(f"加载PCR资源时发生错误:{e}")

    def ids2names(self, ids: list[int]) -> list:
        """
        根据ID转换为官方译名,为了与现行卡池兼容
        """

        res = [
            self.CHARA_NAME[str(id)][0]
            if str(id) in self.CHARA_NAME
            else None  # Logger("PCR_DATA").warning(f"缺少角色{id}的信息, 请注意更新静态资源")
            for id in ids
        ]
        return res


pcr_data = PCRDataService()


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

    async def get_chara(
        self,
        id: Optional[str] = None,
        name: Optional[str] = None,
        star: int = 3,
        equip: int = 0,
        need_icon: bool = False,
        need_card: bool = False,
    ) -> Chara:
        """
        根据提供的ID或名称、星级和装备等级创建一个新的Chara实例。

        Args:
            id (str, optional): 角色的ID。
            name (str, optional): 角色的名称。
            star (int, optional): 角色的星级。
            equip (int, optional): 角色的装备等级。默认为0。
            need_icon (bool, optional): 是否需要角色图标。默认为False。
            need_card (bool, optional): 是否需要角色卡面。默认为False。

        Returns:
            Chara: 具有指定ID、星级和装备等级的Chara类的新实例。
        """
        if (id is None) and (name is None):
            raise ValueError("需要提供角色ID或角色名称")
        if id:
            c = Chara(id, star, equip, name=pcr_data.CHARA_NAME[id][0])
        elif name:
            id = self.name2id(name)
            c = Chara(id, star, equip, name=pcr_data.CHARA_NAME[id][0])
        c.icon = await self.get_chara_icon(c.id, c.star) if need_icon else None
        c.card = (
            await self.get_chara_card(c.id, c.star)
            if need_card and c.star in (3, 6)
            else None
        )
        return c

    async def get_chara_icon(self, id: str, star: Optional[int] = None) -> BytesIO:
        if star is None:
            # 先从本地缓存中获取
            icon_path = self.icon_path / f"icon_unit_{id}61.png"
            if not icon_path.exists():
                icon_path = self.icon_path / f"icon_unit_{id}31.png"
            if not icon_path.exists():
                icon_path = self.icon_path / f"icon_unit_{id}11.png"
            if not icon_path.exists():
                # 本地没有，则从网络下载
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
                # 下载失败，使用缺省图标
                icon_path = pcr_data.unknown_path
            with open(icon_path, "rb") as f:
                # 返回图标数据
                return BytesIO(f.read())
        else:
            star = 3 if star not in (1, 3, 6) else star
            # 从指定的星级获取图标
            icon_path = self.icon_path / f"icon_unit_{id}{star}1.png"
            if icon_path.exists():
                with open(icon_path, "rb") as f:
                    return BytesIO(f.read())
            else:
                # 本地没有，则从网络下载
                await self.download_chara_img(id=id, star=star, type_="icon")
                if not icon_path.exists():
                    return await self.get_chara_icon(id=id)
            return await self.get_chara_icon(id=id, star=star)

    async def get_chara_card(self, id: str, star: Optional[int] = None) -> BytesIO:
        """
        根据指定的ID和星级获取角色卡面。
        """
        star = 3 if star not in (3, 6) else star
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
                # TODO: 这里应该返回一个默认卡面
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
            Logger(f"CHARA_{type_.upper()}").debug(f"Chara {id} {type_}已存在")
            return
        Logger(f"CHARA_{type_.upper()}").info(f"Downloading Chara {type_} from {url}")
        try:
            async with httpx.AsyncClient(verify=False) as client:
                rsp = await client.get(url, timeout=10)
            if 200 == rsp.status_code:
                img = Image.open(BytesIO(rsp.content))
                img.save(save_path)
                Logger(f"CHARA_{type_.upper()}").info(f"Saved to {save_path}")
            else:
                Logger(f"CHARA_{type_.upper()}").error(
                    f"Failed to download {url}. HTTP {rsp.status_code}"
                )
        except Exception as e:
            Logger(f"CHARA_{type_.upper()}").error(
                f"Failed to download {url}. {type(e)}"
            )

    @staticmethod
    async def download_chara_voice(id: str, star: int):
        """
        下载角色声音 # 失效中
        """
        url = f"https://redive.estertion.win/voice/chara/{id}{star}1.webm"
        save_path = pcr_res_path / "priconne" / "voice" / f"chara_{id}{star}1.webm"
        if save_path.exists():
            Logger("CHARA_VOICE").debug(f"Chara {id} voice 已存在")
            return
        Logger("CHARA_VOICE").info(f"Downloading Chara voice from {url}")
        try:
            async with httpx.AsyncClient(verify=False) as client:
                rsp = await client.get(url, timeout=10)
                if 200 == rsp.status_code:
                    with open(save_path, "wb") as f:
                        f.write(rsp.content)
                    Logger("CHARA_VOICE").info(f"Saved to {save_path}")
                else:
                    Logger("CHARA_VOICE").error(
                        f"Failed to download {url}. HTTP {rsp.status_code}"
                    )
        except Exception as e:
            Logger("CHARA_VOICE").error(f"Failed to download {url}. {type(e)}")

    @staticmethod
    def is_npc(id_: str) -> bool:
        """
        判断给定的id是否为NPC角色

        参数：
        id_ (str): 角色的id

        返回值：
        bool: 如果是NPC角色则返回True，否则返回False
        """
        if id_ in pcr_data.UNAVAILABLE_CHARA:
            return True
        else:
            return not ((1000 < int(id_) < 1214) or (1700 < int(id_) < 1900))

    @staticmethod
    def match(
        query: str, choices: list[str] = list(pcr_data.CHARA_ROSTER.keys())
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
            choices = list(pcr_data.CHARA_ROSTER.keys())
        query = normalize_str(query)
        match = difflib.get_close_matches(query, choices, 1, cutoff=0.6)
        if match:
            match = match[0]
        else:
            match = choices[0]
        score = fuzz.ratio(query, match)
        Logger("CHARA_MATCH").debug(f"匹配结果 {match} 相似度{score}")
        return match, score

    @staticmethod
    def name2id(name) -> str:
        """
        根据给定的名称转换成对应的ID。
        """
        name = normalize_str(name)
        return (
            pcr_data.CHARA_ROSTER[name]
            if name in pcr_data.CHARA_ROSTER
            else CharaDataService.UNKNOWN
        )


chara_data = CharaDataService()


if __name__ == "__main__":
    tasks = [
        pcr_data.get_online_pcr_data("chara_name"),
        pcr_data.get_online_pcr_data("chara_profile"),
        pcr_data.get_online_pcr_data("local_pool"),
        pcr_data.get_online_pcr_data("local_pool_ver"),
        pcr_data.get_online_pcr_data("unavailable_chara"),
    ]
    res = asyncio.run(*tasks)
