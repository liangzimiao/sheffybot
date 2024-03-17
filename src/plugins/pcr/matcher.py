from typing import Optional, Tuple, Type, Union

from nonebot.matcher import Matcher
from nonebot.plugin.on import _Group
from nonebot.plugin.on import on_command as _on_command


class CommandGroup(_Group):
    """命令组，用于声明一组有相同名称前缀的命令。

    参数:
        cmd: 指定命令内容
        prefix_aliases: 是否影响命令别名，给命令别名加前缀
        rule: 事件响应规则
        permission: 事件响应权限
        handlers: 事件处理函数列表
        temp: 是否为临时事件响应器（仅执行一次）
        expire_time: 事件响应器最终有效时间点，过时即被删除
        priority: 事件响应器优先级
        block: 是否阻止事件向更低优先级传递
        state: 默认 state
    """

    def __init__(
        self,
        cmd: Union[str, Tuple[str, ...]],
        cmd_aliases: Optional[Tuple[str, ...]] = None,
        prefix_aliases: bool = False,
        **kwargs,
    ):
        """命令前缀"""
        super().__init__(**kwargs)
        self.basecmd: Tuple[str, ...] = (cmd,) if isinstance(cmd, str) else cmd
        self.base_kwargs.pop("aliases", None)
        self.cmd_aliases = (
            (cmd_aliases,) if isinstance(cmd_aliases, str) else cmd_aliases
        )
        self.prefix_aliases = prefix_aliases

    def __repr__(self) -> str:
        return f"CommandGroup(cmd={self.basecmd}, matchers={len(self.matchers)})"

    def command(self, cmd: Union[str, Tuple[str, ...]], **kwargs) -> Type[Matcher]:
        """注册一个新的命令。新参数将会覆盖命令组默认值

        参数:
            cmd: 指定命令内容
            aliases: 命令别名
            force_whitespace: 是否强制命令后必须有指定空白符
            rule: 事件响应规则
            permission: 事件响应权限
            handlers: 事件处理函数列表
            temp: 是否为临时事件响应器（仅执行一次）
            expire_time: 事件响应器最终有效时间点，过时即被删除
            priority: 事件响应器优先级
            block: 是否阻止事件向更低优先级传递
            state: 默认 state
        """
        sub_cmd = (cmd,) if isinstance(cmd, str) else cmd
        # 前缀+命令
        cmd = self.basecmd + sub_cmd
        aliases_set = set()
        # 前缀别名+命令
        if self.cmd_aliases:
            aliases_set = aliases_set | {
                (cmd_alias,) + sub_cmd for cmd_alias in self.cmd_aliases
            }
        # 前缀+命令别名
        if self.prefix_aliases and (aliases := kwargs.get("aliases")):
            aliases_set = aliases_set | {
                self.basecmd + ((alias,) if isinstance(alias, str) else alias)
                for alias in aliases
            }
            # 前缀别名+命令别名
            if self.cmd_aliases:
                aliases_set = aliases_set | {
                    (cmd_alias,) + ((alias,) if isinstance(alias, str) else alias)
                    for alias in aliases
                    for cmd_alias in self.cmd_aliases
                }
        kwargs["aliases"] = aliases_set
        matcher = _on_command(cmd, **self._get_final_kwargs(kwargs))
        self.matchers.append(matcher)
        return matcher


pcr_group = CommandGroup(
    cmd="pcr", cmd_aliases=("PCR", ""), priority=10, prefix_aliases=True
)


# on_shell_command = pcr_group.shell_command
