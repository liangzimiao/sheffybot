# -*- coding: utf-8 -*-
import ast
import json
from pathlib import Path
from typing import Any, Dict, List

import httpx
from loguru import logger

from ...config import pcr_config
from .util import normalize_str, sort_priority

pcr_data_path: Path = pcr_config.pcr_data_path
"""PCR数据存放路径"""
pcr_res_path: Path = pcr_config.pcr_resources_path
"""PCR资源存放路径"""


online_pool_url = "https://api.redive.lolikon.icu/gacha/default_gacha.json"
online_pool_ver_url = "https://api.redive.lolikon.icu/gacha/gacha_ver.json"
online_pcr_data_url = "https://api.redive.lolikon.icu/gacha/unitdata.py"
online_pcr_data_url2 = "https://ghproxy.com/https://github.com/Ice9Coffee/LandosolRoster/blob/master/_pcr_data.py"




class PCRDataService:
    """PCR数据服务"""

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
        if not self.CHARA_NAME:
            logger.opt(colors=True).info(
                "未检测到<y><b>PCR_CHARA_NAME</b></y>数据 将重新生成"
            )
            await self.update_chara_name()
            PCRDataService.CHARA_NAME = self.get_chara_name()
        if not self.CHARA_NAME_ID:
            logger.opt(colors=True).info(
                "未检测到<y><b>PCR_CHARA_NAME_ID</b></y>数据 将重新生成"
            )
            PCRDataService.CHARA_NAME_ID = self.get_chara_name_id()
        if not self.CHARA_PROFILE:
            logger.opt(colors=True).info(
                "未检测到<y><b>PCR_CHARA_PROFILE</b></y>数据 将重新生成"
            )
            await self.update_chara_profile()
            PCRDataService.CHARA_PROFILE = self.get_chara_profile()
        if not self.LOCAL_POOL:
            logger.opt(colors=True).info(
                "未检测到<y><b>PCR_LOCAL_POOL</b></y>数据 将重新生成"
            )
            await self.update_local_pool()
            PCRDataService.LOCAL_POOL = self.get_local_pool()
        if not self.LOCAL_POOL_VER:
            logger.opt(colors=True).info(
                "未检测到<y><b>PCR_LOCAL_POOL_VER</b></y>数据 将重新生成"
            )
            await self.update_local_pool_ver()
            PCRDataService.LOCAL_POOL_VER = self.get_local_pool_ver()

        ver = self.LOCAL_POOL_VER["ver"]
        logger.opt(colors=True).success("Succeeded to load <y><b>PCR_DATA</b></y>")
        logger.info(f"PCR_CHARA_NAME:{len(self.CHARA_NAME)}")
        logger.info(f"PCR_CHARA_PROFILE:{len(self.CHARA_PROFILE)}")
        logger.info(f"PCR_POOL_VER:{ver}")

    async def update_chara_name(self) -> None:
        """
        对比本地和远程的_pcr_data.py, 自动补充本地没有的角色信息, 已有角色信息进行补全
        """
        # 获取线上角色信息
        # online1 = await self.get_online_chara_name(url=online_pcr_data_url)
        online1 = {}
        online2 = await self.get_online_chara_name(url=online_pcr_data_url2)
        online_chara_name = self.merge_dicts(online2, online1)
        if not online_chara_name:
            logger.warning("online_chara_name is None")
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
        result = {"success": 0, "duplicate": 0}
        for idx, names in cls.CHARA_NAME.items():
            for n in names:
                n = normalize_str(n)
                if n not in data:
                    data[n] = idx
                    result["success"] += 1
                else:
                    result["duplicate"] += 1
                    logger.opt(colors=True).warning(
                        f"<y><b>PCR_DATA</b></y>: 出现重名{n}于id{idx}与id{data[n]}相同"
                    )
        logger.opt(colors=True).info(f"<y><b>PCR_DATA</b></y>: {result}")
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
                # name_format = normalize_str(name_format)
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
