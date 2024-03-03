from nonebot.plugin import PluginMetadata
from nonebot_plugin_saa import Image, Text

from ..matcher import on_command
from ..services.query_service import QueryService

__plugin_meta__ = PluginMetadata(
    name="pcr_query",
    description="",
    usage=("[千里眼|rank表]"),
    config=None,
)
query = QueryService()

matcher = on_command("千里眼", priority=5)


@matcher.handle()
async def _():
    # 构造消息
    text, image_list = await query.get_gocha()
    msg = Text(text)
    for image in image_list:
        with open(image, "rb") as f:
            img: bytes = f.read()
        msg += Image(img)
    # 发送消息
    await msg.send()


"""
matcher = on_command("rank表", priority=5)


@matcher.handle()
async def _():
    # 构造消息
    msg = Text("【rank表】")
    # 发送消息
    await msg.send(at_sender=True)
"""
