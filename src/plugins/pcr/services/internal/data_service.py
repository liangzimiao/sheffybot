# -*- coding: utf-8 -*-
import ast
import difflib
import json
import httpx
import unicodedata
import zhconv

from loguru import logger
from fuzzywuzzy import fuzz
from pathlib import Path
from typing import Any, Dict, List, Literal


from ...models import Chara
from ...config import pcr_config

pcr_data_path: Path = pcr_config.pcr_data_path
"""PCR数据存放路径"""
pcr_res_path: Path = pcr_config.pcr_resources_path
"""PCR资源存放路径"""


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

    CHARA_NAME: Dict[str, List[str]] = {}
    CHARA_NAME_ID: Dict[str, str] = {}
    CHARA_PROFILE: Dict[str, Dict[str, str]] = {}
    LOCAL_POOL: Dict[str, Dict[str, Any]] = {}
    LOCAL_POOL_VER: Dict[str, str] = {}

    def __init__(self) -> None:
        pcr_res_path.mkdir(parents=True, exist_ok=True)
        pcr_data_path.mkdir(parents=True, exist_ok=True)

    async def load_data(self) -> None:
        """
        加载数据
        检查文件是否存在以及能否正确读取
        读取为空则启动对应的更新方法重新生成
        """
        PCRDataService.CHARA_NAME = self.get_chara_name()
        PCRDataService.CHARA_NAME_ID = self.get_chara_name_id()
        PCRDataService.CHARA_PROFILE = self.get_chara_profile()
        PCRDataService.LOCAL_POOL = self.get_local_pool()
        PCRDataService.LOCAL_POOL_VER = self.get_local_pool_ver()
        if not PCRDataService.CHARA_NAME:
            logger.info("未检测到PCR_CHARA_NAME数据 将重新生成")
            await self.update_chara_name()
            PCRDataService.CHARA_NAME = self.get_chara_name()
        if not self.CHARA_NAME_ID:
            logger.info("未检测到PCR_CHARA_NAME_ID数据 将重新生成")
            PCRDataService.CHARA_NAME_ID = self.get_chara_name_id()
        if not self.CHARA_PROFILE:
            logger.info("未检测到PCR_CHARA_PROFILE数据 将重新生成")
            await self.update_chara_profile()
            PCRDataService.CHARA_PROFILE = self.get_chara_profile()
        if not self.LOCAL_POOL:
            logger.info("未检测到PCR_LOCAL_POOL数据 将重新生成")
            await self.update_local_pool()
            PCRDataService.LOCAL_POOL = self.get_local_pool()
        if not self.LOCAL_POOL_VER:
            logger.info("未检测到PCR_LOCAL_POOL_VER数据 将重新生成")
            await self.update_local_pool_ver()
            PCRDataService.LOCAL_POOL_VER = self.get_local_pool_ver()

        Chara.CHARA_NAME = self.CHARA_NAME
        ver = self.LOCAL_POOL_VER["ver"]
        logger.success("成功加载PCR_DATA全部数据")
        logger.success(f"PCR_CHARA_NAME:{len(self.CHARA_NAME)}")
        logger.success(f"PCR_CHARA_PROFILE:{len(self.CHARA_PROFILE)}")
        logger.success(f"LOCAL_PCR_POOL_VER:{ver}")

    async def update_chara_name(self) -> None:
        """
        对比本地和远程的_pcr_data.py, 自动补充本地没有的角色信息, 已有角色信息进行补全
        """
        # 获取线上角色信息
        online1 = await self.get_online_chara_name(url=online_pcr_data_url)
        online2 = await self.get_online_chara_name(url=online_pcr_data_url2)
        online_chara_name = self.merge_dicts(online2, online1)
        if (not online2) or (not online1):
            logger.warning("Online_chara_name is None")
            return
        # 获取本地角色信息
        local_chara_name = self.CHARA_NAME.copy()
        logger.info("开始对比角色数据")
        chara_name = self.merge_dicts(online_chara_name, local_chara_name, is_info=True)
        # 保存新数据
        with open(pcr_data_path / "chara_name.json", "w", encoding="utf-8") as file:
            json.dump(chara_name, file, indent=4, ensure_ascii=False)
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
        local_chara_profile = self.CHARA_PROFILE.copy()
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
        with open(pcr_data_path / "chara_profile.json", "w", encoding="utf-8") as file:
            json.dump(local_chara_profile, file, indent=4, ensure_ascii=False)
        logger.success("PCR_CHARA_PROFILE 更新完成")

    async def update_local_pool(self) -> None:
        """
        更新本地卡池文件, 并备份原卡池
        """
        # 获取线上卡池
        online_pool = await self.get_online_pool(url=online_pool_url)
        # 获取本地卡池
        local_pool = self.LOCAL_POOL.copy()
        # 备份本地卡池
        logger.info("开始备份本地卡池")
        local_pool_backup = local_pool
        with open(
            pcr_data_path / "local_pool_backup.json", "w", encoding="utf-8"
        ) as file:
            json.dump(local_pool_backup, file, indent=4, ensure_ascii=False)
        logger.success("PCR_LOCAL_POOL_BACKUP 成功备份至本地")

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
        with open(pcr_data_path / "local_pool.json", "w", encoding="utf-8") as file:
            json.dump(local_pool, file, indent=4, ensure_ascii=False)
        logger.success("PCR_LOCAL_POOL 更新完成")

    async def update_local_pool_ver(self) -> None:
        """
        修改本地版本号
        """
        # 获取线上版本号
        online_pool_ver = await self.get_online_pool_ver()
        local_pool_ver = online_pool_ver
        with open(pcr_data_path / "local_pool_ver.json", "w", encoding="utf-8") as file:
            json.dump(local_pool_ver, file, indent=4, ensure_ascii=False)
        logger.success("PCR_LOCAL_POOL_VER 更新完成")

    @classmethod
    def get_chara_name(cls) -> Dict:
        """
        拿到本地chara_name数据
        """
        try:
            with open(pcr_data_path / "chara_name.json", "r", encoding="utf-8") as file:
                data = json.load(file)
        except Exception:
            data = {}
        return data

    @classmethod
    def get_chara_profile(cls) -> Dict:
        """
        拿到本地chara_profile数据
        """
        try:
            with open(
                pcr_data_path / "chara_profile.json", "r", encoding="utf-8"
            ) as file:
                data = json.load(file)
        except Exception:
            data = {}
        return data

    @classmethod
    def get_local_pool(cls) -> Dict:
        """
        拿到本地local_pool数据
        """
        try:
            with open(pcr_data_path / "local_pool.json", "r", encoding="utf-8") as file:
                data = json.load(file)
        except Exception:
            data = {}
        return data

    @classmethod
    def get_local_pool_ver(cls) -> Dict:
        """
        拿到本地local_pool_ver数据
        """
        try:
            with open(
                pcr_data_path / "local_pool_ver.json", "r", encoding="utf-8"
            ) as file:
                data = json.load(file)
        except Exception:
            data = {}
        return data

    @classmethod
    def get_chara_name_id(cls) -> Dict:
        """
        拿到本地chara_name_id数据
        """
        data = {}
        for idx, names in cls.CHARA_NAME.items():
            for n in names:
                n = normalize_str(n)
                if n not in data:
                    data[n] = idx
                else:
                    logger.warning(
                        f"Priconne.Chara: 出现重名{n}于id{idx}与id{data[n]}相同"
                    )
        return data

    @classmethod
    def ids2names(cls, ids: List[str]) -> list:
        """
        根据ID转换为官方译名,为了与现行卡池兼容
        """
        # print(ids)
        res = [
            cls.CHARA_NAME[str(id)][0]
            if str(id) in cls.CHARA_NAME
            else logger.warning(f"缺少角色{id}的信息, 请注意更新静态资源   ")
            for id in ids
        ]
        return res

    @staticmethod
    async def get_online_chara_name(
        url: str = online_pcr_data_url2
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

    @staticmethod
    async def get_online_chara_profile(
        url: str = online_pcr_data_url2
    ) -> Dict[str, Dict[str, str]]:
        """
        获取在线的角色档案信息, 并处理为json格式
        """
        logger.info(f"开始获取在线角色档案from:{url}")
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

    @staticmethod
    async def get_online_pool_ver(url: str = online_pool_ver_url) -> Dict:
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

    @staticmethod
    async def get_online_pool(url: str = online_pool_url) -> Dict:
        """
        获取在线卡池, 返回json格式
        """
        logger.info("开始获取在线卡池from:" + url)
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

    @staticmethod
    def merge_dicts(
        dict1: Dict[str, list[str]],
        dict2: Dict[str, list[str]],
        is_info: bool = False,
    ) -> Dict[str, list[str]]:
        """
        合并两个字典并返回结果。

        参数:
            dict1 (Dict[str, list[str]]): 第一个要合并的字典。
            dict2 (Dict[str, list[str]]): 第二个要合并的字典。
            is_info (bool, optional): 是否记录额外信息的标志。默认为 False。

        返回:
            Dict[str, list[str]]: 合并后的字典。

        注意:
            - 函数根据键合并两个字典的值。
            - 如果一个键在两个字典中都存在，则将值连接起来。
            - 函数对值进行一些兼容性处理。
            - 如果 `is_info` 为 True，则会记录某些情况下的额外信息。

        """
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


pcr_data = PCRDataService()


class CharaDataService:
    UNKNOWN = "1000"

    def match(self, query, choices):
        """
        匹配给定的查询字符串和选项列表，并返回最佳匹配项及其相似度评分。

        参数：
            query (str)：要匹配的查询字符串。
            choices (list)：要与之匹配的选项列表。

        返回：
            tuple：包含最佳匹配项（str）和相似度评分（int）的元组。
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

    def name2id(self, name) -> str:
        """
        根据给定的名称转换成对应的ID。
        """
        name = normalize_str(name)
        return (
            pcr_data.CHARA_NAME_ID[name]
            if name in pcr_data.CHARA_NAME_ID
            else self.UNKNOWN
        )

    def from_id(
        self,
        id_: int | str,
        star: Literal[1, 3, 6, "1", "3", "6"] = 3,
        equip: int = 0,
    ):
        """
        根据提供的ID、星级和装备等级创建一个新的Chara实例。

        参数:
            id_ (int): 角色的ID。
            star (int, 可选): 角色的星级。默认为3。
            equip (int, 可选): 角色的装备等级。默认为0。
        返回值:
            Chara: 具有指定ID、星级和装备等级的Chara类的新实例。
        """
        return Chara(id_, star, equip)

    def from_name(
        self,
        name,
        star: Literal[1, 3, 6, "1", "3", "6"] = 3,
        equip: int = 0,
    ):
        """
        根据角色名称、星级和装备等级创建一个新的角色实例。

        参数:
            name (str): 角色的名称。
            star (int或str): 角色的星级。默认为3。
            equip (int): 角色的装备等级。默认为0。

        返回值:
            Chara: 具有指定名称、星级和装备等级的角色实例。
        """
        id_ = self.name2id(name)
        return Chara(id_, star, equip)

    def guess_id_name_score(self, name):
        """
        猜测给定名称的角色的ID、名称和得分。

        参数：
            name (str)：要猜测ID、名称和得分的角色的名称。

        返回：
            tuple：包含猜测的ID、名称和得分的元组。
        """
        name, score = self.match(name, pcr_data.CHARA_NAME_ID.keys())
        return pcr_data.CHARA_NAME_ID[name], name, score


chara_data = CharaDataService()
