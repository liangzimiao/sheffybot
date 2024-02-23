from nonebot.adapters import Message
from nonebot.matcher import Matcher
from nonebot.params import ArgPlainText, CommandArg
from nonebot.plugin import PluginMetadata
from nonebot_plugin_saa import Image, Text

from ..matcher import on_command
from ..services.wiki_service import WikiService

__plugin_meta__ = PluginMetadata(
    name="pcr_wiki",
    description="""
    PCR相关的数据查询
    """,
    usage="[查头像|查角色|查卡面|查档案]",
    config=None,
)
wiki = WikiService()


matcher_chara = on_command("查角色", aliases={"查别名"}, priority=5)


@matcher_chara.handle()
async def _(matcher: Matcher, args: Message = CommandArg()):
    if args.extract_plain_text():
        matcher.set_arg("name", args)


@matcher_chara.got("name", prompt="请输入角色名")
async def got_func(name: str = ArgPlainText()):
    # 获取指定角色对象
    c = await wiki.get_chara(name)

    # 构造消息
    if c is None:
        msg = Text("未找到该角色")
    else:
        c_alias = await wiki.get_chara_alias(c)
        assert c.icon
        msg = Text(f"名字：{c.name}\n角色ID: {c.id}\n别名: {c_alias}") + Image(c.icon)
    # 发送消息
    await msg.send()


matcher_icon = on_command("查头像", priority=5)


@matcher_icon.handle()
async def _(matcher: Matcher, args: Message = CommandArg()):
    if args.extract_plain_text():
        matcher.set_arg("name", args)


@matcher_icon.got("name", prompt="请输入角色名")
async def icon_got_func(name: str = ArgPlainText()):
    # 获取指定角色对象
    c = await wiki.get_chara(name)
    # 构造消息
    if c is None:
        msg = Text("未找到该角色")
        await msg.send()
    else:
        icon_list = await wiki.get_chara_icon(name)
        msg = Text(f"名字：{c.name}\n角色ID: {c.id}")
        await msg.send()
        for icon in icon_list:
            msg = Image(icon)
            await msg.send()


matcher_card = on_command("查卡面", priority=5)


@matcher_card.handle()
async def _(matcher: Matcher, args: Message = CommandArg()):
    if args.extract_plain_text():
        matcher.set_arg("name", args)


@matcher_card.got("name", prompt="请输入角色名")
async def card_got_func(name: str = ArgPlainText()):
    # 获取指定角色对象
    c = await wiki.get_chara(name)
    # 构造消息
    if c is None:
        msg = Text("未找到该角色")
        await msg.send()
    else:
        card_list = await wiki.get_chara_card(name)
        msg = Text(f"名字：{c.name}\n角色ID: {c.id}")
        await msg.send()
        for card in card_list:
            msg = Image(card)
            await msg.send()


matcher_profile = on_command("查档案", priority=5)


@matcher_profile.handle()
async def _(matcher: Matcher, args: Message = CommandArg()):
    if args.extract_plain_text():
        matcher.set_arg("name", args)


@matcher_profile.got("name", prompt="请输入角色名")
async def profile_got_func(name: str = ArgPlainText()):
    # 获取指定角色对象
    c = await wiki.get_chara(name)
    # 构造消息
    if c is None:
        msg = Text("未找到该角色")
        await msg.send()
    else:
        profile = await wiki.get_chara_profile(c.id)
        msg = Text(f"ID: {c.id}\n{profile}")
        await msg.send()
