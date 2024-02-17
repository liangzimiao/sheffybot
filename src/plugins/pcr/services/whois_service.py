from ..models import WhoIsGuessResult
from .data_service import chara_data


class WhoIsService:
    async def guess_chara(self, name: str) -> WhoIsGuessResult:
        """
        根据给定的角色名猜测角色。

        参数:
            name (str): 角色名。

        返回:
            WhoIsGuessResult: 角色猜测结果。
        """
        # 完全匹配花名册
        id = chara_data.name2id(name)
        guess_name = name
        score = 100
        is_guess = False
        # 不匹配花名册
        if id == chara_data.UNKNOWN:
            (
                guess_name,
                score,
            ) = chara_data.match(name)
            id = chara_data.name2id(guess_name)
            is_guess = True

        c = chara_data.get_chara_from_id(id)
        c.icon = (
            await chara_data.get_chara_icon(id) if id != chara_data.UNKNOWN else None
        )
        return WhoIsGuessResult(
            score=score, is_guess=is_guess, guess_name=guess_name, guess_chara=c
        )
