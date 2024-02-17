import asyncio
import random
from datetime import timedelta

from nonebot.adapters import Event
from nonebot.plugin import on_command, on_fullmatch, on_message
from nonebot_plugin_saa import Image, Mention, Text
from nonebot_plugin_session import EventSession

from ...config import pcr_config
from ...services.guess_service import GuessService, logger

turn_number = pcr_config.pcr_desc_turn_number
prepare_time = pcr_config.pcr_desc_prepare_time
one_turn_time = pcr_config.pcr_desc_one_turn_time

desc_db_path = pcr_config.pcr_data_path / "guess_games_data" / "pcr_desc_guess.db"
guess_service = GuessService(desc_db_path)

matcher = on_command("猜角色排名", aliases={"猜角色排行榜", "猜角色群排行"}, priority=5)


@matcher.handle()
async def display_ranking(session: EventSession):
    gid = session.id3 if session.id3 else (session.id2 if session.id2 else session.id1)
    assert gid
    platform = session.platform
    gid = f"{platform}_{gid}"
    print(gid)
    ranking = guess_service.get_ranking(gid)
    print(ranking)  # uid, count
    msg = "【猜角色小游戏排行榜】"
    # TODO uid转换nickname
    await matcher.send(msg)


matcher = on_fullmatch(tuple(["猜角色", "/猜角色", "猜人物", "/猜人物"]), priority=5)


@matcher.handle()
async def desc_guess(session: EventSession):
    gid = session.id3 if session.id3 else (session.id2 if session.id2 else session.id1)
    assert gid
    platform = session.platform
    gid = f"{platform}_{gid}"
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
        kws = list(game.question.keys())
        random.shuffle(kws)
        kws = kws[:turn_number]
        txt = f"{prepare_time}秒后每隔{one_turn_time}秒我会给出某位角色的一个描述，根据这些描述猜猜她是谁~"
        msg = Text(txt)
        # 发送准备消息
        await msg.send()
        # 创建事件对象
        finish_event = asyncio.Event()

        def check_answer(event: Event) -> bool:
            """
            检查给定答案是否与游戏的答案匹配。
            """
            # 获取用户答案
            user_answer = event.get_plaintext().strip()
            if not game:
                return False
            return guess_service.check_answer(user_answer, game)

        # 创建临时事件响应器
        checker = on_message(
            rule=check_answer,
            priority=5,
            expire_time=timedelta(seconds=prepare_time + turn_number * one_turn_time),
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
            img = game.answer.icon
            assert img is not None
            msg = Mention(event.get_user_id()) + Text(txt) + Image(img)
            # 设置事件标识为True
            finish_event.set()
            # 发送答对
            await msg.send()

        # 进入准备时间
        await asyncio.sleep(prepare_time)
        # 进入一轮游戏
        for i, k in enumerate(kws):
            try:
                if game.winner:
                    return
                # 如果没有人答对，构造提示消息
                txt = f"提示{i + 1}/{len(kws)}:\n她的{k}是 {game.question.get(k)}"
                msg = Text(txt)
                await msg.send()
                await asyncio.wait_for(finish_event.wait(), timeout=one_turn_time)
                # 清除事件
                finish_event.clear()
                # 结束游戏
                guess_service.end_game(gid)
                logger.debug(f"游戏{type(game).__name__} gid：{game.gid}结束")
            except asyncio.TimeoutError:
                # 如果超时，说明没有人答对
                logger.info(f"游戏{type(game).__name__} gid：{game.gid}第{i + 1}轮结束")
        # 清除事件
        finish_event.clear()
        # 结束游戏
        guess_service.end_game(gid)
        logger.debug(f"游戏{type(game).__name__} gid：{game.gid}结束")
        if game.winner:
            return
        # 构造最终消息
        txt = f"很遗憾，没有人答对~\n正确答案是：{game.answer.name}"
        img = game.answer.icon
        assert img is not None
        msg = Text(txt) + Image(img)
        # 发送最终消息
        await msg.send()


def my_generator(first_num: int, second_num: int):
    yield first_num
    while True:
        yield second_num
