from nonebot import on_regex
from nonebot.adapters import Event
from nonebot.plugin import PluginMetadata
from nonebot_plugin_saa import Image, Mention, Reply, Text
from nonebot_plugin_saa.registries import get_message_id

from ..config import pcr_config
from ..services.whois_service import WhoIsService

__plugin_meta__ = PluginMetadata(
    name="pcr_whois",
    description="根据花名册，快速识别角色",
    usage="[xx是谁|谁是xx]",
)

whois_service = WhoIsService()


whois_matcher = on_regex(r"^(.*)是谁([?？ ])?", priority=5)


@whois_matcher.handle()
async def _(event: Event):
    """
    处理 MessageEvent 并从事件的消息中提取名字。
    根据匹配结果发送响应。
    """

    # Add a TODO comment for 花名册cd
    # TODO: Implement 花名册cd functionality
    user_id = event.get_user_id()
    if pcr_config.pcr_whois_cd > 0:
        pass

    name = event.get_plaintext().strip()
    name = name.split("是", 1)[0]
    print(name)
    if not name:
        return
    result = await whois_service.guess_chara(name)
    if result.score < 60:
        return
    c = result.guess_chara
    assert c.icon is not None and c.name is not None
    msg = ""
    id = get_message_id(event)
    if pcr_config.pcr_whois_is_reply and id:
        msg += Reply(id)
    if result.is_guess:
        msg1 = f'兰德索尔似乎没有叫"{name}"的人...'
        await whois_matcher.send(msg1)
        msg += (
            Mention(user_id)
            + Text(f"您有{result.score}%的可能在找{result.guess_name}")
            + Image(c.icon)
            + Text(c.name)
        )
        await msg.send()
    else:
        msg += Mention(user_id) + Image(c.icon) + Text(c.name)
        await msg.send()
