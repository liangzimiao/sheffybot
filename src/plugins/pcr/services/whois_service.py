from typing import Union
from .internal.data_service import pcr_date
from .internal.data_service import chara_data
from ..models import WhoIsGuessResult


class WhoIsService:
    def __init__(self):
        pass

    def get_whois_info(self, domain):
        """
        获取域名的whois信息
        :param domain:
        :return:
        """
        pass

    def get_whois_info_by_ip(self, ip):
        """
        根据ip获取whois信息
        :param ip:
        :return:
        """
        pass

    def name2id(self, name):
        pass

    async def guess_name(self, name) -> WhoIsGuessResult:
        id = chara_data.name2id(name)
        probability = 100
        is_guess = False
        guess_name = name
        if id == chara_data.UNKNOWN:
            id, guess_name, probability = chara_data.guess_id(name)
            is_guess = True
        c = chara_data.from_id(id)
        return WhoIsGuessResult(
            is_guess=is_guess, probability=probability, guess_name=guess_name
        )
