"""基于源代码的静态调用链分析器.

不依赖外部工具（如 JACG），直接从 Java 源代码分析方法调用关系。
支持：
- 方法调用分析
- 类依赖分析
- 继承关系分析
- 反射调用检测与推断
"""

import logging
import re
from pathlib import Path
from typing import Any

from jcia.adapters.tools.reflection_models import (
    InferenceSource,
    ReflectionCallInfo,
    ReflectionType,
)
from jcia.adapters.tools.reflection_patterns import ReflectionPatternMatcher
from jcia.core.interfaces.call_chain_analyzer import (
    AnalyzerType,
    CallChainAnalyzer,
    CallChainDirection,
    CallChainGraph,
    CallChainNode,
)

logger = logging.getLogger(__name__)


class SourceCodeCallGraphAnalyzer(CallChainAnalyzer):
    """基于源代码的静态调用链分析器.

    直接解析 Java 源代码来分析方法调用关系，无需外部依赖。
    适用于：代码审查、影响分析、快速原型验证
    """

    def __init__(
        self,
        repo_path: str,
        max_depth: int = 10,
        cache_dir: Path | None = None,
    ) -> None:
        """初始化分析器.

        Args:
            repo_path: Java 项目路径
            max_depth: 最大分析深度
            cache_dir: 缓存目录
        """
        self._repo_path = Path(repo_path).resolve()
        self._max_depth = max_depth
        self._cache_dir = cache_dir or (self._repo_path / ".jcia" / "callgraph")
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        # 缓存
        self._method_calls_cache: dict[str, set[str]] = {}
        self._class_methods_cache: dict[str, dict[str, str]] = {}
        self._class_hierarchy_cache: dict[str, list[str]] = {}

        # 反射分析
        self._reflection_matcher = ReflectionPatternMatcher()
        self._reflection_calls_cache: dict[str, list[ReflectionCallInfo]] = {}

        # 扫描项目结构
        self._scan_project()

        logger.info(f"SourceCodeCallGraphAnalyzer initialized with repo: {self._repo_path}")

    @property
    def analyzer_type(self) -> AnalyzerType:
        """返回分析器类型."""
        return AnalyzerType.STATIC

    @property
    def supports_cross_service(self) -> bool:
        """是否支持跨服务分析."""
        return False

    def _scan_project(self) -> None:
        """扫描项目，收集所有 Java 类和方法信息."""
        src_dirs = [
            self._repo_path / "src" / "main" / "java",
            self._repo_path / "src" / "test" / "java",
            self._repo_path / "core" / "src" / "main" / "java",
            self._repo_path / "core" / "src" / "test" / "java",
        ]

        # 查找所有 Java 文件
        java_files: list[Path] = []
        for src_dir in src_dirs:
            if src_dir.exists():
                java_files.extend(src_dir.rglob("*.java"))

        # 如果上面的目录不存在，尝试直接在 repo_path 下查找
        if not java_files:
            java_files = list(self._repo_path.rglob("*.java"))

        # 过滤掉测试文件
        java_files = [f for f in java_files if "/test/" not in str(f)]

        logger.info(f"Found {len(java_files)} Java source files")

        # 分析每个文件
        for java_file in java_files:
            self._analyze_java_file(java_file)

    def _analyze_java_file(self, java_file: Path) -> None:
        """分析单个 Java 文件.

        Args:
            java_file: Java 文件路径
        """
        try:
            content = java_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return

        # 提取包名和类名
        package_match = re.search(r"package\s+([\w.]+);", content)
        package = package_match.group(1) if package_match else ""

        # 查找所有类定义（包括内部类）
        class_pattern = re.compile(
            r"(?:public\s+|private\s+|protected\s+)?(?:static\s+)?class\s+(\w+)"
            r"(?:\s+extends\s+([\w.]+))?"
            r"(?:\s+implements\s+([\w.,\s]+))?",
            re.MULTILINE,
        )

        for match in class_pattern.finditer(content):
            class_name = match.group(1)
            full_class_name = f"{package}.{class_name}" if package else class_name

            # 查找该类中的所有方法
            self._extract_methods_from_class(content, full_class_name)

            # 查找方法调用
            self._extract_method_calls(content, full_class_name)

            # 提取反射调用
            self._extract_reflection_calls(content, full_class_name)

    def _extract_methods_from_class(self, content: str, class_name: str) -> None:
        """从类中提取方法定义.

        Args:
            content: Java 文件内容
            class_name: 类全限定名
        """
        # 方法定义模式
        method_pattern = re.compile(
            r"(?:public\s+|private\s+|protected\s+)?"
            r"(?:static\s+)?"
            r"(?:final\s+)?"
            r"(?:[\w.]+\s+)?"
            r"(\w+)\s*\(",
            re.MULTILINE,
        )

        methods = {}
        for match in method_pattern.finditer(content):
            method_name = match.group(1)
            # 排除构造函数和常见关键字
            if method_name not in ("if", "for", "while", "switch", "catch", "class", "interface"):
                methods[method_name] = class_name

        if methods:
            self._class_methods_cache[class_name] = methods

    def _extract_method_calls(self, content: str, class_name: str) -> None:
        """从类中提取方法调用.

        Args:
            content: Java 文件内容
            class_name: 类全限定名
        """
        # 方法调用模式
        call_pattern = re.compile(
            r"(?:^|\.)(\w+)\s*\((?!.*\))",  # object.method(...)
            re.MULTILINE,
        )

        calls = set()
        for match in call_pattern.finditer(content):
            method_name = match.group(1)
            # 排除常见关键字
            if method_name not in ("if", "for", "while", "switch", "catch", "assert"):
                calls.add(method_name)

        if calls:
            self._method_calls_cache[class_name] = calls

    def _extract_reflection_calls(self, content: str, class_name: str) -> None:
        """从类中提取反射调用.

        Args:
            content: Java 文件内容
            class_name: 类全限定名
        """
        # 使用反射模式匹配器查找反射调用
        reflection_calls = self._reflection_matcher.find_patterns(content, class_name)

        # 同时查找链式反射调用
        chained_calls = self._reflection_matcher.find_chained_calls(content, class_name)

        # 合并结果
        all_reflection_calls = reflection_calls + chained_calls

        if all_reflection_calls:
            self._reflection_calls_cache[class_name] = all_reflection_calls
            logger.debug(
                f"Found {len(all_reflection_calls)} reflection calls in {class_name}"
            )

    def _infer_reflection_target(
        self, reflection_call: ReflectionCallInfo
    ) -> tuple[str | None, str | None]:
        """推断反射调用的目标.

        Args:
            reflection_call: 反射调用信息

        Returns:
            tuple[str | None, str | None]: (目标类, 目标方法)
        """
        # 如果已经有明确目标，直接返回
        if reflection_call.target_class or reflection_call.target_method:
            return reflection_call.target_class, reflection_call.target_method

        # 根据置信度和推断源决定
        if reflection_call.inference_source == InferenceSource.VARIABLE:
            # 尝试从上下文中获取变量值
            variable = reflection_call.context.get("variable")
            if variable:
                # 简单启发式：检查变量是否像类名
                if "." in variable or variable[0].isupper():
                    return variable, None

        return None, None

    def get_reflection_calls(self, class_name: str) -> list[ReflectionCallInfo]:
        """获取指定类的反射调用.

        Args:
            class_name: 类全限定名

        Returns:
            List[ReflectionCallInfo]: 反射调用列表
        """
        return self._reflection_calls_cache.get(class_name, [])

    def get_all_reflection_calls(self) -> dict[str, list[ReflectionCallInfo]]:
        """获取所有反射调用.

        Returns:
            Dict[str, List[ReflectionCallInfo]]: 类名到反射调用列表的映射
        """
        return self._reflection_calls_cache.copy()

    def analyze_reflection_impact(
        self, class_name: str, method_name: str | None = None
    ) -> list[ReflectionCallInfo]:
        """分析可能调用指定类/方法的反射调用.

        Args:
            class_name: 目标类名
            method_name: 目标方法名（可选）

        Returns:
            List[ReflectionCallInfo]: 可能调用目标的反射调用列表
        """
        results: list[ReflectionCallInfo] = []

        for source_class, calls in self._reflection_calls_cache.items():
            for call in calls:
                # 检查是否匹配目标类
                if call.target_class == class_name:
                    if method_name is None or call.target_method == method_name:
                        results.append(call)
                # 检查是否匹配目标方法（类名未知的情况）
                elif method_name and call.target_method == method_name:
                    results.append(call)

        return results

    def analyze_upstream(self, method: str, max_depth: int = 10) -> CallChainGraph:
        """分析上游调用者.

        Args:
            method: 方法全限定名
            max_depth: 最大追溯深度

        Returns:
            CallChainGraph: 上游调用链图
        """
        logger.debug(f"Analyzing upstream for method: {method}")

        # 解析方法名
        class_name, method_name = self._parse_method(method)

        # 收集所有调用者
        callers = self._find_callers(class_name, method_name, max_depth)

        # 构建调用图 - 创建根节点
        root_node = CallChainNode(
            class_name=class_name,
            method_name=method_name,
        )
        root_node.metadata["call_depth"] = 0
        root_node.metadata["severity"] = "HIGH"

        graph = CallChainGraph(
            root=root_node,
            direction=CallChainDirection.UPSTREAM,
            max_depth=max_depth,
        )

        # 添加调用者节点
        for caller_class, caller_method in callers:
            caller_node = CallChainNode(
                class_name=caller_class,
                method_name=caller_method,
            )
            caller_node.metadata["call_depth"] = 1
            caller_node.metadata["severity"] = "MEDIUM"
            root_node.children.append(caller_node)

        return graph

    def analyze_downstream(self, method: str, max_depth: int = 10) -> CallChainGraph:
        """分析下游被调用者.

        Args:
            method: 方法全限定名
            max_depth: 最大追溯深度

        Returns:
            CallChainGraph: 下游调用链图
        """
        logger.debug(f"Analyzing downstream for method: {method}")

        # 解析方法名
        class_name, method_name = self._parse_method(method)

        # 收集所有被调用者
        callees = self._find_callees(class_name, method_name, max_depth)

        # 构建调用图 - 创建根节点
        root_node = CallChainNode(
            class_name=class_name,
            method_name=method_name,
        )
        root_node.metadata["call_depth"] = 0
        root_node.metadata["severity"] = "HIGH"

        graph = CallChainGraph(
            root=root_node,
            direction=CallChainDirection.DOWNSTREAM,
            max_depth=max_depth,
        )

        # 添加被调用者节点
        for callee_class, callee_method in callees:
            callee_node = CallChainNode(
                class_name=callee_class,
                method_name=callee_method,
            )
            callee_node.metadata["call_depth"] = 1
            callee_node.metadata["severity"] = "LOW"
            root_node.children.append(callee_node)

        return graph

    def _find_callers(
        self, class_name: str, method_name: str, max_depth: int
    ) -> list[tuple[str, str]]:
        """查找调用指定方法的方法.

        Args:
            class_name: 类名
            method_name: 方法名
            max_depth: 最大深度

        Returns:
            list[tuple[str, str]]: [(类名, 方法名), ...]
        """
        callers = []

        # 简单实现：查找调用了同名方法的其他类
        for caller_class, calls in self._method_calls_cache.items():
            if method_name in calls and caller_class != class_name:
                callers.append((caller_class, method_name))

        # 检查反射调用
        reflection_callers = self.analyze_reflection_impact(class_name, method_name)
        for ref_call in reflection_callers:
            # 反射调用者的类名
            if ref_call.source_file not in [c[0] for c in callers]:
                callers.append((ref_call.source_file, ref_call.raw_expression[:50]))

        return callers[:max_depth]  # 限制数量

    def _find_callees(
        self, class_name: str, method_name: str, max_depth: int
    ) -> list[tuple[str, str]]:
        """查找被指定方法调用的方法.

        Args:
            class_name: 类名
            method_name: 方法名
            max_depth: 最大深度

        Returns:
            list[tuple[str, str]]: [(类名, 方法名), ...]
        """
        callees = []

        # 从缓存中查找该类调用的方法
        if class_name in self._method_calls_cache:
            calls = self._method_calls_cache[class_name]
            for called_method in calls:
                # 查找方法定义
                for target_class, methods in self._class_methods_cache.items():
                    if called_method in methods and target_class != class_name:
                        callees.append((target_class, called_method))

        # 检查反射调用目标
        reflection_calls = self._reflection_calls_cache.get(class_name, [])
        for ref_call in reflection_calls:
            if ref_call.target_class and ref_call.target_method:
                # 高置信度的反射调用目标
                if ref_call.is_high_confidence():
                    callees.append((ref_call.target_class, ref_call.target_method))
            elif ref_call.target_class:
                # 只有类名的情况
                callees.append((ref_call.target_class, "unknown"))

        return callees[:max_depth]

    def _parse_method(self, method: str) -> tuple[str, str]:
        """解析方法名.

        Args:
            method: 方法全限定名 (如 com.example.MyClass.myMethod)

        Returns:
            tuple[str, str]: (类名, 方法名)
        """
        if "." in method:
            parts = method.rsplit(".", 1)
            return parts[0], parts[1]
        return "", method

    def analyze_both_directions(
        self, method: str, max_depth: int = 10
    ) -> tuple[CallChainGraph, CallChainGraph]:
        """双向分析（上游 + 下游）.

        Args:
            method: 方法全限定名
            max_depth: 最大追溯深度

        Returns:
            tuple[CallChainGraph, CallChainGraph]: (上游图, 下游图)
        """
        upstream = self.analyze_upstream(method, max_depth)
        downstream = self.analyze_downstream(method, max_depth)

        return upstream, downstream

    def build_full_graph(self) -> CallChainGraph:
        """构建完整的调用图.

        Returns:
            CallChainGraph: 完整调用图
        """
        # 创建虚拟根节点
        root_node = CallChainNode(
            class_name="",
            method_name="__full_graph__",
        )
        root_node.metadata["call_depth"] = 0
        root_node.metadata["severity"] = "LOW"

        graph = CallChainGraph(
            root=root_node,
            direction=CallChainDirection.BOTH,
            max_depth=self._max_depth,
        )

        # 添加所有类作为根节点的子节点
        for class_name in self._class_methods_cache:
            class_node = CallChainNode(
                class_name=class_name,
                method_name="*",
            )
            class_node.metadata["call_depth"] = 1
            class_node.metadata["severity"] = "LOW"
            root_node.children.append(class_node)

        return graph

    def analyze_class_dependencies(self, class_name: str) -> dict[str, Any]:  # noqa: C901
        """分析类的依赖关系.

        Args:
            class_name: 类全限定名

        Returns:
            Dict[str, Any]: 依赖分析结果
        """
        dependencies = {
            "class_name": class_name,
            "dependencies": [],
            "dependents": [],
        }

        # 查找该类的依赖（它依赖哪些类）
        if class_name in self._method_calls_cache:
            calls: set[str] = self._method_calls_cache[class_name]
            for target_class in self._class_methods_cache:
                for called_method in calls:
                    # noqa: SIM102
                    target_methods = self._class_methods_cache.get(target_class, {})
                    if called_method in target_methods and target_class != class_name:
                        dependencies["dependencies"].append(target_class)

        # 查找依赖该类的其他类
        for other_class, calls in self._method_calls_cache.items():
            if other_class == class_name:
                continue
            calls: set[str] = calls
            for called_method in calls:
                # noqa: SIM102
                class_methods = self._class_methods_cache.get(class_name, {})
                if called_method in class_methods and other_class not in dependencies["dependents"]:
                    dependencies["dependents"].append(other_class)

        return dependencies

    def find_test_classes(self, class_name: str) -> list[str]:
        """查找对应的测试类.

        Args:
            class_name: 类全限定名

        Returns:
            List[str]: 测试类列表
        """
        # 简单模式：类名 + Test 或 Test + 类名
        simple_class_name = class_name.split(".")[-1]

        test_patterns = [
            f"{simple_class_name}Test",
            f"Test{simple_class_name}",
        ]

        test_classes = []
        for pattern in test_patterns:
            for known_class in self._class_methods_cache:
                if pattern in known_class:
                    test_classes.append(known_class)

        return test_classes
