"""TDD 合规性检查脚本.

检查测试文件和实现文件的创建时间，确保遵循 TDD 原则：
- 测试文件必须早于实现文件创建
- 禁止先实现后测试的开发方式
"""

import os
import sys
from pathlib import Path


def get_file_pairs(project_root: Path) -> list[tuple[Path, Path]]:
    """获取测试文件和实现文件的配对.

    Args:
        project_root: 项目根目录

    Returns:
        List[Tuple[Path, Path]]: (测试文件, 实现文件) 列表
    """
    file_pairs = []

    # 遍历项目目录
    for test_file in project_root.rglob("test_*.py"):
        # 确保在 tests 目录下
        if "tests" not in str(test_file):
            continue

        # 查找对应的实现文件
        # tests/unit/adapters/test_git/test_pydriller_adapter.py
        # -> jcia/adapters/git/pydriller_adapter.py
        rel_path = test_file.relative_to(project_root / "tests" / "unit")
        # test_git/test_pydriller_adapter.py -> adapters/git/pydriller_adapter.py
        parts = list(rel_path.parts)
        if parts[0].startswith("test_"):
            parts[0] = parts[0][5:]  # 移除 test_ 前缀

        # test_ai/test_volcengine_adapter.py -> adapters/ai/volcengine_adapter.py
        # test_git/test_pydriller_adapter.py -> adapters/git/pydriller_adapter.py
        if parts[0].startswith("test_"):
            parts[0] = parts[0][5:]

        # 构建实现文件路径
        impl_path = project_root / "jcia" / Path(*parts)

        # 检查实现文件是否存在
        if impl_path.exists():
            file_pairs.append((test_file, impl_path))

    return file_pairs


def check_tdd_compliance(
    file_pairs: list[tuple[Path, Path]],
) -> tuple[bool, list[dict[str, float | str]]]:
    """检查 TDD 合规性.

    Args:
        file_pairs: (测试文件, 实现文件) 列表

    Returns:
        tuple[bool, list[dict[str, float | str]]]: 是否全部合规及违规列表
    """
    all_compliant = True
    violations: list[dict[str, float | str]] = []

    for test_file, impl_file in file_pairs:
        test_mtime = os.path.getmtime(test_file)
        impl_mtime = os.path.getmtime(impl_file)

        # 测试文件必须早于或等于实现文件时间
        diff_seconds = test_mtime - impl_mtime
        if test_mtime > impl_mtime and diff_seconds > 120:  # 2分钟
            all_compliant = False
            violations.append(
                {
                    "test_file": str(test_file),
                    "impl_file": str(impl_file),
                    "test_time": test_mtime,
                    "impl_time": impl_mtime,
                    "diff_seconds": diff_seconds,
                }
            )

    return all_compliant, violations


def print_violations(violations: list[dict[str, float | str]]) -> None:
    """打印违规信息.

    Args:
        violations: 违规列表
    """

    print("❌ TDD 合规性检查失败！")
    print("\n发现以下违规（测试文件晚于实现文件创建）:\n")

    for v in violations:
        print(f"  📄 测试文件: {v['test_file']}")
        print(f"  💻 实现文件: {v['impl_file']}")
        print(f"  ⏰ 时间差: {v['diff_seconds']:.1f} 秒（测试文件晚）")
        print()

    print("\n📝 TDD 原则要求：")
    print("  1. 先编写测试代码（红阶段）")
    print("  2. 运行测试确认失败")
    print("  3. 实现功能代码让测试通过（绿阶段）")
    print("  4. 重构优化代码（蓝阶段）")
    print("\n请按照 TDD 流程重新开发！")


def main() -> int:
    """主函数.

    Returns:
        int: 退出码（0=成功，1=失败）
    """
    project_root = Path(__file__).parent.parent

    print("=" * 60)
    print("TDD 合规性检查")
    print("=" * 60)
    print(f"项目根目录: {project_root}")
    print()

    # 获取文件配对
    file_pairs = get_file_pairs(project_root)
    print(f"找到 {len(file_pairs)} 对测试/实现文件\n")

    if not file_pairs:
        print("⚠️  未找到测试/实现文件对，跳过检查")
        return 0

    # 检查合规性
    all_compliant, violations = check_tdd_compliance(file_pairs)

    if all_compliant:
        print("✅ TDD 合规性检查通过！")
        print(f"   所有 {len(file_pairs)} 个文件对都遵循 TDD 原则")
        return 0
    else:
        print_violations(violations)
        return 1


if __name__ == "__main__":
    sys.exit(main())
