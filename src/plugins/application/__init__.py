from pathlib import Path

from nonebot import load_plugins
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="application",
    description="应用插件,包含商店插件",
    usage="",
    config=None,
)


sub_plugins = load_plugins(str(Path(__file__).parent.joinpath("plugins").resolve()))
