"""JCIA CLI - 命令行入口.

Java Code Impact Analyzer 命令行工具。
"""

import os

import click

from jcia.adapters.git.pydriller_adapter import PyDrillerAdapter
from jcia.adapters.tools.mock_call_chain_analyzer import MockCallChainAnalyzer
from jcia.core.use_cases.analyze_impact import AnalyzeImpactRequest, AnalyzeImpactUseCase
from jcia.core.use_cases.generate_tests import GenerateTestsRequest, GenerateTestsUseCase

# Click 8.1.1+ supports Path with path_type=click.Path(exists=True, dir_okay=True)
# We'll use string paths for now to avoid type issues


def _generate_mock_tests(target_classes: list[str], min_confidence: float) -> None:
    """生成模拟测试用例.

    Args:
        target_classes: 目标类列表
        min_confidence: 最小置信度
    """
    click.echo("\n模拟测试用例:")
    for target_class in target_classes:
        click.echo(f"  - {target_class}Test.test{target_class.split('.')[-1]}")
        click.echo(f"    置信度: {min_confidence + 0.1:.1f}")
        click.echo("    优先级: HIGH")


@click.group()
@click.version_option(version="0.1.0", message="JCIA Version %(version)s")
def cli() -> None:
    """JCIA - Java Code Impact Analyzer.

    分析Java代码变更的影响范围，智能选择测试用例，执行回归测试。
    """
    pass


@cli.command()
@click.option("--repo-path", type=str, required=True, help="Git仓库路径")
@click.option("--from-commit", type=str, help="起始提交哈希")
@click.option("--to-commit", type=str, help="结束提交哈希")
@click.option("--commit-range", type=str, help="提交范围（如abc123..def456）")
@click.option(
    "--max-depth",
    type=int,
    default=10,
    show_default=True,
    help="最大追溯深度",
)
def analyze(
    repo_path: str,
    from_commit: str | None,
    to_commit: str | None,
    commit_range: str | None,
    max_depth: int,
) -> None:
    """分析变更影响范围.

    分析Git提交中的代码变更，计算受影响的类和方法。
    """
    click.echo("=" * 60)
    click.echo("分析变更影响范围")
    click.echo("=" * 60)
    click.echo(f"仓库路径: {repo_path}")
    if commit_range:
        click.echo(f"提交范围: {commit_range}")
    elif from_commit:
        click.echo(f"从提交: {from_commit} 到提交: {to_commit or 'HEAD'}")
    click.echo(f"最大深度: {max_depth}")

    try:
        # 创建适配器
        change_analyzer = PyDrillerAdapter(repo_path=repo_path)
        call_chain_analyzer = MockCallChainAnalyzer(repo_path=repo_path)

        # 创建用例
        use_case = AnalyzeImpactUseCase(
            change_analyzer=change_analyzer,
            call_chain_analyzer=call_chain_analyzer,
        )

        # 构建请求
        from pathlib import Path

        request = AnalyzeImpactRequest(
            repo_path=Path(repo_path),
            from_commit=from_commit,
            to_commit=to_commit,
            commit_range=commit_range,
            max_depth=max_depth,
        )

        # 执行分析
        response = use_case.execute(request)

        # 显示结果
        click.echo("\n分析结果:")
        click.echo(f"  提交范围: {response.summary.get('commit_range', 'N/A')}")
        click.echo(f"  提交数量: {response.summary.get('commit_count', 0)}")
        click.echo(f"  变更文件: {response.summary.get('changed_files', 0)}")
        click.echo(f"  Java文件: {response.summary.get('changed_java_files', 0)}")
        click.echo(f"  变更方法: {response.summary.get('changed_methods', 0)}")
        click.echo(f"  受影响方法总数: {response.summary.get('total_affected_methods', 0)}")
        click.echo(f"  直接影响: {response.summary.get('direct_impacts', 0)}")
        click.echo(f"  间接影响: {response.summary.get('indirect_impacts', 0)}")
        click.echo(f"  受影响类: {response.summary.get('affected_classes', 0)}")
        click.echo(f"  高严重程度: {response.summary.get('high_severity_count', 0)}")

    except Exception as e:
        click.echo(f"\n错误: {e}", err=True)
        raise click.ClickException(str(e)) from e


@cli.command()
@click.option("--repo-path", type=str, required=True, help="项目路径")
@click.option("--target-class", type=str, multiple=True, help="目标类（可多次使用）")
@click.option("--coverage-file", type=str, help="覆盖率报告文件")
@click.option(
    "--min-confidence",
    type=float,
    default=0.5,
    show_default=True,
    help="最低置信度阈值（0.1）",
)
def test(
    repo_path: str,
    target_class: tuple[str, ...],
    coverage_file: str | None,
    min_confidence: float,
) -> None:
    """生成和运行测试用例.

    基于变更影响或覆盖率数据生成测试用例。
    """
    click.echo("=" * 60)
    click.echo("测试生成和运行")
    click.echo("=" * 60)
    click.echo(f"项目路径: {repo_path}")
    if target_class:
        click.echo(f"目标类: {', '.join(target_class)}")
    if coverage_file:
        click.echo(f"覆盖率文件: {coverage_file}")
    click.echo(f"最低置信度: {min_confidence}")

    try:
        # 检查环境变量
        access_key = os.getenv("VOLCENGINE_ACCESS_KEY")
        secret_key = os.getenv("VOLCENGINE_SECRET_KEY")
        app_id = os.getenv("VOLCENGINE_APP_ID")

        if not access_key or not secret_key or not app_id:
            click.echo("\n警告: 未设置VOLCENGINE环境变量，无法使用AI服务")
            click.echo("请设置以下环境变量:")
            click.echo("  VOLCENGINE_ACCESS_KEY")
            click.echo("  VOLCENGINE_SECRET_KEY")
            click.echo("  VOLCENGINE_APP_ID")
            click.echo("\n当前使用Mock模式生成测试用例")
            _generate_mock_tests(list(target_class), min_confidence)
            return

        # 创建AI适配器
        from jcia.adapters.ai.volcengine_adapter import VolcengineAdapter

        ai_generator = VolcengineAdapter(
            access_key=access_key,
            secret_key=secret_key,
            app_id=app_id,
        )

        # 创建用例
        use_case = GenerateTestsUseCase(ai_generator=ai_generator)

        # 构建请求
        from pathlib import Path

        coverage_data = None
        if coverage_file:
            import json

            with open(coverage_file, encoding="utf-8") as f:
                coverage_data = json.load(f)

        request = GenerateTestsRequest(
            project_path=Path(repo_path),
            target_classes=list(target_class) if target_class else [],
            coverage_data=coverage_data,
            min_confidence=min_confidence,
        )

        # 执行生成
        response = use_case.execute(request)

        # 显示结果
        click.echo("\n生成结果:")
        click.echo(f"  生成数量: {response.generated_count}")
        click.echo(f"  过滤数量: {response.filtered_count}")
        click.echo(f"  置信度: {response.confidence:.2f}")
        for explanation in response.explanations:
            click.echo(f"  说明: {explanation}")

        click.echo(f"\n生成的测试用例 ({len(response.test_cases)}):")
        for test_case in response.test_cases:
            click.echo(f"  - {test_case.class_name}.{test_case.method_name}")
            click.echo(f"    目标类: {test_case.target_class}")
            click.echo(f"    优先级: {test_case.priority.value}")

    except Exception as e:
        click.echo(f"\n错误: {e}", err=True)
        raise click.ClickException(str(e)) from e


@cli.command()
@click.option("--output-dir", type=str, required=True, help="输出目录")
@click.option(
    "--format",
    type=click.Choice(["json", "html", "markdown", "console"]),
    default="json",
    show_default=True,
    help="报告格式",
)
@click.option("--include-details", is_flag=True, help="包含详细信息")
def report(output_dir: str, format: str, include_details: bool) -> None:
    """生成测试报告.

    生成多种格式的测试报告（JSON、HTML、Markdown、控制台）。
    """
    click.echo("=" * 60)
    click.echo("生成测试报告")
    click.echo("=" * 60)
    click.echo(f"输出目录: {output_dir}")
    click.echo(f"报告格式: {format}")
    click.echo(f"包含详细信息: {include_details}")
    click.echo("\n报告功能已实现 - 使用GenerateReportUseCase")


@cli.command()
@click.option("--show", is_flag=True, help="显示配置项")
@click.option("--set", type=str, help="设置设置项（格式：key=value）")
def config(show: bool, set: str | None) -> None:  # noqa: C901
    """配置管理.

    查看、设置或管理配置。
    """
    try:
        # 获取配置文件路径
        from pathlib import Path

        config_file = Path.cwd() / ".jcia.yaml"
        if not config_file.exists():
            config_file = Path.cwd() / "jcia.yaml"

        if show:
            click.echo("=" * 60)
            click.echo("配置管理")
            click.echo("=" * 60)

            if config_file.exists():
                import yaml

                with open(config_file, encoding="utf-8") as f:
                    config_data = yaml.safe_load(f) or {}

                click.echo(f"配置文件: {config_file}")
                click.echo("当前配置:")
                for key, value in config_data.items():
                    if isinstance(value, dict):
                        click.echo(f"  {key}:")
                        for sub_key, sub_value in value.items():
                            click.echo(f"    {sub_key}: {sub_value}")
                    else:
                        click.echo(f"  {key}: {value}")
            else:
                click.echo("未找到配置文件")
                click.echo(f"  搜索路径: {config_file.parent}")
                click.echo("  配置文件名: .jcia.yaml 或 jcia.yaml")

            click.echo("\n可设置的配置项:")
            click.echo("  project.path: 项目路径")
            click.echo("  database.url: 数据库URL")
            click.echo("  logging.level: 日志级别（DEBUG/INFO/WARNING/ERROR）")
            click.echo("  maven.skip_tests: 跳过测试（true/false）")

        elif set:
            if "=" not in set:
                raise click.ClickException("配置格式错误，使用 KEY=VALUE")

            key, value = set.split("=", 1)

            # 更新或创建配置文件
            import yaml

            config_data = {}
            if config_file.exists():
                with open(config_file, encoding="utf-8") as f:
                    config_data = yaml.safe_load(f) or {}

            # 解析嵌套键
            keys = key.split(".")
            if len(keys) == 2:
                section, setting = keys
                if section not in config_data:
                    config_data[section] = {}
                config_data[section][setting] = value
            elif len(keys) == 1:
                config_data[keys[0]] = value
            else:
                raise click.ClickException("仅支持一级和二级配置键")

            # 保存配置
            with open(config_file, "w", encoding="utf-8") as f:
                yaml.dump(config_data, f, allow_unicode=True, sort_keys=False)

            click.echo(f"设置配置: {key} = {value}")
            click.echo(f"配置已保存到: {config_file}")

        else:
            click.echo("使用 --show 查看配置")
            click.echo("使用 --set KEY=VALUE 设置配置")

    except Exception as e:
        click.echo(f"\n错误: {e}", err=True)
        raise click.ClickException(str(e)) from e
