# -*- coding: utf-8 -*-
from loguru import logger
from pathlib import Path
from typing import Any

from ..config import pcr_config
from .internal.pcr_data_service import PCRDataService


pcr_res_path: Path = pcr_config.pcr_resources_path
pcr_data_path: Path = pcr_config.pcr_data_path

pcr_data = PCRDataService()


class UpdateService:
    """PCR数据更新服务"""

    def __init__(self) -> None:
        pass

    async def update_pool(self, force=False) -> int:
        """
        从远程拉取卡池覆盖本地的卡池
        1, 备份原卡池到backup.json
        2, 从远程卡池获取数据, 修改本地卡池数据
        3, 从远程卡池获取版本号, 覆盖到本地
        指定force为true, 则不会比较本地版本号是否最新
        """
        # 更新数据
        # await self.update_pcr_data()

        # 获取远程卡池
        online_pool = await pcr_data.get_online_pool()
        if not online_pool:
            logger.error("获取在线卡池时发生错误")
            return 0

        # 获取远程版本号
        online_pool_ver = await pcr_data.get_online_pool_ver()
        if not online_pool_ver:
            logger.error("获取在线卡池版本时发生错误")
            return 0

        # 比较本地版本号
        local_pool_ver = pcr_data.local_pool_ver
        if force:
            # 指定强制更新
            local_pool_ver = {"ver": "0"}
        if int(online_pool_ver["ver"]) <= int(local_pool_ver["ver"]):
            return 0
        # 修改本地卡池
        await pcr_data.update_local_pool()
        # 覆盖本地版本号
        await pcr_data.update_local_pool_ver()

        return int(pcr_data.local_pool_ver["ver"]) if pcr_data.local_pool_ver else 0

    async def update_pcr_data(self) -> Any:
        a = len(pcr_data.chara_name)
        b = len(pcr_data.chara_profile)
        await pcr_data.update_chara_name()
        await pcr_data.update_chara_profile()
        c = len(pcr_data.chara_name)
        d = len(pcr_data.chara_profile)
        return a, b, c, d

    async def check_pcr_data(self) -> Any:
        a = len(pcr_data.get_chara_name())
        b = len(pcr_data.get_chara_profile())
        return a, b
