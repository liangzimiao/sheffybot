from arclet.alconna import Alconna

from nonebot.plugin import PluginMetadata

from nonebot.adapters.qq.event import GuildMessageEvent


from nonebot_plugin_alconna import on_alconna
from nonebot_plugin_apscheduler import scheduler

from .config import Config, plugin_config
from ...services.update_service import UpdateService


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


cmd = Alconna("更新卡池")
pcr_update_pool = on_alconna(
    cmd,
    aliases={"更新卡池"},
    priority=5,
    use_origin=False,  # 是否使用未经 to_me 等处理过的消息
    use_cmd_start=True,  # 是否使用 COMMAND_START 作为命令前缀
    use_cmd_sep=True,  # 是否使用 COMMAND_SEP 作为命令分隔符
)


@pcr_update_pool.handle()
async def update_pool(event: GuildMessageEvent):
    """
    手动更新卡池时试用此命令
    """
    ver = await update_service.update_pool()
    await pcr_update_chara.finish(f"更新完成，当前卡池版号{ver}")


cmd = Alconna("强制更新卡池")
pcr_force_update_pool = on_alconna(
    cmd,
    aliases={"强制更新卡池"},
    priority=5,
    use_origin=False,  # 是否使用未经 to_me 等处理过的消息
    use_cmd_start=True,  # 是否使用 COMMAND_START 作为命令前缀
    use_cmd_sep=True,  # 是否使用 COMMAND_SEP 作为命令分隔符
)


@pcr_force_update_pool.handle()
async def force_update_pool(event: GuildMessageEvent):
    """
    强制更新卡池
    """
    ver = await update_service.update_pool(force=True)
    await pcr_update_chara.finish(f"更新完成，当前卡池版号{ver}")


cmd = Alconna("更新角色数据")
pcr_update_chara = on_alconna(
    cmd,
    aliases={
        "重载花名册",
        "更新角色数据",
    },
    priority=5,
    use_origin=False,  # 是否使用未经 to_me 等处理过的消息
    use_cmd_start=True,  # 是否使用 COMMAND_START 作为命令前缀
    use_cmd_sep=True,  # 是否使用 COMMAND_SEP 作为命令分隔符
)


@pcr_update_chara.handle()
async def update_chara(event: GuildMessageEvent):
    """
    手动更新角色数据
    """
    a, b, c, d = await update_service.update_pcr_data()
    await pcr_update_chara.finish(
        f"更新前:\nCHARA_NAME:{a}\nCHARA_PROFILE:{b}\n更新后:\nCHARA_NAME:{c}\nCHARA_PROFILE:{d}"
    )


if plugin_config.plugin_is_auto:

    @scheduler.scheduled_job("cron", hour="17", minute="05")
    async def update_data_sdj():
        """
        定时更新PCR数据
        """
        await update_service.update_pool()
        await update_service.update_pcr_data()
        if plugin_config.plugin_is_notice:
            pass
        return


cmd = Alconna("查看PCR数据")
pcr_get_data = on_alconna(
    cmd,
    aliases={"查看数据"},
    priority=5,
    use_origin=False,  # 是否使用未经 to_me 等处理过的消息
    use_cmd_start=True,  # 是否使用 COMMAND_START 作为命令前缀
    use_cmd_sep=True,  # 是否使用 COMMAND_SEP 作为命令分隔符
)


@pcr_get_data.handle()
async def get_pcr_data(event: GuildMessageEvent):
    """
    手动更新卡池时试用此命令
    """
    a, b = await update_service.check_pcr_data()
    await pcr_get_data.finish(f"CHARA_NAME:{a}\nCHARA_PROFILE:{b}")
