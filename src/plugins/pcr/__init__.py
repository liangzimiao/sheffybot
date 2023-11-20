from pathlib import Path
from nonebot import get_driver, logger, load_plugins
from nonebot.plugin import PluginMetadata

from .config import Config, pcr_config
from .services.pcr_data_service import PCRDataService

__plugin_meta__ = PluginMetadata(
    name="PCR",
    description="PCR相关插件",
    usage="",
    config=Config,
)

driver = get_driver()
pcr_date = PCRDataService()


@driver.on_startup
async def first_load():
    # 检查数据并补齐缺少的数据
    pcr_date.load_data()


logger.debug(pcr_config)
sub_plugins = load_plugins(str(Path(__file__).parent.joinpath("plugins").resolve()))
