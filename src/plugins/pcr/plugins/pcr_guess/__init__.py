from nonebot.plugin import PluginMetadata

from . import avatar_guess as avatar_guess
from . import card_guess as card_guess
from . import desc_guess as desc_guess

# from . import voice_guess as voice_guess


__plugin_meta__ = PluginMetadata(
    name="pcr_guess",
    description="pcr相关的猜角色游戏",
    usage="[猜头像|猜卡面|猜角色|猜语音]",
    config=None,
)
