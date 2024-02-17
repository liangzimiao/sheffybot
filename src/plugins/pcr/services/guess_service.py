import random
import sqlite3
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

from PIL import Image

from ..logger import PCRLogger as Logger
from ..models import GuessGame
from .data_service import chara_data, pcr_data

logger = Logger("PCR_GUESS")


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
                "CREATE TABLE IF NOT EXISTS win_record "
                "(gid TEXT NOT NULL, uid TEXT NOT NULL, count INT NOT NULL, PRIMARY KEY(gid, uid))"
            )

    def get_win_count(self, gid: str, uid: str) -> int:
        """
        获取胜利次数。
        """
        with self.connect() as conn:
            r = conn.execute(
                "SELECT count FROM win_record WHERE gid=? AND uid=?", (gid, uid)
            ).fetchone()
            return r[0] if r else 0

    def record_winning(self, gid: str, uid: str) -> int:
        """
        记录胜利。
        """
        n = self.get_win_count(gid, uid)
        n += 1
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO win_record (gid, uid, count) VALUES (?, ?, ?)",
                (gid, uid, n),
            )
        return n

    def get_ranking(self, gid: str) -> list[tuple[str, int]]:
        """
        获取排行榜。
        """
        with self.connect() as conn:
            r = conn.execute(
                "SELECT uid, count FROM win_record WHERE gid=? ORDER BY count DESC LIMIT 10",
                (gid,),
            ).fetchall()
            return r


class GuessService:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.playing = {}

    def is_playing(self, gid: str) -> bool:
        """
        判断指定gid的游戏是否正在进行。
        """
        return gid in self.playing

    def end_game(self, gid: str) -> None:
        """
        结束指定gid的游戏。
        """
        del self.playing[gid]

    def get_game(self, gid: str) -> Optional[GuessGame]:
        """
        获取指定gid的游戏。
        """
        return self.playing[gid] if gid in self.playing else None

    def get_ranking(self, gid: str) -> list[tuple[str, int]]:
        """
        获取给定gid的游戏排名。
        """
        return self.db.get_ranking(gid)

    def record(self, gid: str, uid: str) -> int:
        """
        记录当前游戏下用户的胜利，并返回胜利次数。
        gid: 游戏的ID。
        uid: 用户的ID。
        """
        return self.db.record_winning(gid, uid)

    async def start_avatar_game(
        self, gid: str, blacklist: list[str], patch_size=32
    ) -> GuessGame:
        """
        开始一个AvatarGuessGame游戏。

        参数:
            gid (str): 游戏的ID。
            patch_size (int, 可选): 游戏中补丁的大小。默认为32。

        返回:
            AvatarGuessGame: 猜头像游戏对象。
        """
        # 随机选择一个角色作为答案
        ids = list(pcr_data.CHARA_NAME.keys())
        id_ = random.choice(ids)
        while chara_data.is_npc(id_) or id_ in blacklist:
            id_ = random.choice(ids)
        c = chara_data.get_chara_from_id(id_)
        c.icon = await chara_data.get_chara_icon(id_, random.choice((1, 3, 6)))
        answer = c
        # 生成题目图片
        img = Image.open(c.icon)
        w, h = img.size
        l = random.randint(0, w - patch_size)  # noqa: E741
        u = random.randint(0, h - patch_size)
        img = img.crop((l, u, l + patch_size, u + patch_size))
        img_bytes = BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)
        question = img_bytes
        # 创建游戏
        game = GuessGame(gid=gid, winner=None, answer=answer, question=question)
        self.playing[gid] = game
        return game

    async def start_card_game(
        self, gid: str, blacklist: list, pic_side_length: int = 32
    ) -> GuessGame:
        """
        开始一个CardGuessGame游戏。

        参数:
            gid (str): 游戏的ID。

        返回:
            CardGuessGame: 猜卡面游戏对象。
        """
        # 随机选择一个角色作为答案
        ids = list(pcr_data.CHARA_NAME.keys())
        id_ = random.choice(ids)
        while chara_data.is_npc(id_) or id_ in blacklist:
            id_ = random.choice(ids)
        c = chara_data.get_chara_from_id(id_)
        c.card = await chara_data.get_chara_card(id_, random.choice((3, 6)))
        answer = c
        # 生成题目图片
        img = Image.open(c.card)
        w, h = img.size
        l = random.randint(0, w - pic_side_length)  # noqa: E741
        u = random.randint(0, h - pic_side_length)
        img = img.crop((l, u, l + pic_side_length, u + pic_side_length))
        img_bytes = BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)
        q_image = img_bytes
        # 创建游戏
        game = GuessGame(gid=gid, winner=None, answer=answer, question=q_image)
        self.playing[gid] = game
        return game

    async def start_desc_game(self, gid: str) -> GuessGame:
        """
        开始一个DescGuessGame游戏。

        参数:
            gid (str): 游戏的ID。

        返回:
            DescGuessGame: 猜角色游戏对象。
        """
        # 随机选择一个角色作为答案
        id_ = random.choice(list(pcr_data.CHARA_PROFILE.keys()))
        c = chara_data.get_chara_from_id(id_)
        c.icon = await chara_data.get_chara_icon(id_)
        # 生成题目档案
        profile = pcr_data.CHARA_PROFILE[id_].copy()
        profile.pop("名字", None)
        # 创建游戏
        game = GuessGame(gid=gid, winner=None, answer=c, question=profile)
        self.playing[gid] = game
        return game

    async def start_voice_game(self, gid) -> Any:
        """
        开始一个VoiceGuessGame游戏。

        参数:
            gid (str): 游戏的ID。

        返回:
            VoiceGuessGame: 猜语音游戏对象。
        """
        # 随机选择一个角色作为答案
        ...

    @staticmethod
    def check_answer(
        user_answer: str,
        game: GuessGame,
    ) -> bool:
        """
        判断给定的答案是否正确，根据角色数据进行判断。

        参数:
            answer (str): 要判断的答案。
            gid: gid 参数。

        返回:
            bool: 如果答案正确则返回 True，否则返回 False。
        """
        # 获取用户答案的角色
        user_chara = chara_data.get_chara_from_name(chara_data.match(user_answer)[0])
        return user_chara == game.answer

    @property
    def db(self) -> Dao:
        """
        数据库对象。
        """
        return Dao(self.db_path)
