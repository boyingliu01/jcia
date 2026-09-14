"""JCIA 命令行接口."""

from jcia.cli.main import cli

# setup.py 的 console_scripts 引用 jcia.cli:main。若不显式定义 main 别名，
# getattr 会命中 import 系统自动绑定的 jcia.cli.main 子模块对象（不可调用），
# 安装后的 jcia 命令启动即抛 TypeError。
main = cli

__all__ = ["cli", "main"]
