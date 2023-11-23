from arclet.alconna import (
    Alconna,
    Arparma,
    Args,
    Option,
    CommandMeta,
    store_true,
)


from nonebot.plugin import PluginMetadata
from nonebot import logger
from nonebot.adapters.qq.event import GuildMessageEvent


from nonebot_plugin_alconna import AlconnaMatches, on_alconna
from nonebot_plugin_apscheduler import scheduler

from .config import Config, plugin_config
from ...services import UpdateService
from ...models import UpdateResult

__plugin_meta__ = PluginMetadata(
    name="pcr_update",
    description="""
    - [重载花名册] 用于更新人物
    - [更新卡池] 用于更新卡池
    - [查看PCR数据] 用于查看本地数据
    """,
    usage="[重载花名册|更新卡池|查看PCR数据]",
    config=Config,
)

update_service = UpdateService()


strategy = ["strategy", "策略", "攻略"]
pool = ["pool", "卡池", "pcr卡池", "PCR卡池"]
chara = ["chara", "角色数据", "人物数据", "花名册"]

alc = Alconna(
    "更新",
    Args["data", strategy + pool + chara],
    Option("-F|-f|--force", action=store_true),
    meta=CommandMeta(compact=True),
)
pcr_update = on_alconna(
    alc,
    auto_send_output=True,
    aliases={"update", "重载"},
    priority=5,
)


@pcr_update.handle()
async def _(event: GuildMessageEvent, result: Arparma = AlconnaMatches()):
    """
    处理PCR更新事件。
    """
    # print(result.find("force"))
    if result.main_args["data"] in strategy:
        pass
    if result.main_args["data"] in pool:
        res: UpdateResult = await update_service.update_pool(force=result.find("force"))
        await pcr_update.finish(res.message)
    if result.main_args["data"] in chara:
        res: UpdateResult = await update_service.update_pcr_data()
        await pcr_update.finish(res.message)
    await pcr_update.finish("ok")


if plugin_config.plugin_is_auto:
    logger.info("定时更新PCR数据")

    @scheduler.scheduled_job("cron", hour="17", minute="05")
    async def update_data_sdj():
        """
        定时更新PCR数据
        """
        if plugin_config.plugin_is_notice:
            pass
        await update_service.update_pool()
        await update_service.update_pcr_data()


pcr_check_data = on_alconna(
    "查看PCR数据",
    aliases={"查看数据"},
    priority=5,
)


@pcr_check_data.handle()
async def get_pcr_data(event: GuildMessageEvent):
    """
    查看本地数据
    """
    a, b = await update_service.check_pcr_data()
    await pcr_check_data.finish(f"CHARA_NAME:{a}\nCHARA_PROFILE:{b}")
