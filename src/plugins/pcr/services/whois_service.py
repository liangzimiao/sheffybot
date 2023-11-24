from ..models import WhoIsGuessResult
from .internal.data_service import chara_data


class WhoIsService:
    async def guess_chara(self, name: str) -> WhoIsGuessResult:
        """
        根据给定的角色名猜测角色。

        参数:
            name (str): 角色名。

        返回:
            WhoIsGuessResult: 角色猜测结果。
        """
        id = chara_data.name2id(name)
        guess_name = name
        score = 100
        if id == chara_data.UNKNOWN:
            (
                guess_name,
                score,
            ) = chara_data.match(name)
            id = chara_data.name2id(guess_name)
        c = await chara_data.from_id(id)
        return WhoIsGuessResult(score=score, guess_name=guess_name, guess_chara=c)
