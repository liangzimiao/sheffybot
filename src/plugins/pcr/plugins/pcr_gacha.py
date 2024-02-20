from nonebot.plugin import PluginMetadata, on_command
from nonebot_plugin_saa import Image, Mention, Text
from nonebot_plugin_session import EventSession

from ..services.gacha_service import Gacha, GachaService, chara_data, logger

__plugin_meta__ = PluginMetadata(
    name="pcr_gacha",
    description="""
    pcr相关的抽卡模拟
    """,
    usage="[单抽|十连|来一井|查看卡池|切换卡池]",
    config=None,
)

gacha_10_aliases = {
    "抽十连",
    "十连",
    "十连！",
    "十连抽",
    "来个十连",
    "来发十连",
    "来次十连",
    "抽个十连",
    "抽发十连",
    "抽次十连",
    "十连扭蛋",
    "扭蛋十连",
    "10连",
    "10连！",
    "10连抽",
    "来个10连",
}
gacha_1_aliases = [
    "单抽",
    "单抽！",
    "来发单抽",
    "来个单抽",
    "来次单抽",
    "扭蛋单抽",
    "单抽扭蛋",
]
gacha_300_aliases = {"抽一井", "来一井", "来发井", "抽发井", "天井扭蛋", "扭蛋天井"}
SUPER_LUCKY_LINE = 170

gacha_service = GachaService()


matcher = on_command("单抽", aliases=set(gacha_1_aliases), priority=5)


@matcher.handle()
async def _(session: EventSession):
    # 获取群组id and uid
    uid = session.id1
    gid = session.id2
    if gid is None or uid is None:
        return
    # 获取群组对应卡池
    gacha = await gacha_service.get_gacha(gid=gid)
    # 单抽
    c, h = await gacha.gacha_one(gacha.up_prob, gacha.s3_prob, gacha.s2_prob)
    # 构造消息
    assert c.icon
    msg = (
        Mention(uid)
        + Text(f'素敵な仲間が増えますよ！{c.name} {"★" * c.star}')
        + Image(c.icon)
    )
    # 发送消息
    await msg.send()


matcher = on_command("十连", aliases=set(gacha_10_aliases), priority=5)


@matcher.handle()
async def _(session: EventSession):
    # 获取群组id and uid
    uid = session.id1
    gid = session.id2
    if gid is None or uid is None:
        return
    # 获取群组对应卡池
    gacha = await gacha_service.get_gacha(gid=gid)
    # 十连
    c_list, hiishi = await gacha.gacha_ten()
    # 构造消息
    if hiishi >= SUPER_LUCKY_LINE:
        msg = Text("恭喜海豹！おめでとうございます！")
        await msg.send()
    msg = Mention(uid) + Text("\n素敵な仲間が増えますよ！\n")
    try:
        img = await gacha_service.draw_gacha(c_list)
        msg += Image(img)
    except Exception as e:
        logger.error(f"Draw_Gacha_Result error:{e}")
    result = [f'{c.name}{"★" * c.star}' for c in c_list]
    msg += Text(f"{' '.join(result[0:5])}")
    msg += Text(f"\n{' '.join(result[5:])}")
    # 发送消息
    await msg.send()


matcher = on_command("来一井", aliases=set(gacha_300_aliases), priority=5)


@matcher.handle()
async def _(session: EventSession):
    # 获取群组id and uid
    uid = session.id1
    gid = session.id2
    if gid is None or uid is None:
        return
    # 获取群组对应卡池
    gacha: Gacha = await gacha_service.get_gacha(gid=gid)
    # 来一井
    result = await gacha.gacha_tenjou()
    # 构造消息
    s3 = len(result["s3"])
    s2 = len(result["s2"])
    s1 = len(result["s1"])
    up = result["up_num"]
    res = result["s3"]
    length = len(res)
    if length == 0:
        msg = Text("竟...竟然没有3★？！")
        await msg.send()
    msg2 = Mention(uid) + Text("\n素敵な仲間が増えますよ！\n")
    try:
        if length != 0:
            img = await gacha_service.draw_gacha(res)
            msg2 += Image(img)
    except Exception as e:
        logger.error(f"Draw_Gacha_Result error:{e}")
    msg = [
        f"★★★×{s3} ★★×{s2} ★×{s1}",
        f"\n获得{up}个up角色与女神秘石×{50*(s3) + 10*s2 + s1}！\n第{result['first_up_pos']}抽首次获得up角色\n"
        if up
        else f"\n获得女神秘石{50*(up+s3) + 10*s2 + s1}个！\n",
    ]
    if up == 0 and s3 == 0:
        msg.append("太惨了，咱们还是退款删游吧...")
    elif up == 0 and s3 > 7:
        msg.append("up呢？我的up呢？")
    elif up == 0 and s3 <= 3:
        msg.append("这位酋长，大月卡考虑一下？")
    elif up == 0:
        msg.append("据说天井的概率只有12.16%")
    elif up <= 2:
        if result["first_up_pos"] < 50:
            msg.append("你的喜悦我收到了，滚去喂鲨鱼吧！")
        elif result["first_up_pos"] < 100:
            msg.append("已经可以了，您已经很欧了")
        elif result["first_up_pos"] > 290:
            msg.append("标 准 结 局")
        elif result["first_up_pos"] > 250:
            msg.append("补井还是不补井，这是一个问题...")
        else:
            msg.append("期望之内，亚洲水平")
    elif up == 3:
        msg.append("抽井母五一气呵成！您就是欧洲人？")
    elif up >= 4:
        msg.append("记忆碎片一大堆！您是托吧？")
    for i in msg:
        msg2 += Text(i)
    # 发送消息
    await msg2.send()


matcher = on_command(
    "查看卡池",
    aliases={
        "查看卡池",
        "康康卡池",
        "卡池資訊",
        "看看up",
        "看看UP",
        "卡池资讯",
    },
    priority=5,
)


@matcher.handle()
async def _(session: EventSession):
    # 获取群组id
    gid = session.id2
    if gid is None:
        return
    # 获取群组对应卡池
    gacha = await gacha_service.get_gacha(gid=gid)
    # 查看卡池 and 构造消息
    msg = Text(f"本期{gacha.pool_name}卡池主打的角色：\n")
    for up in gacha.up:
        up_chara = await chara_data.get_chara(name=up, star=3, need_icon=True)
        assert up_chara.icon
        msg += Text(f"{up_chara.name}") + Image(up_chara.icon)
    msg += Text(
        f"\nUP角色合计={(gacha.up_prob/10):.1f}% 3★出率={(gacha.s3_prob)/10:.1f}%"
    )
    # 发送消息
    await msg.send()


matcher = on_command("切换卡池", priority=5)


@matcher.handle()
async def _(session: EventSession):
    # 获取群组id
    gid = session.id2
    # 获取群组对应卡池
    pass
    # 切换卡池
    pass
    # 构造消息
    pass
    # 发送消息
    pass
