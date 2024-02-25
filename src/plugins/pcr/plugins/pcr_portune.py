from nonebot.adapters import Event
from nonebot.plugin import PluginMetadata
from nonebot_plugin_saa import Image, Mention, Reply, Text
from nonebot_plugin_saa.registries import get_message_id

from ..config import pcr_config
from ..matcher import on_command
from ..services.portune_service import DailyNumberLimiter, portune_service

__plugin_meta__ = PluginMetadata(
    name="pcr_portune",
    description="""
    随机角色预测今日运势
    准确率高达114.514%！
    """,
    usage="[抽签|人品|运势]",
)

is_reply = pcr_config.pcr_portune_is_reply
lmt = DailyNumberLimiter(max_num=pcr_config.pcr_portune_limit)


pcr_portune = on_command("抽签", aliases={"人品", "运势"}, priority=5)


@pcr_portune.handle()
async def portune(event: Event):
    if not lmt.check(event.get_user_id()):
        msg = Mention(event.get_user_id()) + Text("你今天已经抽过签了，欢迎明天再来~")
    else:
        lmt.increase(event.get_user_id())
        pic = portune_service.drawing_pic()
        id = get_message_id(event)
        if is_reply and id:
            msg = Reply(id) + Mention(event.get_user_id()) + Image(pic)
        else:
            msg = Mention(event.get_user_id()) + Image(pic)
    await msg.send()
