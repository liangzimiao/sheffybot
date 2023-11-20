# -*- coding: utf-8 -*-
import ast
import asyncio
import difflib
import json
import httpx
import unicodedata
import zhconv

from loguru import logger
from fuzzywuzzy import fuzz
from pathlib import Path
from typing import Any, Dict, List


from ...models import Chara
from ...config import pcr_config

pcr_data_path: Path = pcr_config.pcr_data_path
pcr_res_path: Path = pcr_config.pcr_resources_path


online_pool_url = "https://api.redive.lolikon.icu/gacha/default_gacha.json"
online_pool_ver_url = "https://api.redive.lolikon.icu/gacha/gacha_ver.json"
online_pcr_data_url = "https://api.redive.lolikon.icu/gacha/unitdata.py"
online_pcr_data_url2 = "https://ghproxy.com/https://github.com/Ice9Coffee/LandosolRoster/blob/master/_pcr_data.py"


def sort_priority(values, group):
    """
    根据给定的分组优先级对值列表进行排序。
    """
    def helper(x):
        if x in group:
            return 0, x
        return 1, x

    values.sort(key=helper)

def normalize_str(string) -> str:
    """
    规范化unicode字符串 并 转为小写 并 转为简体
    """
    string = unicodedata.normalize("NFKC", string)
    string = string.lower()
    string = zhconv.convert(string, "zh-hans")
    return string

def set_default(obj):
    """
    将一个集合对象转换为列表。

    参数:
        obj (set): 要转换的集合对象。

    返回值:
        list: 如果输入是一个集合对象，则返回转换后的列表对象，否则返回原始输入对象。
    """
    if isinstance(obj, set):
        return list(obj)
    return obj


class PCRDataService:
    """PCR常用的数据服务"""

    data_path: Path = pcr_data_path
    """PCR数据存放路径"""
    res_path: Path = pcr_res_path
    """PCR资源存放路径"""
    _chara_name: Dict[str, list[str]] = {}
    _chara_name_id: Dict[str, str] = {}
    _chara_profile: Dict[str, dict[str, str]] = {}
    _local_pool: Dict[str, Dict[str, Any]] = {}
    _local_pool_ver: Dict[str, str] = {}
    _local_pool_backup: Dict[str, Dict[str, Any]] = {}

    @property
    def chara_name(self) -> Dict[str, list[str]]:
        """角色id与别名列表"""
        return self._chara_name.copy() if self._chara_name else self.get_chara_name()

    @property
    def chara_name_id(self) -> Dict[str, str]:
        """角色名字与id唯一对应表"""
        return (
            self._chara_name_id.copy()
            if self._chara_name_id
            else self.get_chara_name_id()
        )

    @property
    def chara_profile(self) -> Dict[str, Dict[str, str]]:
        """角色档案"""
        return (
            self._chara_profile.copy()
            if self._chara_profile
            else self.get_chara_profile()
        )

    @property
    def local_pool(self) -> Dict[str, Dict[str, Any]]:
        """本地卡池"""
        return self._local_pool.copy() if self._local_pool else self.get_local_pool()

    @property
    def local_pool_ver(self) -> Dict[str, str]:
        """本地版号"""
        return (
            self._local_pool_ver.copy()
            if self._local_pool_ver
            else self.get_local_pool_ver()
        )

    def __init__(self) -> None:
        pcr_res_path.mkdir(parents=True, exist_ok=True)
        pcr_data_path.mkdir(parents=True, exist_ok=True)
        pass

    def load_data(self) -> None:
        """
        加载数据
        检查文件是否存在以及能否正确读取
        读取为空则启动对应的更新方法重新生成
        """
        if (
            self.chara_profile
            and self.chara_name
            and self.local_pool
            and self.local_pool_ver
        ):
            ver = self.local_pool_ver["ver"]
            logger.success("成功加载PCR_DATA全部数据")
            logger.success(f"CHARA_NAME:{len(self.chara_name)}")
            logger.success(f"CHARA_PROFILE:{len(self.chara_profile)}")
            logger.success(f"LOCAL_POOL_VER:{ver}")
            return
        if not self.chara_name:
            logger.info("未检测到PCR_CHARA_NAME数据 将重新生成")
            asyncio.create_task(self.update_chara_name(), name="update_chara_name")
        if not self.chara_profile:
            logger.info("未检测到PCR_CHARA_PROFILE数据 将重新生成")
            asyncio.create_task(
                self.update_chara_profile(), name="update_chara_profile"
            )
        if not self.local_pool:
            logger.info("未检测到PCR_LOCAL_POOL数据 将重新生成")
            asyncio.create_task(self.update_local_pool(), name="update_local_pool")
        if not self.local_pool_ver:
            logger.info("未检测到PCR_LOCAL_POOL_VER数据 将重新生成")
            asyncio.create_task(
                self.update_local_pool_ver(), name="update_local_pool_ver"
            )

    async def update_chara_name(self) -> None:
        """
        对比本地和远程的_pcr_data.py, 自动补充本地没有的角色信息, 已有角色信息进行补全
        """
        # 获取线上角色信息
        online1 = await self.get_online_chara_name(url=online_pcr_data_url)
        online2 = await self.get_online_chara_name(url=online_pcr_data_url2)
        online_chara_name = self.merge_dicts(online2, online1)
        if (not online2) or (not online1):
            logger.warning("online_chara_name is None")
            return
        # 获取本地角色信息
        local_chara_name = self.chara_name
        logger.info("开始对比角色数据")
        result = self.merge_dicts(online_chara_name, local_chara_name, is_info=True)
        # 保存新数据
        PCRDataService._chara_name = result
        self._save_chara_name()
        logger.success("PCR_CHARA_NAME 更新完成")

    async def update_chara_profile(self) -> None:
        """
        对比本地和远程的_pcr_data.py, 自动补充本地没有的角色档案, 已有角色档案进行补全
        """
        # 获取线上角色档案
        online_chara_profile = await self.get_online_chara_profile()
        if not online_chara_profile:
            logger.warning("online_chara_profile is None")
            return
        # 获取本地角色档案
        local_chara_profile = self.chara_profile
        logger.info("开始对比角色档案")
        for id in online_chara_profile:
            if (
                id not in local_chara_profile
                or len(local_chara_profile[id])
                != len(online_chara_profile[id])  # 可能有不足
            ):
                logger.info(f"已开始更新角色{id}的档案")
                m = online_chara_profile[id]
                local_chara_profile[id] = m
        # 保存新数据
        PCRDataService._chara_profile = local_chara_profile
        self._save_chara_profile()
        logger.success("PCR_CHARA_PROFILE 更新完成")

    async def update_local_pool(self) -> None:
        """
        更新本地卡池文件, 并备份原卡池
        """
        # 获取线上卡池
        online_pool = await self.get_online_pool(url=online_pool_url)
        # 获取本地卡池
        local_pool = self.local_pool
        # 备份本地卡池
        logger.info("开始备份本地卡池")
        PCRDataService._local_pool_backup = local_pool
        self._save_local_pool_backup()

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
            for online_pool_name in online_pool:
                if online_pool_name in pool_name[server]:
                    # 仅当命中时才更新卡池, 如果网站删除一个卡池, 更新后不会影响本地卡池
                    local_pool[server] = online_pool[online_pool_name]
                    # 检查UP角色是重复在star3中出现
                    if local_pool[server]["up"]:
                        up_chara_id = local_pool[server]["up"][0]
                        if up_chara_id in local_pool[server]["star3"]:
                            local_pool[server]["star3"].remove(up_chara_id)
                    # 角色名转id
                    for star in ids_list:
                        local_pool[server][star] = self.ids2names(
                            local_pool[server][star]
                        )
                        if not local_pool[server][star]:
                            # MIX池会出现无UP角色的空列表, 然后偷偷换成我老婆
                            local_pool[server][star] = ["镜华(万圣节)"]
                            logger.info(
                                f"{server}卡池{star}列表为空, 已替换为镜华(万圣节)"
                            )

        # 将新卡池写入文件
        PCRDataService._local_pool = local_pool
        self._save_local_pool()
        logger.success("PCR_LOCAL_POOL 更新完成")

    async def update_local_pool_ver(self) -> None:
        """
        修改本地版本号
        """
        # 获取线上版本号
        online_pool_ver = await self.get_online_pool_ver()
        PCRDataService._local_pool_ver = online_pool_ver
        self._save_local_pool_ver()
        logger.success("PCR_LOCAL_POOL_VER 更新完成")

    @classmethod
    def get_chara_name(cls) -> Dict:
        """
        拿到本地chara_name数据

        Returns:
            Dict: _description_
        """
        try:
            with open(pcr_data_path / "chara_name.json", "r", encoding="utf-8") as file:
                cls._chara_name = json.load(file)
        except Exception:
            cls._chara_name = {}
        return cls._chara_name.copy()

    @classmethod
    def get_chara_name_id(cls) -> Dict:
        cls._chara_name_id.clear()
        for idx, names in cls._chara_name.items():
            for n in names:
                n = normalize_str(n)
                if n not in cls._chara_name_id:
                    cls._chara_name_id[n] = idx
                else:
                    logger.warning(
                        f"priconne.chara.Roster: 出现重名{n}于id{idx}与id{cls._chara_name_id[n]}"
                    )
        # 保存新数据
        return cls._chara_name_id.copy()

    @classmethod
    def get_chara_profile(cls) -> Dict:
        """
        拿到本地chara_profile数据

        Returns:
            Dict: _description_
        """
        try:
            with open(
                pcr_data_path / "chara_profile.json", "r", encoding="utf-8"
            ) as file:
                cls._chara_profile = json.load(file)
        except Exception:
            cls._chara_profile = {}
        return cls._chara_profile.copy()

    @classmethod
    def get_local_pool_ver(cls) -> Dict:
        try:
            with open(
                pcr_data_path / "local_pool_ver.json", "r", encoding="utf-8"
            ) as file:
                cls._local_pool_ver = json.load(file)
        except Exception:
            cls._local_pool_ver = {}
        return cls._local_pool_ver.copy()

    @classmethod
    def get_local_pool(cls):
        try:
            with open(pcr_data_path / "local_pool.json", "r", encoding="utf-8") as file:
                cls._local_pool = json.load(file)
        except Exception:
            cls._local_pool = {}
        return cls._local_pool.copy()

    @classmethod
    def _save_chara_name(cls) -> None:
        with open(pcr_data_path / "chara_name.json", "w", encoding="utf-8") as file:
            json.dump(cls._chara_name, file, indent=4, ensure_ascii=False)
        logger.success("PCR_CHARA_NAME 成功保存至本地")

    @classmethod
    def _save_chara_profile(cls) -> None:
        with open(pcr_data_path / "chara_profile.json", "w", encoding="utf-8") as file:
            json.dump(cls._chara_profile, file, indent=4, ensure_ascii=False)
        logger.success("PCR_CHARA_PROFILE 成功保存至本地")

    @classmethod
    def _save_local_pool(cls) -> None:
        with open(pcr_data_path / "local_pool.json", "w", encoding="utf-8") as file:
            json.dump(cls._local_pool, file, indent=4, ensure_ascii=False)
        logger.success("PCR_LOCAL_POOL 成功保存至本地")

    @classmethod
    def _save_local_pool_backup(cls) -> None:
        with open(
            pcr_data_path / "local_pool_backup.json", "w", encoding="utf-8"
        ) as file:
            json.dump(cls._local_pool_backup, file, indent=4, ensure_ascii=False)
        logger.success("PCR_LOCAL_POOL_BACKUP 成功保存至本地")

    @classmethod
    def _save_local_pool_ver(cls) -> None:
        with open(pcr_data_path / "local_pool_ver.json", "w", encoding="utf-8") as file:
            json.dump(cls._local_pool_ver, file, indent=4, ensure_ascii=False)
        logger.success("PCR_LOCAL_POOL_VER 成功保存至本地")

    @classmethod
    async def get_online_chara_name(
        cls, url: str = online_pcr_data_url2
    ) -> Dict[str, list[str]]:
        """
        获取在线的角色数据信息, 并处理为json格式
        """
        logger.info(f"开始获取在线角色数据from:{url}")
        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(url=url, follow_redirects=True, timeout=30)
                # 检查响应是否成功
                if response.status_code == 200:
                    # 将响应内容写入文件
                    response_text = response.text
                    # 定义一个列表，包含想要的字典的名称
                    content_names = "CHARA_NAME"
                    # 将文件内容转换为AST对象
                    tree = ast.parse(response_text)
                    # 定义一个空字典，用于存储三个数据
                    data = {}
                    # 遍历抽象语法树中的所有节点，找到类型为ast.Assign的节点
                    for node in ast.walk(tree):
                        # 如果节点是一个赋值语句
                        if isinstance(node, ast.Assign):
                            # 获取赋值语句的左边的变量名
                            name = node.targets[0].id  # type: ignore
                            # 如果变量名是您想要的数据之一
                            if name is content_names:
                                # 将赋值语句的右边的值转换为Python对象，并存储到字典中
                                data = ast.literal_eval(node.value)
                                return {str(k): v for k, v in data.items()}
                            else:
                                data = {}
                    return data
                else:
                    logger.error(f"获取在线角色数据时发生错误{response.status_code}")
                    return {}
        except Exception as e:
            logger.error(f"获取在线角色数据时发生错误 请求错误：{type(e)}")
            return {}

    @classmethod
    async def get_online_chara_profile(
        cls, url: str = online_pcr_data_url2
    ) -> Dict[str, Dict[str, str]]:
        """
        获取在线的角色档案信息, 并处理为json格式
        """
        logger.info("开始获取在线角色档案")
        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(url=url, follow_redirects=True, timeout=30)
                # 检查响应是否成功
                if response.status_code == 200:
                    # 将响应内容写入文件
                    response_text = response.text
                    # 定义一个列表，包含想要的字典的名称
                    content_names = "CHARA_PROFILE"
                    # 将文件内容转换为AST对象
                    tree = ast.parse(response_text)
                    # 定义一个空字典，用于存储三个数据
                    data = {}
                    # 遍历抽象语法树中的所有节点，找到类型为ast.Assign的节点
                    for node in ast.walk(tree):
                        # 如果节点是一个赋值语句
                        if isinstance(node, ast.Assign):
                            # 获取赋值语句的左边的变量名
                            name = node.targets[0].id  # type: ignore
                            # 如果变量名是您想要的数据之一
                            if name is content_names:
                                # 将赋值语句的右边的值转换为Python对象，并存储到字典中
                                data = ast.literal_eval(node.value)
                                return {str(k): v for k, v in data.items()}
                            else:
                                data = {}
                    return data
                else:
                    logger.error(f"获取在线角色档案时发生错误{response.status_code}")
                    return {}
        except Exception as e:
            logger.error(f"获取在线角色档案时发生错误 请求错误：{type(e)}")
            return {}

    @classmethod
    async def get_online_pool_ver(cls, url: str = online_pool_ver_url) -> Dict:
        """
        获取在线版本号
        """
        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(url=url, follow_redirects=True, timeout=30)
                if response.status_code == 200:
                    online_pool_ver_json = response.json()
                    online_pool_ver = online_pool_ver_json
                    logger.info(f"检查卡池更新, 在线卡池版本{online_pool_ver}")
                    return online_pool_ver
                else:
                    logger.error(f"获取在线卡池版本时发生错误{response.status_code}")
                    return {}
        except Exception as e:
            logger.error(f"获取在线卡池版本时发生错误 {type(e)}")
            return {}

    @classmethod
    async def get_online_pool(cls, url: str = online_pool_url) -> Dict:
        """
        获取在线卡池, 返回json格式
        """
        logger.info("开始获取在线卡池")
        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(url=url, follow_redirects=True, timeout=30)
                if response.status_code == 200:
                    online_pool = response.json()
                    return online_pool
                else:
                    logger.error(f"获取在线卡池时发生错误{response.status_code}")
                    return {}
        except Exception as e:
            logger.error(f"获取在线卡池时发生错误 {type(e)}")
            return {}

    def ids2names(self, ids: List[str]) -> list:
        """
        根据ID转换为官方译名,为了与现行卡池兼容
        """
        # print(ids)
        res = [
            self.chara_name[str(id)][0]
            if str(id) in self.chara_name
            else logger.warning(f"缺少角色{id}的信息, 请注意更新静态资源   ")
            for id in ids
        ]
        return res

    @staticmethod
    def merge_dicts(
        dict1: Dict[str, list[str]],
        dict2: Dict[str, list[str]],
        is_info: bool = False,
    ) -> Dict[str, list[str]]:
        # 创建一个新的字典来存储结果
        result = {}
        # 遍历第一个字典，将其内容添加到结果字典中
        for key, value in dict1.items():
            if key not in result:
                result[key] = value
            else:
                result[key] += value
        # 遍历第二个字典，将其内容添加到结果字典中
        for key, value in dict2.items():
            if key not in result:
                result[key] = value
            else:
                result[key] += value
        for key in result:
            # 由于返回数据可能出现全半角重复, 做一定程度的兼容性处理, 会将所有全角替换为半角, 并移除重别称
            for i, name in enumerate(result[key]):
                name_format = name.replace("（", "(")
                name_format = name_format.replace("）", ")")
                name_format = normalize_str(name_format)
                result[key][i] = name_format
            n = result[key][0]
            group = {f"{n}"}
            # 转集合再转列表, 移除重复元素, 按原名日文优先顺序排列
            m = list(set(result[key]))
            sort_priority(m, group)
            result[key] = m
            if is_info:
                if key not in dict2 or len(result[key]) != len(dict2[key]):
                    logger.info(f"已开始更新角色{key}的数据和图标")
        return result


pcr_date = PCRDataService()


class CharaDataService:
    UNKNOWN = "1000"
    UnavailableChara = {
        "1067",  # 穗希
        "1069",  # 霸瞳
        "1072",  # 可萝爹
        "1073",  # 拉基拉基
        "1102",  # 泳装大眼
        "1183",  # 星弓星
        "1184",  # 星弓栞
        "1204",
        "1205",
        "1206",  # (小小甜心)
        "1164",
        "1194",
        "1195",
        "1196",
        "1197",
        "1200",
        "1201",
        "1202",
        "1203",  # (未实装)
    }

    def match(self, query, choices):
        """
        匹配队列里最相似的元素

        Args:
            query (_type_): 匹配队列
            choices (_type_): 匹配对象

        Returns:
            _type_: _description_
        """
        query = normalize_str(query)
        a = difflib.get_close_matches(query, choices, 1, cutoff=0.6)
        if a:
            a = a[0]
        else:
            a = choices[0]
        b = fuzz.ratio(query, a)
        logger.info(f"匹配结果 {a} 相似度{b}")
        return a, b

    def get_id(self, name) -> str:
        name = normalize_str(name)
        return (
            pcr_date.chara_name_id[name]
            if name in pcr_date.chara_name_id
            else self.UNKNOWN
        )

    def get_name(self, name) -> str:
        """
        根据给定的名称获取对应的ID。

        参数:
            name (str): 要转换为ID的名称。

        返回:
            int: 对应于给定名称的ID。
        """
        name = normalize_str(name)
        return (
            pcr_date.chara_name_id[name]
            if name in pcr_date.chara_name_id
            else self.UNKNOWN
        )

    def name2id(self, name):
        return self.get_id(name)

    def from_id(self, id_, star=0, equip=0):
        """
        _summary_

        Args:
            id_ (_type_): _description_
            star (int, optional): _description_. Defaults to 0.
            equip (int, optional): _description_. Defaults to 0.

        Returns:
            _type_: _description_
        """
        return Chara(id_, star, equip)

    def from_name(self, name, star=0, equip=0):
        """
        根据给定的名称生成一个角色对象。

        参数:
            name (str): 角色的名称。
            star (int): 角色的星级评分。默认为 0。
            equip (int): 角色的装备值。默认为 0。

        返回:
            Chara: 根据给定的名称、星级评分和装备值生成的角色对象。
        """
        id_ = self.name2id(name)
        return Chara(id_, star, equip)

    def guess_id(self, name):
        """@return: id, name, score"""
        name = normalize_str(name)
        if name in pcr_date.chara_name_id:
            return pcr_date.chara_name_id[name]

        return roster.guess_id(name)

    def is_npc(self, id_: str) -> bool:
        if id_ in self.UnavailableChara:
            return True
        else:
            return not ((1000 < int(id_) < 1214) or (1700 < int(id_) < 1900))


chara_data = CharaDataService()
