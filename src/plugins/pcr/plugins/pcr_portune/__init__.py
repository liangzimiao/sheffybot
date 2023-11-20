from nonebot.plugin import PluginMetadata
from arclet.alconna import Alconna, Args, Option
from nonebot_plugin_alconna import on_alconna

from nonebot.adapters.qq.event import GuildMessageEvent
from nonebot.adapters.qq import MessageSegment, Message
from nonebot.adapters.qq.models import MessageReference

from ...services.portune_service import DailyNumberLimiter, PortuneService
from .config import Config, plugin_config


__plugin_meta__ = PluginMetadata(
    name="pcr_portune",
    description="""
    [抽签|人品|运势]
    随机角色预测今日运势
    准确率高达114.514%！
    """,
    usage="[抽签|人品|运势]",
    config=Config,
)

is_reply = plugin_config.plugin_is_reply
lmt = DailyNumberLimiter(max_num=plugin_config.plugin_limit)
portune_service = PortuneService()


cmd = Alconna("抽签", Option("-c", Args["target", str]))
pcr_portune = on_alconna(
    cmd,
    aliases={"人品", "运势"},
    priority=0,
    use_origin=False,  # 是否使用未经 to_me 等处理过的消息
    use_cmd_start=True,  # 是否使用 COMMAND_START 作为命令前缀
    use_cmd_sep=True,  # 是否使用 COMMAND_SEP 作为命令分隔符
)


@pcr_portune.handle()
async def portune(event: GuildMessageEvent):
    if not lmt.check(event.get_user_id()):
        msg = Message(MessageSegment.mention_user(user_id=event.get_user_id()))
        msg += MessageSegment.text("你今天已经抽过签了，欢迎明天再来~")
        await pcr_portune.finish(message=msg)
    else:
        lmt.increase(event.get_user_id())
    pic = portune_service.drawing_pic()
    if is_reply:
        msgr = MessageReference(message_id=event.id)
        msg = Message(MessageSegment.reference(msgr))
        msg += Message(MessageSegment.mention_user(user_id=event.get_user_id()))
        msg += MessageSegment.file_image(data=pic)
    else:
        msg = Message(MessageSegment.mention_user(user_id=event.get_user_id()))
        msg += MessageSegment.file_image(data=pic)
    await pcr_portune.send(message=msg)
