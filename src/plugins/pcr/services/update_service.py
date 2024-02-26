# -*- coding: utf-8 -*-
from ..logger import PCRLogger as Logger
from .data_service import pcr_data

logger = Logger("PCR_UPDATE")


class UpdateService:
    """PCR数据更新服务"""

    def __init__(self) -> None:
        pass

    async def check_pcr_data(self) -> str:
        """
        此函数返回当前 PCR 数据作为字符串。

        返回:
            str: 当前 PCR 数据作为字符串。
        """
        return str(pcr_data)

    async def update_pool(self, force=False) -> str:
        """
        更新local_pool数据。

        Args:
            force (bool, optional): 是否强制更新，即使版本号相同。默认为 False。

        Returns:
            str: 更新结果的消息。
        """
        # 获取本地版本号
        local_pool_ver = {"ver": "0"} if force else pcr_data.LOCAL_POOL_VER.copy()
        # 获取远程版本号
        online_pool_ver = await pcr_data.get_online_pcr_data("local_pool_ver")
        if not online_pool_ver:
            logger.error("获取在线卡池版本时发生错误")
            return "获取在线卡池版本时发生错误"
        # 比较版本号
        if int(online_pool_ver.get("ver", "0")) <= int(local_pool_ver.get("ver", "0")):
            return "卡池已是最新版本,当前版本为" + str(online_pool_ver.get("ver"))
        try:
            # 修改本地卡池
            await pcr_data.update_pcr_data("local_pool")
            # 覆盖本地版本号
            await pcr_data.update_pcr_data("local_pool_ver")
            # 重新加载数据
            await pcr_data.load_pcr_data()
        except Exception:
            return "更新卡池时发生错误"
        return "卡池已更新到最新版本,当前版本为" + str(online_pool_ver.get("ver"))

    async def update_pcr_data(self) -> str:
        """
        更新 PCR 数据。

        返回:
            str: 表示更新结果的消息。
        """
        a = len(pcr_data.CHARA_NAME)
        b = len(pcr_data.CHARA_PROFILE)
        try:
            # 更新数据
            await pcr_data.update_pcr_data("chara_name")
            await pcr_data.update_pcr_data("chara_profile")
            # 重新加载数据
            await pcr_data.load_pcr_data()
            c = len(pcr_data.CHARA_NAME)
            d = len(pcr_data.CHARA_PROFILE)
            message = "更新角色数据成功\n更新前:\nCHARA_NAME: {}\nCHARA_PROFILE: {}\n更新后:\nCHARA_NAME: {}\nCHARA_PROFILE: {}\n".format(
                a, b, c, d
            )
        except Exception:
            message = "更新数据时发生错误"
        return message
