import asyncio
import hashlib
from io import BytesIO
from typing import Optional
import json
from ..models import Chara
from .data_service import chara_data as chara
from .data_service import pcr_data as pcr


class WikiService:
    """Wiki服务"""

    def __init__(self) -> None:
        pass

    async def get_chara(self, name: str) -> Optional[Chara]:
        """获取指定角色对象"""
        c = await chara.get_chara(name=name, need_icon=True)
        if c.id == chara.UNKNOWN:
            return None
        return c

    async def get_chara_alias(self, c: Chara) -> str:
        """获取指定角色的别名"""
        return "， ".join(pcr.CHARA_NAME[c.id])

    async def get_chara_icon(self, name: str) -> list:
        """获取指定角色的头像"""
        icon_list = []
        id_ = chara.name2id(name=name)
        res = await asyncio.gather(
            chara.get_chara_icon(id=id_, star=1),
            chara.get_chara_icon(id=id_, star=3),
            chara.get_chara_icon(id=id_, star=6),
        )
        icon_list = self.dedupe_images(list(res))
        return icon_list

    async def get_chara_card(self, name: str) -> list:
        """获取指定角色的卡面"""
        card_list = []
        id_ = chara.name2id(name=name)
        res = await asyncio.gather(
            chara.get_chara_card(id=id_, star=3),
            chara.get_chara_card(id=id_, star=6),
        )
        card_list = self.dedupe_images(list(res))
        return card_list

    async def get_chara_profile(self, id_: str) -> str:
        """获取指定角色的档案"""
        return (
            json.dumps(
                pcr.CHARA_PROFILE[id_], ensure_ascii=False, separators=(",", ": ")
            )
            .replace('"', "")
            .replace("{", "")
            .replace("}", "")
            .replace(",", "\n")
        )

    def dedupe_images(self, images: list[BytesIO]) -> list[BytesIO]:
        """
        去重图片列表
        """
        # 创建一个空的集合
        seen = set()
        # 创建一个新的列表，用于存储不重复的图片
        deduped_images = []
        # 遍历原始列表
        for image in images:
            # 使用哈希函数计算图片的哈希值
            image_hash = hashlib.md5(image.getbuffer()).hexdigest()
            # 如果哈希值不在集合中，则将图片添加到集合中并将其添加到新列表中
            if image_hash not in seen:
                seen.add(image_hash)
                deduped_images.append(image)
        return deduped_images

    def get_image_hash(self, image_bytes):
        hash_object = hashlib.md5()
        hash_object.update(image_bytes.getbuffer())
        return hash_object.hexdigest()
