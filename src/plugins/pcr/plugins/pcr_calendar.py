import asyncio
import json
import re
import traceback
from io import BytesIO
from pathlib import Path

from nonebot.params import RegexGroup
from nonebot.plugin import PluginMetadata, on_regex
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_saa import (
    Image,
    PlatformTarget,
    SaaTarget,
    Text,
    enable_auto_select_bot,
)
from nonebot_plugin_session import EventSession

from ..config import pcr_config
from ..services.calendar_service import generate_day_schedule, logger

enable_auto_select_bot()


__plugin_meta__ = PluginMetadata(
    name="pcr_calendar",
    description="""
    公主连结活动日历
    日历 : 查看本群订阅服务器日历
    [国台日]服日历 : 查看指定服务器日程
    [国台日]服日历 on/off : 订阅/取消订阅指定服务器的日历推送
    日历 time 时:分 : 设置日历推送时间
    日历 status : 查看本群日历推送设置
    """,
    usage="[[国台日]服日历]",
    config=None,
)


pcr_data_path: Path = pcr_config.pcr_data_path
"""PCR数据存放路径"""
path = pcr_data_path / "calendar"

gid_data = {}


matcher = on_regex(pattern=r"^([国台日])?服?日[历程](.*)")


@matcher.handle()
async def _(session: EventSession, target: SaaTarget, matched_groups=RegexGroup()):
    # 获取群组id and uid
    gid = session.id2
    if gid is None:
        return
    platform = session.platform
    gid = f"{platform}_{gid}"
    # 获取参数
    server_name = matched_groups[0]
    if server_name == "台":
        server = "tw"
    elif server_name == "日":
        server = "jp"
    elif server_name == "国":
        server = "cn"
    elif gid in gid_data and len(gid_data[gid]["server_list"]) > 0:
        server = gid_data[gid]["server_list"][0]
    else:
        server = "cn"
    cmd = matched_groups[1]
    if not cmd:
        im = await generate_day_schedule(server)
        bytes_io = BytesIO()
        # 将图像保存到 BytesIO 对象中
        im.save(bytes_io, format="png")
        # 将光标移动到字节流的起始位置
        bytes_io.seek(0)
        msg = Image(bytes_io)
    else:
        if gid not in gid_data:
            gid_data[gid] = {
                "server_list": [],
                "hour": 8,
                "minute": 0,
            }
        if "on" in cmd:
            if server not in gid_data[gid]["server_list"]:
                gid_data[gid]["target"] = target.dict()
                gid_data[gid]["server_list"].append(server)
            save_data()
            msg = Text(f"{server}日程推送已开启")
        elif "off" in cmd:
            if server not in gid_data[gid]["server_list"]:
                del gid_data[gid]["target"]
                gid_data[gid]["server_list"].remove(server)
            save_data()
            msg = Text(f"{server}日程推送已关闭")
        elif "time" in cmd:
            match = re.search(r"(\d*):(\d*)", cmd)
            if not match or len(match.groups()) < 2:
                msg = Text("请指定推送时间")
            else:
                gid_data[gid]["hour"] = int(match.group(1))
                gid_data[gid]["minute"] = int(match.group(2))
                msg = Text(
                    f"推送时间已设置为: {gid_data[gid]['hour']}:{gid_data[gid]['minute']:02d}"
                )
        elif "status" in cmd:
            msg = Text(f"订阅日历: {gid_data[gid]['server_list']}")
            msg += Text(
                f"\n推送时间: {gid_data[gid]['hour']}:{gid_data[gid]['minute']:02d}"
            )
        else:
            msg = Text("指令错误")
        update_guild_schedule(gid)
        save_data()
    await msg.send()


def load_data():
    if not path.exists():
        return
    try:
        with open(path / "pcr_data.json", encoding="utf8") as f:
            data = json.load(f)
            for k, v in data.items():
                gid_data[k] = v
    except Exception:
        traceback.print_exc()


def save_data():
    path.mkdir(parents=True, exist_ok=True)
    try:
        with open(path / "pcr_data.json", "w", encoding="utf8") as f:
            json.dump(gid_data, f, ensure_ascii=False, indent=2)
    except Exception:
        traceback.print_exc()


async def send_calendar(gid):
    if str(gid) not in gid_data:
        return

    for server in gid_data[gid]["server_list"]:
        im = await generate_day_schedule(server)
        bytes_io = BytesIO()
        # 将图像保存到 BytesIO 对象中
        im.save(bytes_io, format="png")
        # 将光标移动到字节流的起始位置
        bytes_io.seek(0)
        msg = Image(bytes_io)
        for _ in range(5):  # 失败重试5次
            try:
                await msg.send_to(
                    target=PlatformTarget.deserialize(gid_data[gid]["target"])
                )
                logger.info(f"gid:{gid} 推送{server}日历成功")
                break
            except Exception:
                logger.info(f"gid:{gid} 推送{server}日历失败")
            await asyncio.sleep(60)


def update_guild_schedule(gid):
    if gid not in gid_data:
        return
    scheduler.add_job(
        send_calendar,
        "cron",
        args=(gid,),
        id=f"calendar_{gid}",
        replace_existing=True,
        hour=gid_data[gid]["hour"],
        minute=gid_data[gid]["minute"],
    )


def startup():
    load_data()
    for gid in gid_data:
        update_guild_schedule(gid)


startup()
