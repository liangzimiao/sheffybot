from nonebot.plugin import PluginMetadata

from . import avatar_guess as avatar_guess

# from . import card_guess as card_guess
# from . import desc_guess as desc_guess
# from . import voice_guess as voice_guess
from .config import Config

__plugin_meta__ = PluginMetadata(
    name="pcr_guess",
    description="""
    [抽签|人品|运势]
    随机角色预测今日运势
    准确率高达114.514%！
    """,
    usage="[猜头像|猜卡面|猜角色|猜语音]",
    config=Config,
)
