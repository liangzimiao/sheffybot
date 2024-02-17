from nonebot.adapters import Bot, Event
from nonebot.plugin import PluginMetadata
from nonebot_plugin_alconna import on_alconna
from nonebot_plugin_apscheduler import scheduler

from ..config import pcr_config
from ..services.update_service import UpdateService, logger

__plugin_meta__ = PluginMetadata(
    name="pcr_update",
    description="""
    用于查看本地数据,用于更新本地数据
    """,
    usage="[重载花名册|更新卡池|查看PCR数据]",
    config=None,
)

update_service = UpdateService()


strategy = ["strategy", "策略", "攻略"]
pool = ["pool", "卡池", "pcr卡池", "PCR卡池"]
chara = ["chara", "角色数据", "人物数据", "花名册"]


matcher = on_alconna(
    "查看PCR数据",
    aliases={"查看数据"},
    priority=5,
)


@matcher.handle()
async def _():
    """
    查看本地数据
    """
    result = await update_service.check_pcr_data()
    await matcher.finish(result)


pcr_update = on_alconna(
    "更新PCR数据",
    aliases={"查看人物数据", "更新人物数据", "更新人物"},
    priority=5,
)


@pcr_update.handle()
async def _(bot: Bot, event: Event):
    """
    处理PCR更新事件。
    """
    result = await update_service.update_pcr_data()
    await pcr_update.finish(result)


if pcr_config.pcr_update_is_auto:
    logger.info("定时更新PCR数据")

    @scheduler.scheduled_job("cron", hour="17", minute="05")
    async def update_data_sdj():
        """
        定时更新PCR数据
        """
        if pcr_config.pcr_update_is_notice:
            pass
        await update_service.update_pool()
        await update_service.update_pcr_data()
