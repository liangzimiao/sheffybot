from nonebot import on_regex
from nonebot.adapters.qq.event import GuildMessageEvent
from nonebot.adapters.qq.message import Message, MessageSegment
from nonebot.plugin import PluginMetadata

from ...models import WhoIsGuessResult
from ...services import WhoIsService
from .config import Config, plugin_config

__plugin_meta__ = PluginMetadata(
    name="pcr_whois",
    description="""
    - [xx是谁？] 
    - [谁是xx？] #用于更新卡池
    """,
    usage="[xx是谁|谁是xx]",
    config=Config,
)

whois_service = WhoIsService()


whois_matcher = on_regex(r"^(.*)是谁([?？ ])?", priority=5)


@whois_matcher.handle()
async def _(event: GuildMessageEvent):
    """
    处理 MessageEvent 并从事件的消息中提取名字。
    根据匹配结果发送响应。
    """
    name = event.get_message().extract_plain_text().strip()
    name = name.split("是", 1)[0]
    print(name)
    if not name:
        return
    result: WhoIsGuessResult = await whois_service.guess_chara(name)
    c = result.guess_chara
    assert c.icon is not None and c.name is not None
    if result.score == 100:
        msg = MessageSegment.file_image(c.icon) + MessageSegment.text(c.name)
        await whois_matcher.send(msg, at_sender=True)
    elif result.score >= 60:
        msg = f'兰德索尔似乎没有叫"{name}"的人...'
        await whois_matcher.send(msg)
        msg = (
            MessageSegment.text(f"您有{result.score}%的可能在找{result.guess_name}")
            + MessageSegment.file_image(c.icon)
            + MessageSegment.text(c.name)
        )
        await whois_matcher.send(msg, at_sender=True)
