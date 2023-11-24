# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Tuple

from loguru import logger

from ..config import pcr_config
from ..models import UpdateResult
from .internal.data_service import pcr_data

pcr_res_path: Path = pcr_config.pcr_resources_path
pcr_data_path: Path = pcr_config.pcr_data_path


class UpdateService:
    """PCR数据更新服务"""

    def __init__(self) -> None:
        pass

    async def update_pool(self, force=False) -> UpdateResult:
        """
        从远程拉取卡池覆盖本地的卡池
        指定force为true, 则不会比较本地版本号是否最新
        """
        # 获取本地版本号
        local_pool_ver = {"ver": "0"} if force else pcr_data.LOCAL_POOL_VER.copy()
        # 获取远程版本号
        online_pool_ver = await pcr_data.get_online_pool_ver()
        if not online_pool_ver:
            logger.error("获取在线卡池版本时发生错误")
            return UpdateResult(
                is_success=False, type_name="pool", message="获取在线卡池版本时发生错误"
            )
        # 比较版本号
        if int(online_pool_ver["ver"]) <= int(local_pool_ver["ver"]):
            return UpdateResult(
                is_success=True,
                type_name="pool",
                message="卡池已是最新版本,当前版本为" + local_pool_ver["ver"],
            )
        try:
            # 修改本地卡池
            await pcr_data.update_local_pool()
            # 覆盖本地版本号
            await pcr_data.update_local_pool_ver()
            # 重新加载数据
            await pcr_data.load_data()
        except Exception:
            return UpdateResult(
                is_success=False, type_name="pool", message="更新卡池时发生错误"
            )
        return UpdateResult(
            is_success=True,
            type_name="pool",
            message="卡池已更新到最新版本,当前版本为" + online_pool_ver["ver"],
        )

    async def update_pcr_data(self) -> UpdateResult:
        """
        更新并重新加载PCR数据。

        该函数通过调用相应的更新函数`pcr_data.update_chara_name()`和`pcr_data.update_chara_profile()`来更新PCR数据中的角色名称和角色档案。更新数据后，通过调用`pcr_data.load_data()`重新加载数据。然后计算更新前后角色名称和角色档案的长度。

        返回：
            Tuple[int, int, int, int]：包含更新前角色名称和角色档案的长度（a和b），以及更新后角色名称和角色档案的长度（c和d）的元组。
        """
        a = len(pcr_data.CHARA_NAME)
        b = len(pcr_data.CHARA_PROFILE)
        # 更新数据
        try:
            # 更新数据
            await pcr_data.update_chara_name()
            await pcr_data.update_chara_profile()
            # 重新加载数据
            await pcr_data.load_data()
        except Exception:
            return UpdateResult(
                is_success=False, type_name="chara", message="更新数据时发生错误"
            )
        c = len(pcr_data.CHARA_NAME)
        d = len(pcr_data.CHARA_PROFILE)
        return UpdateResult(
            is_success=True,
            type_name="chara",
            message="更新角色数据成功\n更新前:\nCHARA_NAME:"
            + str(a)
            + "\nCHARA_PROFILE:"
            + str(b)
            + "\n更新后:\nCHARA_NAME:"
            + str(c)
            + "\nCHARA_PROFILE:"
            + str(d),
        )

    async def check_pcr_data(self) -> Tuple[int, int]:
        """
        检查PCR数据中角色名称和角色档案列表的长度。

        返回:
            Tuple[int, int]：一个元组，包含角色名称列表和角色档案列表的长度。
        """
        a = len(pcr_data.CHARA_NAME)
        b = len(pcr_data.CHARA_PROFILE)
        return a, b
