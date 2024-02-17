from pathlib import Path

from nonebot import get_driver, load_plugins
from nonebot.plugin import PluginMetadata

from .config import Config
from .services.data_service import pcr_data

__plugin_meta__ = PluginMetadata(
    name="PCR",
    description="PCR相关插件",
    usage="",
    config=Config,
)
# 环奈头像1701待修复
# 设置UNKNOWN头像
# 配置ffmpeg，否则无法发送m4a格式的语音


driver = get_driver()


@driver.on_startup
async def first_load():
    # 检查数据并补齐缺少的数据
    await pcr_data.load_pcr_data()
    #print(type(pcr_data.CHARA_ROSTER.get("未知角色")))
    #print(pcr_data.CHARA_ROSTER.get("未知角色"))


sub_plugins = load_plugins(str(Path(__file__).parent.joinpath("plugins").resolve()))
