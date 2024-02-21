import ast
import asyncio
import base64
import datetime
import math
import re
import time
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path

import aiohttp
from PIL import Image, ImageDraw, ImageFont

from ..config import pcr_config
from ..logger import PCRLogger as Logger

logger = Logger("PCR-Calendar")

item_height = 45
pcr_res_path: Path = pcr_config.pcr_resources_path
"""PCR资源存放路径"""
font_path = pcr_res_path / "calendar" / "wqy-microhei.ttc"
font = ImageFont.truetype(font_path, int(item_height * 0.67))
item_height = 45

color = [
    {"front": "black", "back": "white"},
    {"front": "white", "back": "ForestGreen"},
    {"front": "white", "back": "DarkOrange"},
    {"front": "white", "back": "BlueViolet"},
]


def create_image(item_number, title_len):
    width = int(item_height * title_len * 0.7)
    height = item_number * item_height
    im = Image.new("RGBA", (width, height), (255, 255, 255, 255))  # type:ignore
    return im


def draw_rec(im, color, x, y, w, h, r):
    draw = ImageDraw.Draw(im)
    draw.rectangle((x + r, y, x + w - r, y + h), fill=color)
    draw.rectangle((x, y + r, x + w, y + h - r), fill=color)
    r = r * 2
    draw.ellipse((x, y, x + r, y + r), fill=color)
    draw.ellipse((x + w - r, y, x + w, y + r), fill=color)
    draw.ellipse((x, y + h - r, x + r, y + h), fill=color)
    draw.ellipse((x + w - r, y + h - r, x + w, y + h), fill=color)


def draw_text(im, x, y, w, h, text, align, color):
    draw = ImageDraw.Draw(im)
    # tw, th = draw.textlength(text, font=font)
    _, _, tw, th = draw.textbbox((0, 0), text, font=font)
    y = y + (h - th) / 2
    if align == 0:  # 居中
        x = x + (w - tw) / 2
    elif align == 1:  # 左对齐
        x = x + 5
    elif align == 2:  # 右对齐
        x = x + w - tw - 5
    draw.text((x, y), text, fill=color, font=font)


def draw_item(im, n, t, text, days):
    if t >= len(color):
        t = 1
    x = 0
    y = n * item_height

    width = im.width
    height = int(item_height * 0.95)

    draw_rec(im, color[t]["back"], x, y, width, height, int(item_height * 0.1))

    draw_text(im, x, y, width, height, text, 1, color[t]["front"])

    if days > 0:
        text1 = f"{days}天后结束"
    elif days < 0:
        text1 = f"{-days}天后开始"
    else:
        text1 = "即将结束"
    draw_text(im, x, y, width, height, text1, 2, color[t]["front"])


def draw_title(im, n, left=None, middle=None, right=None):
    x = 0
    y = n * item_height
    width = im.width
    height = int(item_height * 0.95)

    draw_rec(im, color[0]["back"], x, y, width, height, int(item_height * 0.1))
    if middle:
        draw_text(im, x, y, width, height, middle, 0, color[0]["front"])
    if left:
        draw_text(im, x, y, width, height, left, 1, color[0]["front"])
    if right:
        draw_text(im, x, y, width, height, right, 2, color[0]["front"])


translate_list = {
    "ベリーハード": "VH",
    "ハード": "困难",
    "ノーマル": "普通",
    "ノマクエ": "普通",
    "ダンジョン": "地下城玛娜",
    "ルナの塔": "露娜塔",
    "クランバトル": "公会战",
    "プレイヤー": "玩家",
}


def transform_gamewith_calendar(html_text):
    data_list = re.findall(r"data-calendar='(.*?)'", html_text, re.S)
    event_list = {}
    for data in data_list:
        event = ast.literal_eval(data)
        start = time.localtime(event["start_time"])
        end = time.localtime(event["end_time"])
        # gamewith: 1 庆典活动 2 剧情活动 3 工会战 4 露娜塔 5 复刻活动
        type_id = int(event["color_id"])
        if type_id == 1:
            type_id = 2
        elif type_id == 3:
            type_id = 3
        else:
            type_id = 1
        name = event["event_name"]
        for k, v in translate_list.items():
            name = name.replace(k, v)
        event_list[event["id"]] = {
            "name": name,
            "start_time": time.strftime("%Y/%m/%d %H:%M:%S", start),
            "end_time": time.strftime("%Y/%m/%d %H:%M:%S", end),
            "type": type_id,
        }
    return list(event_list.values())


keyword_list = [
    "year",
    "month",
    "day",
    "qdhd",  # 庆典活动
    "tdz",  # 团队战
    "tbhd",  # 特别活动
    "jqhd",  # 剧情活动
    "jssr",  # 角色生日
]

event_keyword_list = [
    "qdhd",  # 庆典活动 04:59
    "tbhd",  # 特别活动 23:59
    "jqhd",  # 剧情活动 23:59
    "tdz",  # 团队战 23:59
]


class ContentParse(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.data = []
        self.is_title = False

    def handle_starttag(self, tag, attrs):
        if len(attrs) != 0 and "cl-t" in attrs[0]:
            self.is_title = True
        else:
            self.is_title = False

    def handle_data(self, data):
        if self.is_title:
            self.data.append(data)


def parse_content(day_content):
    content_html = ""
    data = {}
    for keyword in event_keyword_list:
        content_html = day_content[keyword]
        parser = ContentParse()
        parser.feed(content_html)
        data[keyword] = parser.data
    return data


def extract_calendar_data(js_text):
    # 提取js的data部分转换为python对象
    data_str = re.search(r"\[.*?\]", js_text, re.S)
    assert data_str
    data_str = data_str.group(0)
    data_str = data_str.replace("//", "#")
    for keyword in keyword_list:
        data_str = data_str.replace(keyword, f'"{keyword}"')
    data = ast.literal_eval(data_str)
    # 解析活动内容html
    for i in range(len(data)):
        for day in data[i]["day"]:
            content = parse_content(data[i]["day"][day])
            data[i]["day"][day] = content
    return data


def transform_calendar_data(data):
    event_cache = {}
    event_list = []
    today = datetime.date(
        datetime.date.today().year,
        datetime.date.today().month,
        datetime.date.today().day,
    )
    for i in range(len(data)):
        for day_str in data[i]["day"]:
            # print(data[i]['year'], data[i]['month'], day_str, data[i]['day'][day_str])
            # 遍历本日活动
            year = int(data[i]["year"])
            month = int(data[i]["month"])
            day = int(day_str)
            event_number = 0
            for keyword in event_keyword_list:
                end_time = "23:59"
                if keyword == "qdhd":
                    end_time = "04:59"
                for event_name in data[i]["day"][day_str][keyword]:
                    event_number = event_number + 1
                    if event_name not in event_cache.keys():
                        # event_cache[event_name] = {'year': year, 'month': month, 'day': int(day)}
                        event_cache[event_name] = {
                            "start_year": year,
                            "start_month": month,
                            "start_day": day,
                            "end_year": year,
                            "end_month": month,
                            "end_day": day,
                            "end_time": end_time,
                        }
            try:
                diff = (datetime.date(year, month, day) - today) / datetime.timedelta(1)
            except Exception:
                continue
            if diff == 0 and event_number == 0:  # 无今日数据
                return []
            for event_name in list(event_cache.keys()):
                is_active = False
                for keyword in event_keyword_list:
                    if event_name in data[i]["day"][day_str][keyword]:
                        is_active = True
                if is_active:
                    event_cache[event_name]["end_year"] = year
                    event_cache[event_name]["end_month"] = month
                    event_cache[event_name]["end_day"] = day
                else:
                    event_list.append(
                        {
                            "title": event_name,
                            "start": f'{event_cache[event_name]["start_year"]}/{event_cache[event_name]["start_month"]}/{event_cache[event_name]["start_day"]} 05:00',
                            "end": f'{event_cache[event_name]["end_year"]}/{event_cache[event_name]["end_month"]}/{event_cache[event_name]["end_day"]} {event_cache[event_name]["end_time"]}',
                        }
                    )
                    event_cache.pop(event_name)
    for event_name in list(event_cache.keys()):
        event_list.append(
            {
                "title": event_name,
                "start": f'{event_cache[event_name]["start_year"]}/{event_cache[event_name]["start_month"]}/{event_cache[event_name]["start_day"]} 05:00',
                "end": f'{event_cache[event_name]["end_year"]}/{event_cache[event_name]["end_month"]}/{event_cache[event_name]["end_day"]} {event_cache[event_name]["end_time"]}',
            }
        )
    return event_list


def transform_bilibili_calendar(data):
    data = extract_calendar_data(data)
    data = transform_calendar_data(data)
    return data


# type 0普通 1 活动 2双倍 3 公会战

event_data = {
    "cn": [],
    "cnb": [],
    "tw": [],
    "jp": [],
}

event_updated = {
    "cn": "",
    "cnb": "",
    "tw": "",
    "jp": "",
}

lock = {
    "cn": asyncio.Lock(),
    "cnb": asyncio.Lock(),
    "tw": asyncio.Lock(),
    "jp": asyncio.Lock(),
}


async def query_data(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                return await resp.json()
    except Exception:
        pass
    return None


async def load_event_bilibili():
    data = ""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://static.biligame.com/pcr/gw/calendar.js"
            ) as resp:
                data = await resp.text("utf-8")
                data = transform_bilibili_calendar(data)
    except Exception:
        print("解析B站日程表失败")
        return 1
    if data:
        if len(data) == 0:
            print("B站日程表无数据")
            return 1
        event_data["cnb"] = []
        for item in data:
            start_time = datetime.datetime.strptime(item["start"], r"%Y/%m/%d %H:%M")
            end_time = datetime.datetime.strptime(item["end"], r"%Y/%m/%d %H:%M")
            event = {
                "title": item["title"],
                "start": start_time,
                "end": end_time,
                "type": 1,
            }
            if "倍" in event["title"]:
                event["type"] = 2
            elif "团队战" in event["title"]:
                event["type"] = 3
            event_data["cnb"].append(event)
        return 0
    return 1


async def load_event_cn():
    data = await query_data("https://pcrbot.github.io/calendar-updater-action/cn.json")
    if data:
        event_data["cn"] = []
        for item in data:
            start_time = datetime.datetime.strptime(
                item["start_time"], r"%Y/%m/%d %H:%M:%S"
            )
            end_time = datetime.datetime.strptime(
                item["end_time"], r"%Y/%m/%d %H:%M:%S"
            )
            event = {
                "title": item["name"],
                "start": start_time,
                "end": end_time,
                "type": 1,
            }
            if "倍" in event["title"]:
                event["type"] = 2
            elif "公会战" in event["title"]:
                event["type"] = 3
            event_data["cn"].append(event)
        return 0
    return 1


async def load_event_tw():
    data = await query_data("https://pcredivewiki.tw/static/data/event.json")
    if data:
        event_data["tw"] = []
        for item in data:
            start_time = datetime.datetime.strptime(
                item["start_time"], r"%Y/%m/%d %H:%M"
            )
            end_time = datetime.datetime.strptime(item["end_time"], r"%Y/%m/%d %H:%M")
            event = {
                "title": item["campaign_name"],
                "start": start_time,
                "end": end_time,
                "type": 1,
            }
            if "倍" in event["title"]:
                event["type"] = 2
            elif "戰隊" in event["title"]:
                event["type"] = 3
            event_data["tw"].append(event)
        return 0
    return 1


async def load_event_jp():
    data = await query_data(
        "https://cdn.jsdelivr.net/gh/pcrbot/calendar-updater-action@gh-pages/jp.json"
    )
    if data:
        event_data["jp"] = []
        for item in data:
            start_time = datetime.datetime.strptime(
                item["start_time"], r"%Y/%m/%d %H:%M:%S"
            )
            end_time = datetime.datetime.strptime(
                item["end_time"], r"%Y/%m/%d %H:%M:%S"
            )
            event = {
                "title": item["name"],
                "start": start_time,
                "end": end_time,
                "type": 1,
            }
            if "倍" in event["title"]:
                event["type"] = 2
            elif "公会战" in event["title"]:
                event["type"] = 3
            event_data["jp"].append(event)
        return 0
    return 1


async def load_event_gamewith():
    data = ""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://gamewith.jp/pricone-re/") as resp:
                data = await resp.text("utf-8")
                data = transform_gamewith_calendar(data)
    except Exception:
        print("解析gamewith日程表失败")
        return 1
    if data:
        event_data["jp"] = []
        for item in data:
            start_time = datetime.datetime.strptime(
                item["start_time"], r"%Y/%m/%d %H:%M:%S"
            )
            end_time = datetime.datetime.strptime(
                item["end_time"], r"%Y/%m/%d %H:%M:%S"
            )
            event = {
                "title": item["name"],
                "start": start_time,
                "end": end_time,
                "type": item["type"],
            }
            event_data["jp"].append(event)
        return 0
    return 1


async def load_event(server):
    if server == "cnb":
        return await load_event_bilibili()
    elif server == "cn":
        return await load_event_cn()
    elif server == "tw":
        return await load_event_tw()
    elif server == "jp":
        return await load_event_gamewith()
    return 1


def get_pcr_now(offset):
    pcr_now = datetime.datetime.now()
    if pcr_now.hour < 5:
        pcr_now -= datetime.timedelta(days=1)
    pcr_now = pcr_now.replace(
        hour=18, minute=0, second=0, microsecond=0
    )  # 用晚6点做基准
    pcr_now = pcr_now + datetime.timedelta(days=offset)
    return pcr_now


async def get_events(server, offset, days):
    events = []
    pcr_now = datetime.datetime.now()
    if pcr_now.hour < 5:
        pcr_now -= datetime.timedelta(days=1)
    pcr_now = pcr_now.replace(
        hour=18, minute=0, second=0, microsecond=0
    )  # 用晚6点做基准

    await lock[server].acquire()
    try:
        t = pcr_now.strftime("%y%m%d")
        if event_updated[server] != t:
            if await load_event(server) == 0:
                event_updated[server] = t
    finally:
        lock[server].release()

    start = pcr_now + datetime.timedelta(days=offset)
    end = start + datetime.timedelta(days=days)
    end -= datetime.timedelta(hours=18)  # 晚上12点结束

    for event in event_data[server]:
        if (
            end > event["start"] and start < event["end"]
        ):  # 在指定时间段内 已开始 且 未结束
            event["start_days"] = math.ceil(
                (event["start"] - start) / datetime.timedelta(days=1)
            )  # 还有几天开始
            event["left_days"] = math.floor(
                (event["end"] - start) / datetime.timedelta(days=1)
            )  # 还有几天结束
            events.append(event)
    events.sort(
        key=lambda item: item["type"] * 100 - item["left_days"], reverse=True
    )  # 按type从大到小 按剩余天数从小到大
    return events


server_name = {
    "cn": "国服",
    "tw": "台服",
    "jp": "日服",
}


def im2base64str(im):
    io = BytesIO()
    im.save(io, "png")
    base64_str = f"base64://{base64.b64encode(io.getvalue()).decode()}"
    return base64_str


async def generate_day_schedule(server="cn"):
    if server == "cn":
        events = await get_events("cn", 0, 7)
        event_sb = await get_events("cnb", 0, 7)
        if len(events) < len(event_sb):
            events = event_sb
    else:
        events = await get_events(server, 0, 7)

    has_prediction = False
    title_len = 25
    for event in events:
        if event["start_days"] > 0:
            has_prediction = True
        title_len = max(title_len, len(event["title"]) + 5)
    if has_prediction:
        im = create_image(len(events) + 2, title_len)
    else:
        im = create_image(len(events) + 1, title_len)

    title = f"公主连结{server_name[server]}活动"
    pcr_now = get_pcr_now(0)
    draw_title(im, 0, title, pcr_now.strftime("%Y/%m/%d"), "正在进行")

    if len(events) == 0:
        draw_item(im, 1, 1, "无数据", 0)
    i = 1
    for event in events:
        if event["start_days"] <= 0:
            draw_item(im, i, event["type"], event["title"], event["left_days"])
            i += 1
    if has_prediction:
        draw_title(im, i, right="即将开始")
        for event in events:
            if event["start_days"] > 0:
                i += 1
                draw_item(im, i, event["type"], event["title"], -event["start_days"])
    return im


if __name__ == "__main__":

    async def main():
        events = await get_events("cn", 0, 1)
        for event in events:
            print(event)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
