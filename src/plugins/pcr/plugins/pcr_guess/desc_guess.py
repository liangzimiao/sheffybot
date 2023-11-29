# ref: https://github.com/GWYOG/GWYOG-Hoshino-plugins/blob/master/pcravatarguess
# Originally written by @GWYOG
# Reflacted by @Ice-Cirno
# GPL-3.0 Licensed
# Thanks to @GWYOG for his great contribution!

import asyncio
import random
from datetime import timedelta

from loguru import logger
from nonebot.adapters.qq import GuildMessageEvent, MessageSegment
from nonebot.plugin import on_fullmatch, on_message

from ...services import GuessService
from .config import plugin_config

turn_number = plugin_config.desc_turn_number
prepare_time = plugin_config.desc_prepare_time
one_turn_time = plugin_config.desc_one_turn_time

db_path = plugin_config.plugin_data_path / "pcr_desc_guess.db"
guess_service = GuessService(db_path)

matcher = on_fullmatch(
    tuple(["猜角色排行榜", "猜角色排名", "猜角色群排行"]), priority=5
)


@matcher.handle()
async def display_ranking(event: GuildMessageEvent):
    gid = event.get_session_id()
    gid = event.guild_id
    print(gid)
    ranking = guess_service.get_ranking(gid)
    print(ranking)
    msg = "【猜角色小游戏排行榜】"
    pass
    await matcher.send(msg)


matcher = on_fullmatch(tuple(["猜角色", "/猜角色", "猜人物", "/猜人物"]), priority=5)


@matcher.handle()
async def desc_guess(event: GuildMessageEvent):
    gid = event.guild_id
    # 如果游戏正在进行，则返回提示信息
    if guess_service.is_playing(gid):
        await matcher.finish("游戏仍在进行中…")
    else:
        # 否则，开始一个新的游戏
        game = await guess_service.start_desc_game(gid)
        logger.debug(
            f"游戏{type(game).__name__} gid：{game.gid} 答案：{game.answer.name}"
        )
        # 构造准备消息
        kws = list(game.profile.keys())
        random.shuffle(kws)
        kws = kws[:turn_number]
        txt = f"{prepare_time}秒后每隔{one_turn_time}秒我会给出某位角色的一个描述，根据这些描述猜猜她是谁~"
        msg = MessageSegment.text(txt)
        # 发送准备消息
        await matcher.send(msg)
        # 创建事件对象
        finish_event = asyncio.Event()
        # 创建临时事件响应器
        checker = on_message(
            rule=check_answer,
            priority=5,
            expire_time=timedelta(seconds=prepare_time + turn_number * one_turn_time),
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
            img = game.answer.icon
            assert img is not None
            msg = (
                MessageSegment.mention_user(event.get_user_id())
                + MessageSegment.text(txt)
                + MessageSegment.file_image(img)
            )
            # 设置事件标识为True
            finish_event.set()
            # 发送答对消息
            await checker.send(msg)

        # 进入准备时间
        await asyncio.sleep(prepare_time)
        # 进入一轮游戏
        for i, k in enumerate(kws):
            try:
                if game.winner:
                    return
                # 如果没有人答对，构造提示消息
                txt = f"提示{i + 1}/{len(kws)}:\n她的{k}是 {game.profile[k]}"
                msg = MessageSegment.text(txt)
                await matcher.send(msg)
                await asyncio.wait_for(finish_event.wait(), timeout=one_turn_time)
                # 清除事件
                finish_event.clear()
                # 结束游戏
                guess_service.end_game(gid)
                logger.success(f"游戏{type(game).__name__} gid：{game.gid}结束")
            except asyncio.TimeoutError:
                # 如果超时，说明没有人答对
                logger.info(f"游戏{type(game).__name__} gid：{game.gid}第{i + 1}轮结束")
        # 清除事件
        finish_event.clear()
        # 结束游戏
        guess_service.end_game(gid)
        logger.success(f"游戏{type(game).__name__} gid：{game.gid}结束")
        if game.winner:
            return
        # 构造最终消息
        txt = f"很遗憾，没有人答对~\n正确答案是：{game.answer.name}"
        img = game.answer.icon
        assert img is not None
        msg = MessageSegment.text(txt) + MessageSegment.file_image(img)
        # 发送最终消息
        await matcher.send(msg)


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


def my_generator(first_num: int, second_num: int):
    yield first_num
    while True:
        yield second_num
