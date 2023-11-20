from arclet.alconna import Alconna


from nonebot import on_regex
from nonebot.plugin import PluginMetadata
from nonebot.adapters.qq.event import GuildMessageEvent


from nonebot_plugin_alconna import on_alconna


from .config import Config, plugin_config
from ...models import WhoIsGuessResult
from ...services import WhoIsService


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
    根据用户输入猜测，返回可能角色
    """
    name = event.get_message().extract_plain_text().strip()
    name = name.split("是", 1)[0]
    print(name)
    if not name:
        return
    result: WhoIsGuessResult = await whois_service.guess_name(name)
    if result.probability < 60:
        return
    if result.is_guess:
        name = name
        msg = f'兰德索尔似乎没有叫"{name}"的人...'
        await whois_matcher.send(Message(msg))
        msg = f"您有{result.probability}%的可能在找{result.guess_name} {c.icon.cqcode} {c.name}"
        await matcher.send(Message(msg))
    else:
        msg = f"{c.icon.cqcode} {c.name}"
        await matcher.send(Message(msg), at_sender=True)
