import unicodedata

import zhconv


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
