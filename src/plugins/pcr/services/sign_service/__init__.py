import json
import random
import textwrap
import time
from io import BytesIO
from pathlib import Path
from typing import Union

import httpx
from nonebot.adapters import Bot, Event
from nonebot_plugin_userinfo import get_user_info
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ...config import pcr_config
from ...logger import PCRLogger
from ...models import CollectionResult
from .base import CardRecordDAO

pcr_res_path: Path = pcr_config.pcr_resources_path
pcr_data_path: Path = pcr_config.pcr_data_path


login_presents = [
    "扫荡券×5",
    "卢币×1000",
    "普通EXP药水×5",
    "宝石×50",
    "玛那×3000",
    "扫荡券×10",
    "卢币×1500",
    "普通EXP药水×15",
    "宝石×80",
    "白金转蛋券×1",
    "扫荡券×15",
    "卢币×2000",
    "上级精炼石×3",
    "宝石×100",
    "白金转蛋券×1",
]

todo_list = [
    "找伊绪老师上课",
    "给宫子买布丁",
    "和真琴寻找伤害优衣的人",
    "找镜哥探讨女装",
    "跟吉塔一起登上骑空艇",
    "和霞一起调查伤害优衣的人",
    "和佩可小姐一起吃午饭",
    "找小小甜心玩过家家",
    "帮碧寻找新朋友",
    "去真步真步王国",
    "找镜华补习数学",
    "陪胡桃排练话剧",
    "和初音一起午睡",
    "成为露娜的朋友",
    "帮铃莓打扫咲恋育幼院",
    "和静流小姐一起做巧克力",
    "去伊丽莎白农场给栞小姐送书",
    "观看慈乐之音的演出",
    "解救挂树的队友",
    "来一发十连",
    "井一发当期的限定池",
    "给妈妈买一束康乃馨",
    "购买黄金保值",
    "竞技场背刺",
    "给别的女人打钱",
    "氪一单",
    "努力工作，尽早报答妈妈的养育之恩",
    "成为魔法少女",
    "搓一把日麻",
]


logger = PCRLogger("PCR_SIGN")


class SignService:
    """签到服务"""

    sign_res_path: Path = pcr_res_path / "sign"
    """签到资源路径"""
    stamp_path: Path = sign_res_path / "stamp"
    """卡片资源路径"""
    font_path: Path = sign_res_path / "STHUPO.TTF"
    """字体资源路径"""
    db_path: Path = pcr_data_path / "sign" / "pcr_stamp.db"
    """数据库路径"""
    goodwill_path: Path = pcr_data_path / "sign" / "goodwill.json"
    """好感数据路径"""
    col_num = pcr_config.pcr_sign_col_num
    """查看仓库时每行显示的卡片个数"""
    is_preload: bool = pcr_config.pcr_sign_is_preload
    """是否启动时直接将所有图片加载到内存中以提高查看仓库的速度(增加约几M内存消耗)"""
    bg_mode: int = pcr_config.pcr_sign_bg_mode
    """背景模式"""
    card_file_names_all: list = []
    """卡片列表"""
    image_list = stamp_path.rglob("*.*")
    """图片列表"""

    def __init__(self):
        if not self.goodwill_path.exists():
            # 不存在就创建文件
            self.goodwill_path.parent.mkdir(parents=True, exist_ok=True)
            # 在goodwill_path文件中存储空字典
            with open(self.goodwill_path, "w") as file:
                json.dump({}, file)

        self.image_cache = {}
        for image in self.image_list:
            # 图像缓存
            if self.is_preload:
                image_path = image
                img = Image.open(image_path)
                c_id = (str(image)[:-4]).split("\\")[-1]
                self.image_cache[c_id] = (
                    img.convert("RGBA") if img.mode != "RGBA" else img
                )
            self.card_file_names_all.append(image)
            self.len_card = len(self.card_file_names_all)

    async def get_sign_card(
        self, gid: str, uid: str, bot: Bot, event: Event
    ) -> Union[str, BytesIO]:
        # 日期
        time_tuple = time.localtime(time.time())
        last_time = f"{time_tuple[0]}年{time_tuple[1]}月{time_tuple[2]}日"

        with open(self.goodwill_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            try:
                if data[str(gid)][str(uid)][1] == last_time:
                    msg = "今天已经签到过啦，明天再来叭~"
                    return msg
            except KeyError:
                pass
        # 发癫待办
        todo = random.choice(todo_list)
        # 增加好感
        goodwill = random.randint(1, 10)
        # 随机图案
        stamp = random.choice(self.card_file_names_all)
        # 生成卡片
        result = await self.draw_card(
            path=stamp,
            gid=gid,
            uid=uid,
            todo=todo,
            last_time=last_time,
            goodwill=goodwill,
            bot=bot,
            event=event,
        )
        # 收集册
        card_id = (str(stamp)[:-4]).split("\\")[-1]
        self.db.add_card_num(gid, uid, int(card_id))
        return result

    async def get_collection(
        self, gid: str, uid: str, bot: Bot, event: Event
    ) -> CollectionResult:
        result: CollectionResult = {
            "collection_img": BytesIO(),
            "ranking_desc": "",
            "rank_text": "",
            "cards_num": "0/0",
        }

        ranking = self.db.get_group_ranking(gid, uid)

        with open(self.goodwill_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data = data[f"{gid}"]
        new_dictionary = {}
        rank_text = ""
        rank_num = 1
        for user_data in data:
            new_dictionary[f"{user_data}"] = int(f"{data[f'{user_data}'][0]}")
        for i in sorted(new_dictionary.items(), key=lambda x: x[1], reverse=True):
            q, g = i
            try:
                rank_user = await get_user_info(bot=bot, event=event, user_id=q)
                rank_user = rank_user.user_name if rank_user else q
                rank_text += f"{rank_num}. {rank_user} 好感:{g}\n"
                rank_num += 1
            except Exception:
                pass
            if rank_num > 10:
                break
        rank_num = 1
        for i in sorted(new_dictionary.items(), key=lambda x: x[1], reverse=True):
            q, g = i
            try:
                if q != str(uid):
                    rank_num += 1
                else:
                    break
            except Exception:
                pass

        result["collection_img"] = await self.draw_collection(gid, uid)
        result["rank_text"] = f"好感排行: \n{rank_text}......\n当前排名: {rank_num}"
        # result["rank_text"] = f"第{rank_num}位"
        result["ranking_desc"] = f"第{ranking}位" if ranking != -1 else "未上榜"
        result["cards_num"] = (
            f"{self.normalize_digit_format(len(self.db.get_cards_num(gid, uid)))}/{self.normalize_digit_format(len(self.card_file_names_all))}"
        )
        return result

    async def draw_card(
        self,
        path: Path,
        gid: str,
        uid: str,
        todo: str,
        last_time: str,
        goodwill: int,
        bot: Bot,
        event: Event,
    ) -> BytesIO:
        """绘制卡片"""
        # 背景
        if self.bg_mode == 1:
            bg_bytes = await self.get_background()
            # 调整大小
            sign_bg: Image.Image = Image.open(bg_bytes).convert("RGBA")
            weight, height = sign_bg.size
            if (weight / height) >= (928 / 1133):
                print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                sign_bg = sign_bg.resize((int(weight * (1133 / height)), 1133))
                print(sign_bg.size)
                print(
                    (
                        int((int(weight * (1133 / height)) - 928) / 2),
                        0,
                        int((int(weight * (1133 / height)) - 928) / 2 + 928),
                        1133,
                    )
                )
                sign_bg = sign_bg.crop(
                    (
                        int((int(weight * (1133 / height)) - 928) / 2),
                        0,
                        int((int(weight * (1133 / height)) - 928) / 2 + 928),
                        1133,
                    )
                )
            elif (weight / height) < (928 / 1133):
                print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
                sign_bg = sign_bg.resize((928, int(height * (928 / weight))))
                print(sign_bg.size)
                print(
                    (
                        0,
                        int((int(height * (928 / weight)) - 1133) / 2),
                        928,
                        int((int(height * (928 / weight)) - 1133) / 2 + 1133),
                    )
                )
                sign_bg = sign_bg.crop(
                    (
                        0,
                        int((int(height * (928 / weight)) - 1133) / 2),
                        928,
                        int((int(height * (928 / weight)) - 1133) / 2 + 1133),
                    )
                )
            sign_bg = sign_bg.resize((928, 1133))
            # 模糊背景
            sign_bg = sign_bg.filter(ImageFilter.GaussianBlur(8))
            # 背景阴影
            shadow = Image.open(self.sign_res_path / "image" / "shadow.png").convert(
                "RGBA"
            )
        else:
            sign_bg_list = []
            for sign in (self.sign_res_path / "image" / "sign_bg").rglob("*.*"):
                sign_bg_list.append(sign)
            sign_bg = random.choice(sign_bg_list)
            sign_bg = Image.open(sign_bg)
        draw = ImageDraw.Draw(sign_bg)
        # 调整样式
        stamp_img = Image.open(path)
        stamp_img = stamp_img.resize((502, 502))
        w, h = stamp_img.size
        mask = Image.new("RGBA", (w, h), color=(0, 0, 0, 0))  # type: ignore
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, w, h), fill=(0, 0, 0, 255))
        sign_bg.paste(stamp_img, (208, 43, 208 + w, 43 + h), mask)
        # 更新好感
        data = await self.update_goodwill(
            gid=gid, uid=uid, last_time=last_time, goodwill=goodwill
        )
        # 计算排行
        data = data[f"{gid}"]
        new_dictionary = {}
        rank_num = 1
        for user_data in data:
            new_dictionary[f"{user_data}"] = int(f"{data[f'{user_data}'][0]}")
        for i in sorted(new_dictionary.items(), key=lambda x: x[1], reverse=True):
            q, g = i
            try:
                if q != str(uid):
                    rank_num += 1
                else:
                    rank_user = await get_user_info(bot=bot, event=event, user_id=q)
                    rank_user = rank_user.user_name if rank_user else "主人"
                    break
            except Exception:
                pass
        response_text = await self.get_yi_yan()
        # 绘制文字
        with open(self.font_path, "rb") as draw_font:
            bytes_font = BytesIO(draw_font.read())
            text_font = ImageFont.truetype(font=bytes_font, size=45)
        draw.text(xy=(98, 580), text=f"欢迎回来，{rank_user}~!", font=text_font)
        draw.text(
            xy=(98, 633), text=f"好感 + {goodwill} !  当前好感: {g}", font=text_font
        )
        draw.text(
            xy=(98, 686),
            text=f"当前群排名: 第 {rank_num} 位",
            fill=(200, 255, 255),
            font=text_font,
        )
        draw.text(
            xy=(98, 739),
            text='发送"收集册"查看收集进度',
            fill=(255, 180, 220),
            font=text_font,
        )
        para = textwrap.wrap(f"主人今天要{todo}吗?", width=16)
        for i, line in enumerate(para):
            draw.text((98, 53 * i + 792), line, "white", text_font)
        para = textwrap.wrap(f"今日一言: {response_text}", width=16)
        for i, line in enumerate(para):
            draw.text((98, 53 * i + 898), line, "white", text_font)

        output = BytesIO()
        if self.bg_mode == 1:
            # 合并图片
            final = Image.new("RGBA", (928, 1133))
            final = Image.alpha_composite(final, sign_bg)
            final = Image.alpha_composite(final, shadow)
            final.save(output, format="png")
        else:
            sign_bg.save(output, format="png")
        return output

    async def draw_collection(self, gid: str, uid: str) -> BytesIO:
        # 收集册
        row_num = (
            self.len_card // self.col_num
            if self.len_card % self.col_num != 0
            else self.len_card // self.col_num - 1
        )
        base = Image.open(self.sign_res_path / "image" / "frame.png")
        base = base.resize(
            (
                40 + self.col_num * 80 + (self.col_num - 1) * 10,
                150 + row_num * 80 + (row_num - 1) * 10,
            ),
            Image.Resampling.LANCZOS,
        )
        cards_num = self.db.get_cards_num(gid, uid)
        row_index_offset = 0
        row_offset = 0
        cards_list = self.card_file_names_all
        for index, path in enumerate(cards_list):
            row_index = index // self.col_num + row_index_offset
            col_index = index % self.col_num
            c_id = (str(path)[:-4]).split("\\")[-1]
            f = (
                self.get_pic(c_id, False)
                if int(c_id) in cards_num
                else self.get_pic(c_id, True)
            )
            base.paste(
                f,
                (
                    30 + col_index * 80 + (col_index - 1) * 10,
                    row_offset + 40 + row_index * 80 + (row_index - 1) * 10,
                ),
            )
        row_offset += 30
        bytes_io = BytesIO()
        base.save(bytes_io, format="JPEG")
        bytes_io.seek(0)
        return bytes_io

    async def update_goodwill(
        self, gid: str, uid: str, last_time: str, goodwill: int
    ) -> dict:
        """更新好感度"""
        # 读写数据
        with open(self.goodwill_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            try:
                user_goodwill = data[str(gid)][str(uid)][0]
            except KeyError:
                user_goodwill = 0
        with open(self.goodwill_path, "w", encoding="utf-8") as f:
            if str(gid) in data:
                data[str(gid)][str(uid)] = [user_goodwill + goodwill, last_time]
            else:
                data[str(gid)] = {str(uid): [user_goodwill + goodwill, last_time]}
            json.dump(data, f, indent=4, ensure_ascii=False)
        return data

    def get_pic(self, c_id: str, grey: bool = False) -> Image.Image:
        if self.is_preload:
            sign_image = self.image_cache[c_id]
        else:
            pic_path = self.stamp_path / f"{c_id}.png"
            sign_image = Image.open(pic_path)
        sign_image = sign_image.resize((80, 80), Image.Resampling.LANCZOS)
        if grey:
            sign_image = sign_image.convert("L")
        return sign_image

    @staticmethod
    async def get_background() -> BytesIO:
        # 下载背景
        res = httpx.get(
            url="https://dev.iw233.cn/api.php?sort=mp&type=json",
            headers={"Referer": "http://www.weibo.com/"},
        )
        res = res.text
        pic_url = json.loads(res)["pic"][0]
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{pic_url}",
                headers={
                    "Referer": "http://www.weibo.com/",
                },
                timeout=10,
            )
            return BytesIO(response.content)

    @staticmethod
    async def get_yi_yan() -> str:
        # 一言
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("https://v1.hitokoto.cn/?c=f&encode=text")
                status_code = response.status_code
                if status_code == 200:
                    response_text = response.text
                else:
                    response_text = f"请求错误: {status_code}"
                return response_text
        except Exception as error:
            logger.warning(f"{error}")
            return f"{error}"

    @staticmethod
    def normalize_digit_format(n):
        return f"0{n}" if n < 10 else f"{n}"

    @property
    def db(self):
        return CardRecordDAO(self.db_path)


sign_service = SignService()
