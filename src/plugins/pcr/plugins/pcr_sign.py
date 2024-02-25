from io import BytesIO

from nonebot.log import logger
from nonebot.plugin import PluginMetadata
from nonebot_plugin_saa import Image, Text
from nonebot_plugin_session import EventSession

from ..matcher import on_command
from ..services.sign_service import sign_service as sign

__plugin_meta__ = PluginMetadata(
    name="pcr签到",
    description="从 hoshino 搬来的 pcr 签到\n签到(获得好感和 pcr 的印章)",
    usage=("[签到|盖章|收集册]"),
    config=None,
)


give_okodokai = on_command("盖章", aliases={"签到", "妈!"}, priority=30, block=True)


@give_okodokai.handle()
async def _(session: EventSession):
    # 获取群组id and uid
    gid = session.id3 if session.id3 else (session.id2 if session.id2 else None)
    assert gid
    platform = session.platform
    gid = f"{platform}_{gid}"
    uid = session.id1
    if gid is None or uid is None:
        return
    # 签到
    res = await sign.get_sign_card(uid=uid, gid=gid)
    if isinstance(res, str):
        await give_okodokai.finish(res)
    elif isinstance(res, BytesIO):
        await Image(res).send(at_sender=True)


storage = on_command(
    "收集册",
    aliases={
        "签到排行榜",
    },
    priority=30,
    block=True,
)


@storage.handle()
async def _(session: EventSession):
    # 获取群组id and uid
    gid = session.id3 if session.id3 else (session.id2 if session.id2 else None)
    assert gid
    platform = session.platform
    gid = f"{platform}_{gid}"
    uid = session.id1
    if gid is None or uid is None:
        return

    result = await sign.get_collection(gid, uid)

    # 整合信息并发送

    # 构造消息
    msg = Image(result["collection_img"]) + Text(
        f"图鉴完成度: {result['cards_num']}\n当前群排名: {result['ranking_desc']}\n{result['rank_text']}"
    )

    await msg.send(at_sender=True)
