
import unicodedata
from pathlib import Path

import zhconv

from .config import pcr_config

pcr_data_path: Path = pcr_config.pcr_data_path
"""PCR数据存放路径"""
pcr_res_path: Path = pcr_config.pcr_resources_path
"""PCR资源存放路径"""


def normalize_str(string) -> str:
    """
    规范化unicode字符串 并 转为小写 并 转为简体
    """
    string = unicodedata.normalize("NFKC", string)
    string = string.lower()
    string = zhconv.convert(string, "zh-hans")
    return string


def sort_priority(values, group):
    """
    根据给定的分组优先级对值列表进行排序。
    """

    def helper(x):
        if x in group:
            return 0, x
        return 1, x

    values.sort(key=helper)


def set_default(obj):
    """
    将一个集合对象转换为列表。

    参数:
        obj (set): 要转换的集合对象。

    返回值:
        list: 如果输入是一个集合对象，则返回转换后的列表对象，否则返回原始输入对象。
    """
    if isinstance(obj, set):
        return list(obj)
    return obj


def merge_dicts(
    dict1: dict[str, list[str]],
    dict2: dict[str, list[str]],
) -> dict[str, list[str]]:
    """
    合并两个字典并返回结果。
    参数:
        dict1 (Dict[str, list[str]]): 第一个要合并的字典。
        dict2 (Dict[str, list[str]]): 第二个要合并的字典。
    返回:
        Dict[str, list[str]]: 合并后的字典。
    注意:
        - 函数根据键合并两个字典的值。
        - 如果一个键在两个字典中都存在，则将值连接起来。
        - 函数对值进行一些兼容性处理。
    """
    # 创建一个新的字典来存储结果
    result = {}
    # 遍历第一个字典，将其内容添加到结果字典中
    for key, value in dict1.items():
        if key not in result:
            result[key] = value
        else:
            result[key] += value
    # 遍历第二个字典，将其内容添加到结果字典中
    for key, value in dict2.items():
        if key not in result:
            result[key] = value
        else:
            result[key] += value
    for key in result:
        # 由于返回数据可能出现全半角重复, 做一定程度的兼容性处理, 会将所有全角替换为半角, 并移除重别称
        for i, name in enumerate(result[key]):
            name_format = name.replace("（", "(")
            name_format = name_format.replace("）", ")")
            # name_format = normalize_str(name_format)
            result[key][i] = name_format
        n = result[key][0]
        group = {f"{n}"}
        # 转集合再转列表, 移除重复元素, 按原名日文优先顺序排列
        m = list(set(result[key]))
        sort_priority(m, group)
        result[key] = m
    return result
