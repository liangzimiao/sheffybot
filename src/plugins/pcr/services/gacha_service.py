import random
import sqlite3
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image

from ..config import pcr_config
from ..logger import PCRLogger
from ..models import Chara, GachaTenjouResult
from .data_service import chara_data
from .data_service import pcr_data as pcr

pcr_res_path: Path = pcr_config.pcr_resources_path
pcr_data_path: Path = pcr_config.pcr_data_path

db_path = pcr_config.pcr_data_path / "gacha_game" / "pcr_gacha_gid.db"

logger = PCRLogger("PCR_GACHA")


class Dao:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.touch()
        self._create_table()

    def connect(self):
        return sqlite3.connect(self.db_path)

    def _create_table(self):
        with self.connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS gid_pool "
                "(gid TEXT NOT NULL PRIMARY KEY, pool TEXT )"
            )

    def get_pool(self, gid: str) -> Optional[str]:
        """
        获取卡池
        """
        with self.connect() as conn:
            r = conn.execute(
                "SELECT pool FROM gid_pool WHERE gid=? ", (gid,)
            ).fetchone()
            return r[0] if r else None

    def set_pool(self, gid: str, pool_name: str):
        """
        设置卡池
        """
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO gid_pool (gid, pool) VALUES (?, ?)",
                (gid, pool_name),
            )


class Gacha:
    def __init__(self, pool_name: str = "BL"):
        try:
            pool = pcr.LOCAL_POOL[pool_name]
        except KeyError:
            pool = pcr.LOCAL_POOL["BL"]
        self.pool_name = pool_name
        self.up_prob = pool["up_prob"]
        self.s3_prob = pool["s3_prob"]
        self.s2_prob = pool["s2_prob"]
        self.s1_prob = 1000 - self.s2_prob - self.s3_prob
        self.up = pool["up"]
        self.star3 = pool["star3"]
        self.star2 = pool["star2"]
        self.star1 = pool["star1"]

    async def gacha_one(
        self,
        up_prob: int,
        s3_prob: int,
        s2_prob: int,
        icon: bool = True,
    ) -> Tuple[Chara, int]:
        """
        sx_prob: x星概率，要求和为1000
        up_prob: UP角色概率（从3星划出）
        up_chara: UP角色名列表

        return: (单抽结果:Chara, 秘石数:int)
        ---------------------------
        |up|      |  20  |   78   |
        |   ***   |  **  |    *   |
        ---------------------------
        """
        rn = random.SystemRandom()
        pick = rn.randint(1, 1000)
        if pick <= up_prob:
            return await chara_data.get_chara(
                name=rn.choice(self.up), star=3, need_icon=True
            ), 100
        elif pick <= s3_prob:
            return await chara_data.get_chara(
                name=rn.choice(self.star3), star=3, need_icon=True
            ), 50
        elif pick <= s2_prob + s3_prob:
            return await chara_data.get_chara(
                name=rn.choice(self.star2), star=2, need_icon=icon
            ), 10
        else:
            return await chara_data.get_chara(
                name=rn.choice(self.star1), star=1, need_icon=icon
            ), 1

    async def gacha_ten(self) -> Tuple[List[Chara], int]:
        result = []
        hiishi = 0
        up = self.up_prob
        s3 = self.s3_prob
        s2 = self.s2_prob
        for _ in range(9):  # 前9连
            c, y = await self.gacha_one(up, s3, s2)
            result.append(c)
            hiishi += y if y != 100 else 50
        c, y = await self.gacha_one(up, s3, 1000 - s3)  # 保底第10抽
        result.append(c)
        hiishi += y if y != 100 else 50

        return result, hiishi

    async def gacha_tenjou(self) -> GachaTenjouResult:
        result: GachaTenjouResult = {
            "s3": [],
            "s2": [],
            "s1": [],
            "first_up_pos": 999,
            "up_num": 0,
            "hiishi": 0,
        }
        first_up_pos = 999
        up_num = 0
        hiishi = 0
        num: int = 20
        for i in range(num):
            for j in range(1, 10):  # 前9连
                c, y = await self.gacha_one(
                    self.up_prob, self.s3_prob, self.s2_prob, icon=False
                )
                hiishi += y
                if 100 == y:
                    result["s3"].append(c)
                    first_up_pos = min(i * 10 + j, first_up_pos)
                    up_num += 1
                elif 50 == y:
                    result["s3"].append(c)
                elif 10 == y:
                    result["s2"].append(c)
                elif 1 == y:
                    result["s1"].append(c)
            c, y = await self.gacha_one(
                self.up_prob, self.s3_prob, 1000 - self.s3_prob, icon=False
            )  # 保底第10抽
            hiishi += y
            if 100 == y:
                result["s3"].append(c)
                first_up_pos = min((i + 1) * 10, first_up_pos)
                up_num += 1
            elif 50 == y:
                result["s3"].append(c)
            elif 10 == y:
                result["s2"].append(c)
            elif 1 == y:
                result["s1"].append(c)
        result["first_up_pos"] = first_up_pos
        result["up_num"] = up_num
        result["hiishi"] = hiishi
        return result


class GachaService:
    def __init__(self):
        self.local_pool = pcr.LOCAL_POOL.copy()

    async def draw_gacha(
        self,
        c_list: List[Chara],
    ) -> BytesIO:
        """
        绘制抽卡结果
        """
        pics = []
        step = 5
        length = len(c_list)
        for i in range(0, length, step):
            j = min(length, i + step)
            pics.append(gen_team_pic(c_list[i:j], star_slot_verbose=False))
        res = concat_pic(pics)
        bytes = BytesIO()
        res.save(bytes, format="png")
        bytes.seek(0)
        return bytes

    async def get_gacha(self, gid: str) -> Gacha:
        """
        获取群组对应的卡池
        """
        pool_name = self.db.get_pool(gid=gid)
        if pool_name:
            return Gacha(pool_name=pool_name)
        return Gacha()

    async def set_gacha(self, gid: str, pool_name: str) -> None:
        """
        修改群组对应的卡池
        """
        self.db.set_pool(gid=gid, pool_name=pool_name)

    def match_gacha(self, index: int):
        return list(pcr.LOCAL_POOL.keys())

        # return ""

    def get_all_gacha(self) -> List[str]:
        """
        Return a list of all gacha pools.
        """
        return list(pcr.LOCAL_POOL.keys())

    @property
    def db(self) -> Dao:
        """
        数据库对象。
        """
        return Dao(db_path)


def concat_pic(pics: List[Image.Image], border=5):
    num = len(pics)
    w, h = pics[0].size
    des = Image.new("RGBA", (w, num * h + (num - 1) * border), (255, 255, 255, 255))  # type: ignore
    for i, pic in enumerate(pics):
        des.paste(pic, (0, i * (h + border)), pic)
    return des


def gen_team_pic(team, size=64, star_slot_verbose=True) -> Image.Image:
    num = len(team)
    des = Image.new("RGBA", (num * size, size), color=(255, 255, 255, 255))  # type: ignore
    for i, chara in enumerate(team):
        src = render_icon(chara, size, star_slot_verbose)
        des.paste(src, (i * size, 0), src)
    return des


def render_icon(c: Chara, size: int, star_slot_verbose: bool = True) -> Image.Image:
    """
    Renders an icon for the given character with the specified size.

    Args:
        c (Chara): The character for which the icon is rendered.
        size (int): The size of the rendered icon.
        star_slot_verbose (bool, optional): Whether to render star slots in verbose mode. Defaults to True.

    Returns:
        Image.Image: The rendered icon image.
    """
    pic = (
        Image.open(c.icon)
        .convert("RGBA")
        .resize((size, size), Image.Resampling.LANCZOS)
    )
    l_ = size // 6
    star_lap = round(l_ * 0.15)
    margin_x = (size - 6 * l_) // 2
    margin_y = round(size * 0.05)
    if c.star:
        for i in range(5 if star_slot_verbose else min(c.star, 5)):
            a = i * (l_ - star_lap) + margin_x
            b = size - l_ - margin_y
            s = pcr.gadget_star if c.star > i else pcr.gadget_star_dis
            s = s.resize((l_, l_), Image.Resampling.LANCZOS)
            pic.paste(s, (a, b, a + l_, b + l_), s)
        if 6 == c.star:
            a = 5 * (l_ - star_lap) + margin_x
            b = size - l_ - margin_y
            s = pcr.gadget_star_pink
            s = s.resize((l_, l_), Image.Resampling.LANCZOS)
            pic.paste(s, (a, b, a + l_, b + l_), s)
    if c.equip:
        l_ = round(l_ * 1.5)
        a = margin_x
        b = margin_x
        s = pcr.gadget_equip.resize((l_, l_), Image.Resampling.LANCZOS)
        pic.paste(s, (a, b, a + l_, b + l_), s)
    return pic
