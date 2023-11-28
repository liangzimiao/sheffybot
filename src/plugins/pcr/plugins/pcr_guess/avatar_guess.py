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

patch_size = plugin_config.avatar_patch_size
one_turn_time = plugin_config.avatar_one_turn_time
blacklist_id = plugin_config.avatar_blacklist_id

db_path = plugin_config.plugin_data_path / "pcr_avatar_guess.db"
guess_service = GuessService(db_path)


matcher = on_fullmatch(tuple(["猜头像排行", "猜头像排名", "猜头像排行榜"]), priority=5)


@matcher.handle()
async def display_ranking(event: GuildMessageEvent):
    gid = event.get_session_id()
    gid = event.guild_id
    print(gid)
    ranking = guess_service.get_ranking(gid)
    msg = "【猜头像小游戏排行榜】"
    pass
    await matcher.send(msg)


matcher = on_fullmatch("猜头像", priority=5)


@matcher.handle()
async def avatar_guess(event: GuildMessageEvent):
    gid = event.guild_id
    if guess_service.is_playing(gid):
        await matcher.finish("游戏仍在进行中…")
    else:
        game = await guess_service.start_avatar_game(gid, patch_size)
        assert game.image and game.answer
        print(game.answer.name)
        msg = MessageSegment.text(
            f"猜猜这个图片是哪位角色头像的一部分?({one_turn_time}s后公布答案)"
        ) + MessageSegment.file_image(game.image)
        await matcher.send(msg)
        finish_event = asyncio.Event()
        checker = on_message(
            rule=check_answer,
            priority=7,
            expire_time=timedelta(seconds=one_turn_time),
            temp=True,
        )

        @checker.handle()
        async def _(event: GuildMessageEvent):
            assert game.answer and game.answer.icon
            n = guess_service.record(game.gid, event.get_user_id())
            msg = (
                MessageSegment.mention_user(event.get_user_id())
                + MessageSegment.text(
                    f"猜对了，真厉害！TA已经猜对{n}次了~\n正确答案是{game.answer.name}"
                )
                + MessageSegment.file_image(game.answer.icon)
            )
            finish_event.set()
            await checker.send(msg)

        try:
            finish_event = asyncio.Event()
            await asyncio.wait_for(
                finish_event.wait(), timeout=one_turn_time
            )  # 等待15秒或者收到指令
        except asyncio.TimeoutError:
            if game.winner:
                return
            txt = f"正确答案是：{game.answer.name}"
            img = game.answer.icon
            assert img is not None
            msg = (
                MessageSegment.text(txt)
                + MessageSegment.file_image(img)
                + MessageSegment.text("\n很遗憾，没有人答对~")
            )
            await matcher.send(msg)  # 发送消息
        finally:
            finish_event.clear()  # 清除事件标志
            guess_service.end_game(gid)
            print("事件响应器结束")


def check_answer(event: GuildMessageEvent) -> bool:
    answer = event.get_message().extract_plain_text().strip()
    game = guess_service.get_game(event.guild_id)
    answer = guess_service.match_answer(answer)
    if not game:
        return False
    assert game.answer is not None
    if answer.name == game.answer.name:
        return True
    elif answer == "取消":
        guess_service.end_game(game.gid)
        return True
    else:
        return False
