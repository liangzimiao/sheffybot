import requests

from io import BytesIO
from dataclasses import dataclass
from loguru import logger
from pathlib import Path
from PIL import Image
from typing import Optional, Literal


from ..config import pcr_config

pcr_data_path: Path = pcr_config.pcr_data_path
pcr_res_path: Path = pcr_config.pcr_resources_path


@dataclass
class Chara:
    """PCR角色"""

    id: str | int
    """角色id"""
    star: Literal[1, 3, 6, "1", "3", "6"] = 3
    """角色星级"""
    name: Optional[str] = "未知角色"
    """角色名字"""

    @property
    def icon_path(self) -> Path:
        """
        返回当前单元的图标图像文件的路径。
        """
        return Path(
            pcr_res_path / "priconne" / "icon" / f"icon_unit_{self.id}{self.star}1.png"
        )

    @property
    def card_path(self) -> Path:
        """
        返回当前实例的卡片图像文件的路径。
        """
        return Path(
            pcr_res_path / "priconne" / "card" / f"card_full_{self.id}{self.star}1.png"
        )

    @property
    def icon(self) -> BytesIO:
        """角色头像"""
        # 获取图片路径
        icon_path = self.icon_path
        # 检查图片是否已经下载
        if icon_path.exists():
            # 打开图片并返回BytesIO
            with open(icon_path, "rb") as f:
                return BytesIO(f.read())
        else:
            # 如果没有下载,则先下载再返回
            download_chara_img(c=self, type_="icon")
            # 重新打开图片并返回BytesIO
            return self.icon

    @property
    def card(self) -> BytesIO:
        """角色卡面"""
        # 获取图片路径
        card_path = self.card_path
        # 检查图片是否已经下载
        if card_path.exists():
            # 打开图片并返回BytesIO
            with open(card_path, "rb") as f:
                return BytesIO(f.read())
        else:
            # 如果没有下载,则先下载再返回
            download_chara_img(c=self, type_="card")
            # 重新打开图片并返回BytesIO
            return self.icon


def download_chara_img(c: Chara, type_: Literal["card", "icon"]):
    """
    根据指定的类型下载给定角色对象的角色图片。

    参数：
        c (Chara)：角色对象。
        type_ (str)：要下载的图片类型。可以是"card"或"icon"之一。

    """
    if type_ == "icon":
        url = f"https://redive.estertion.win/icon/unit/{c.id}{c.star}1.webp"
        save_path = c.icon_path
    elif type_ == "card":
        url = f"https://redive.estertion.win/card/full/{c.id}{c.star}1.webp"
        save_path = c.card_path

    if save_path.exists():
        logger.debug(f"Chara {type_} {save_path}已存在")
        return
    logger.debug(f"Downloading Chara {type_} from {url}")
    try:
        rsp = requests.get(url, stream=True, timeout=10)
        if 200 == rsp.status_code:
            img = Image.open(BytesIO(rsp.content))
            img.save(save_path)
            logger.info(f"Saved to {save_path}")
        else:
            logger.error(f"Failed to download {url}. HTTP {rsp.status_code}")
    except Exception as e:
        logger.error(f"Failed to download {url}. {type(e)}")
