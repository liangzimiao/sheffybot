import imghdr
import random
import sqlite3
from io import BytesIO
from pathlib import Path
from typing import Literal, Optional

from PIL import Image

from ..models import Chara
from ..models.guess_model import (
    AvatarGuessGame,
    CardGuessGame,
    CharaGuessGame,
    GuessGame,
    VoiceGuessGame,
)
from .internal.data_service import chara_data, pcr_data


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
                "(gid INT NOT NULL, uid INT NOT NULL, count INT NOT NULL, PRIMARY KEY(gid, uid))"
            )

    def get_win_count(self, gid, uid):
        with self.connect() as conn:
            r = conn.execute(
                "SELECT count FROM win_record WHERE gid=? AND uid=?", (gid, uid)
            ).fetchone()
            return r[0] if r else 0

    def record_winning(self, gid, uid):
        n = self.get_win_count(gid, uid)
        n += 1
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO win_record (gid, uid, count) VALUES (?, ?, ?)",
                (gid, uid, n),
            )
        return n

    def get_ranking(self, gid):
        with self.connect() as conn:
            r = conn.execute(
                "SELECT uid, count FROM win_record WHERE gid=? ORDER BY count DESC LIMIT 10",
                (gid,),
            ).fetchall()
            return r


class GuessService:
    @property
    def db(self):
        return Dao(self.db_path)

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.playing = {}

    def is_playing(self, gid):
        return gid in self.playing

    async def start_avatar_game(self, gid, patch_size=32):
        game = AvatarGuessGame(gid)
        self.playing[gid] = game
        return await avatar_guess(game, patch_size)

    def end_game(self, gid):
        del self.playing[gid]

    def get_game(self, gid) -> Optional[GuessGame]:
        return self.playing[gid] if gid in self.playing else None

    def get_ranking(self, gid):
        """
        获取给定gid的排名。

        参数：
            gid (int): 组的id。

        返回：
            int: 组的排名。
        """
        return self.db.get_ranking(gid)

    def record(self, gid, uid):
        """
        记录游戏和用户的胜利。
        gid: 游戏的ID。
        uid: 用户的ID。
        """
        return self.db.record_winning(gid, uid)

    @staticmethod
    def match_answer(answer: str) -> Chara:
        """
        给定一个答案，返回角色的名称。
        """
        answer_c = chara_data.from_name(chara_data.match(answer)[0])
        return answer_c


async def avatar_guess(game: AvatarGuessGame, patch_size=32) -> AvatarGuessGame:
    """
    给定AvatarGuessGame对象的题目图片与答案角色。

    参数:
        game (AvatarGuessGame): 要猜测头像的AvatarGuessGame对象。
        patch_size (int, 可选): 从头像图像中裁剪的补丁大小。默认为32。

    返回:
        AvatarGuessGame: 更新后的AvatarGuessGame对象，包含猜测的头像和裁剪后的图像。
    """
    ids = list(pcr_data.CHARA_NAME.keys())
    id_ = random.choice(ids)
    while chara_data.is_npc(id_):
        id_ = random.choice(ids)
    c = chara_data.from_id(id_)
    c.icon = await chara_data.get_chara_icon(id_, random.choice((3, 6)))
    img = Image.open(c.icon)
    w, h = img.size
    l = random.randint(0, w - patch_size)  # noqa: E741
    u = random.randint(0, h - patch_size)
    cropped = img.crop((l, u, l + patch_size, u + patch_size))
    game.image = BytesIO()
    cropped.save(game.image, format="PNG")
    game.image.seek(0)
    game.answer = c
    return game
