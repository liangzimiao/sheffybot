from nonebot.plugin import PluginMetadata

from . import avatar_guess as avatar_guess
from . import card_guess as card_guess
from . import desc_guess as desc_guess

# from . import voice_guess as voice_guess


__plugin_meta__ = PluginMetadata(
    name="pcr_guess",
    description="""
    pcr相关的猜角色游戏
    """,
    usage="[猜头像|猜卡面|猜角色|猜语音]",
    config=None,
)


# from nonebot import MatcherGroup
# from nonebot.adapters import Event

# def for_pcr(event: Event) -> bool:
#    message = event.get_plaintext()
#    if "pcr" or "PCR" in message:
#        return True
#    return False

# group = MatcherGroup(rule=for_pcr)

# matcher1 = group.on_message()
# matcher2 = group.on_message()
