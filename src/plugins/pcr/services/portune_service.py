import json
import random
import pytz
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from ..config import pcr_config


pcr_res_path: Path = pcr_config.pcr_resources_path
pcr_data_path: Path = pcr_config.pcr_data_path


class PortuneService:
    """PCR运势服务"""

    res_path: Path
    """PCR运势资源路径"""
    luck_type_cache = None
    luck_desc_cache = None

    def __init__(self) -> None:
        self.res_path = pcr_res_path / "portune"

    @property
    def luck_type(self) -> list:
        if PortuneService.luck_type_cache is None:
            print("PortuneService.luck_type无缓存")
            with open(self.res_path / "luck_type.json", "r", encoding="utf-8") as file:
                PortuneService.luck_type_cache = json.load(file)
        return PortuneService.luck_type_cache

    @property
    def luck_desc(self) -> list:
        if PortuneService.luck_desc_cache is None:
            print("PortuneService.luck_desc无缓存")
            with open(self.res_path / "luck_desc.json", "r", encoding="utf-8") as file:
                PortuneService.luck_desc_cache = json.load(file)
        return PortuneService.luck_desc_cache

    def drawing_pic(self) -> BytesIO:
        """
        生成运势图片

        Returns:
            BytesIO: 图片的BytesIO
        """
        fontPath = {
            "title": self.res_path / "font/Mamelon.otf",
            "text": self.res_path / "font/sakura.ttf",
        }

        charaid = str(random.randint(1, 66))
        filename = "frame_" + charaid + ".jpg"

        img = Image.open(self.res_path / "imgbase" / filename)
        # Draw title
        draw = ImageDraw.Draw(img)
        text, title = self.get_info(charaid)

        text = text["content"]
        font_size = 45
        color = "#F5F5F5"
        image_font_center = (140, 99)
        ttfront = ImageFont.truetype(str(fontPath["title"]), font_size)
        font_length = ttfront.getlength(title)

        draw.text(
            (
                image_font_center[0] - font_length / 2,
                image_font_center[1] - font_size / 2,
            ),
            title,
            fill=color,
            font=ttfront,
        )
        # Text rendering
        font_size = 25
        color = "#323232"
        image_font_center = [140, 297]
        ttfront = ImageFont.truetype(str(fontPath["text"]), font_size)
        result = self.decrement(text)
        if not result[0]:
            raise Exception("Unknown error in daily luck")
        textVertical = []
        for i in range(0, result[0]):
            font_height = len(result[i + 1]) * (font_size + 4)
            textVertical = self.vertical(result[i + 1])
            x = int(
                image_font_center[0]
                + (result[0] - 2) * font_size / 2
                + (result[0] - 1) * 4
                - i * (font_size + 4)
            )
            y = int(image_font_center[1] - font_height / 2)
            draw.text((x, y), textVertical, fill=color, font=ttfront)
        # 创建一个新的 BytesIO 对象
        bytes_io = BytesIO()
        # 将图像保存到 BytesIO 对象中
        img.save(bytes_io, format="JPEG")
        # 将光标移动到字节流的起始位置
        bytes_io.seek(0)
        return bytes_io

    def get_luck_type(self, desc) -> str:
        target_luck_type = desc["good-luck"]
        for i in self.luck_type:
            if i["good-luck"] == target_luck_type:
                return i["name"]
        raise Exception("luck type not found")

    def get_info(self, charaid):
        for i in self.luck_desc:
            if charaid in i["charaid"]:
                typewords = i["type"]
                desc = random.choice(typewords)
                return desc, self.get_luck_type(desc)
        raise Exception("luck description not found")

    def decrement(self, text) -> list:
        length = len(text)
        result = []
        cardinality = 9
        if length > 4 * cardinality:
            return [False]
        numberOfSlices = 1
        while length > cardinality:
            numberOfSlices += 1
            length -= cardinality
        result.append(numberOfSlices)
        # Optimize for two columns
        space = " "
        length = len(text)
        if numberOfSlices == 2:
            if length % 2 == 0:
                # even
                fillIn = space * int(9 - length / 2)
                return [
                    numberOfSlices,
                    text[: int(length / 2)] + fillIn,
                    fillIn + text[int(length / 2) :],
                ]
            else:
                # odd number
                fillIn = space * int(9 - (length + 1) / 2)
                return [
                    numberOfSlices,
                    text[: int((length + 1) / 2)] + fillIn,
                    fillIn + space + text[int((length + 1) / 2) :],
                ]
        for i in range(0, numberOfSlices):
            if i == numberOfSlices - 1 or numberOfSlices == 1:
                result.append(text[i * cardinality :])
            else:
                result.append(text[i * cardinality : (i + 1) * cardinality])
        return result

    def vertical(self, str):
        list = []
        for s in str:
            list.append(s)
        return "\n".join(list)


class DailyNumberLimiter:
    tz = pytz.timezone("Asia/Shanghai")

    def __init__(self, max_num):
        self.today = -1
        self.count = defaultdict(int)
        self.max = max_num

    def check(self, key) -> bool:
        now = datetime.now(self.tz)
        day = (now - timedelta(hours=0)).day
        if day != self.today:
            self.today = day
            self.count.clear()
        return bool(self.count[key] < self.max)

    def get_num(self, key):
        return self.count[key]

    def increase(self, key, num=1):
        self.count[key] += num

    def reset(self, key):
        self.count[key] = 0
