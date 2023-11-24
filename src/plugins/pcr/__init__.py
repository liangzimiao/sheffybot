from pathlib import Path

from nonebot import get_driver, load_plugins
from nonebot.plugin import PluginMetadata

from .config import Config
from .services.internal.data_service import pcr_data

__plugin_meta__ = PluginMetadata(
    name="PCR",
    description="PCR相关插件",
    usage="",
    config=Config,
)

driver = get_driver()


@driver.on_startup
async def first_load():
    # 检查数据并补齐缺少的数据
    await pcr_data.load_data()
    #print(type(pcr_data.CHARA_NAME_ID["未知角色"]))


# logger.debug(pcr_config)
sub_plugins = load_plugins(str(Path(__file__).parent.joinpath("plugins").resolve()))
