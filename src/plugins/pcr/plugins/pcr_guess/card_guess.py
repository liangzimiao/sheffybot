# ref: https://github.com/GWYOG/GWYOG-Hoshino-plugins/blob/master/pcravatarguess
# Originally written by @GWYOG
# Reflacted by @Ice-Cirno
# GPL-3.0 Licensed
# Thanks to @GWYOG for his great contribution!

import asyncio
from datetime import timedelta

from nonebot.adapters.qq import GuildMessageEvent, MessageSegment
from nonebot.plugin import on_fullmatch, on_message

from ...services import GuessService
from .config import plugin_config

# BASE_WIN_COIN = 175
# RANK_WIN_COIN = 50
# GET_COIN_CD = 60 * 60


pic_side_length = plugin_config.card_pic_side_length
one_turn_time = plugin_config.card_one_turn_time
blacklist_id = plugin_config.card_blacklist_id

db_path = plugin_config.plugin_data_path / "pcr_card_guess.db"
guess_service = GuessService(db_path)


finish_event = asyncio.Event()


matcher = on_fullmatch(
    tuple(["猜卡面排行榜", "猜卡面排名", "猜卡面群排行"]), priority=5
)


@matcher.handle()
async def display_ranking(event: GuildMessageEvent):
    gid = event.get_session_id()
    gid = event.guild_id
    print(gid)
    ranking = guess_service.get_ranking(gid)
    print(ranking)
    msg = "【猜卡面小游戏排行榜】"
    pass
    await matcher.send(msg)


matcher = on_fullmatch(tuple(["猜卡面", "/猜卡面"]), priority=5)


@matcher.handle()
async def card_guess(event: GuildMessageEvent):
    gid = event.guild_id
    # 如果游戏正在进行，则返回提示信息
    if guess_service.is_playing(gid):
        await matcher.finish("游戏仍在进行中…")
    else:
        # 否则，开始一个新的游戏
        game = await guess_service.start_card_game(gid, blacklist_id, pic_side_length)
        print(game.answer)
        # 构造题目消息
        msg = MessageSegment.text(
            f"猜猜这个图片是哪位角色卡面的一部分?({one_turn_time}s后公布答案)"
        ) + MessageSegment.file_image(game.q_image)
        # 发送题目
        await matcher.send(msg)
        # 创建事件对象
        finish_event = asyncio.Event()
        # 创建临时事件响应器
        checker = on_message(
            rule=check_answer,
            priority=5,
            expire_time=timedelta(seconds=one_turn_time),
            temp=True,
        )

        @checker.handle()
        async def _(event: GuildMessageEvent):
            # 获取答对者id
            game.winner = event.get_user_id()
            # 获取答对次数
            n = guess_service.record(game.gid, game.winner)
            # 构造答对消息
            txt = f"\n猜对了，真厉害！TA已经猜对{n}次了~\n正确答案是{game.answer.name}"
            img = game.answer.card
            assert img is not None
            msg = (
                MessageSegment.mention_user(event.get_user_id())
                + MessageSegment.text(txt)
                + MessageSegment.file_image(img)
            )
            # 设置事件标识为True
            finish_event.set()
            # 发送答对
            await checker.send(msg)

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
            msg = (
                MessageSegment.text(txt)
                + MessageSegment.file_image(img)
                + MessageSegment.text(txt2)
            )
            # 发送答案
            await matcher.send(msg)
        finally:
            # 清除事件
            finish_event.clear()
            # 结束游戏
            guess_service.end_game(gid)
            print(f"游戏{game}结束")


def check_answer(event: GuildMessageEvent):
    """
    检查给定答案是否与游戏的答案匹配。

    参数:
        event (GuildMessageEvent): 包含消息的事件。

    返回值:
        bool: 如果答案与游戏的答案匹配，则为True；否则为False。
    """
    gid = event.guild_id
    # 获取用户答案
    user_answer = event.get_message().extract_plain_text().strip()
    # 获取小组所在游戏
    game = guess_service.get_game(gid)

    if not game:
        return False
    return guess_service.check_answer(user_answer, game)
