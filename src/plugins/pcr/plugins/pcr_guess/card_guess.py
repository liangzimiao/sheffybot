import asyncio
from datetime import timedelta

from nonebot.adapters import Bot, Event
from nonebot.plugin import on_command, on_fullmatch, on_message
from nonebot_plugin_saa import Image, Text
from nonebot_plugin_session import EventSession
from nonebot_plugin_userinfo import get_user_info

from ...config import pcr_config
from ...services.guess_service import GuessService, logger

# BASE_WIN_COIN = 175
# RANK_WIN_COIN = 50
# GET_COIN_CD = 60 * 60


blacklist_id = []
pic_side_length = pcr_config.pcr_card_pic_side_length
one_turn_time = pcr_config.pcr_card_one_turn_time

card_db_path = pcr_config.pcr_data_path / "guess_games" / "pcr_card_guess.db"
guess_service = GuessService(card_db_path)


matcher = on_command("猜卡面排名", aliases={"猜卡面排行榜", "猜卡面群排行"}, priority=5)


@matcher.handle()
async def display_ranking(bot: Bot, event: Event, session: EventSession):
    gid = session.id3 if session.id3 else (session.id2 if session.id2 else session.id1)
    assert gid
    platform = session.platform
    gid = f"{platform}_{gid}"
    print(gid)
    ranking = guess_service.get_ranking(gid)
    print(ranking)  # uid, count
    msg = "【猜卡面小游戏排行榜】"
    for uid, count in ranking:
        user = await get_user_info(bot=bot, event=event, user_id=uid)
        if not user:
            msg += f"\n{uid}：{count}次"
        else:
            msg += f"\n{user.user_name}：{count}次"
    await matcher.send(msg)


matcher = on_fullmatch(tuple(["猜卡面", "/猜卡面"]), priority=5)


@matcher.handle()
async def card_guess(session: EventSession):
    gid = session.id3 if session.id3 else (session.id2 if session.id2 else session.id1)
    assert gid
    platform = session.platform
    gid = f"{platform}_{gid}"
    # 如果游戏正在进行，则返回提示信息
    if guess_service.is_playing(gid):
        await matcher.finish("游戏仍在进行中…")
    else:
        # 否则，开始一个新的游戏
        game = await guess_service.start_card_game(gid, blacklist_id, pic_side_length)
        logger.debug(f"PCR猜卡面游戏 gid：{game.gid} 答案：{game.answer.name}")
        # 构造题目消息
        msg = Text(
            f"猜猜这个图片是哪位角色卡面的一部分?({one_turn_time}s后公布答案)"
        ) + Image(game.question)
        # 发送题目
        await msg.send()
        # 创建事件对象
        finish_event = asyncio.Event()

        async def check_answer(event: Event) -> bool:
            """
            检查给定答案是否与游戏的答案匹配。
            """
            # 获取用户答案
            user_answer = event.get_plaintext().strip()
            if not game:
                return False
            return await guess_service.check_answer(user_answer, game)

        # 创建临时事件响应器
        checker = on_message(
            rule=check_answer,
            priority=5,
            expire_time=timedelta(seconds=one_turn_time),
            temp=True,
        )

        @checker.handle()
        async def _(event: Event):
            # 获取答对者id
            game.winner = event.get_user_id()
            # 获取答对次数
            n = guess_service.record(game.gid, game.winner)
            # 构造答对消息
            txt = f"\n猜对了，真厉害！TA已经猜对{n}次了~\n正确答案是{game.answer.name}"
            img = game.answer.card
            assert img is not None
            msg = Text(txt) + Image(img)
            # 设置事件标识为True
            finish_event.set()
            # 发送答对消息
            await msg.send(at_sender=True)

        # 等待15秒或者收到指令
        try:
            await asyncio.wait_for(
                finish_event.wait(), timeout=one_turn_time
            )  # 等待15秒或者收到指令
        except asyncio.TimeoutError:
            # 如果超时，说明没有人答对
            if game.winner:
                return
            # 构造答案消息
            txt = f"正确答案是：{game.answer.name}"
            txt2 = "\n很遗憾，没有人答对~"
            img = game.answer.card
            assert img is not None
            msg = Text(txt) + Image(img) + Text(txt2)
            # 发送答案
            await msg.send()
        finally:
            # 清除事件
            finish_event.clear()
            # 结束游戏
            guess_service.end_game(gid)
            logger.debug(f"PCR猜卡面游戏 gid：{game.gid} 结束")
