# JCIA 核心适配器详细实现计划

**版本**: 1.0
**日期**: 2026-02-08
**作者**: Claude Code

---

## 概述

当前项目已有完整的接口定义和领域服务层，但以下6个关键适配器目前只有Mock实现，需要提供真实的工程实现。这些适配器是JCIA分析Java代码变更影响的核心组件，特别是对**远程调用（Dubbo、gRPC、RESTful）**的支持。

---

## 需要实现的6个适配器

### 1. **JavaAllCallGraphAdapter** - 静态调用链分析器

**接口**: `CallChainAnalyzer`
**位置**: `jcia/adapters/tools/java_all_call_graph_adapter.py`

#### 核心功能

分析Java代码的静态调用关系，包括：
- 直接方法调用（`a.method()`）
- 反射调用（`Method.invoke()`）
- 接口实现调用
- **远程调用识别**（Dubbo、gRPC、REST调用）

#### 技术选型

**Java-all-call-graph** (JACG) - 阿里开源的Java静态调用链分析工具

**GitHub**: https://github.com/bytedance/java-all-call-graph

#### 详细实现思路

##### 1. JACG集成方式

```python
class JavaAllCallGraphAdapter(CallChainAnalyzer):
    """基于 java-all-call-graph 的静态调用链分析器."""

    def __init__(self, repo_path: str, jacg_jar: str | None = None):
        self._repo_path = repo_path
        self._jacg_jar = jacg_jar or self._download_jacg()
        self._output_dir = Path(repo_path) / ".jcia" / "jacg"
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._cache = {}  # 调用链缓存
```

##### 2. JACG JAR下载和版本管理

```python
def _download_jacg(self) -> str:
    """自动下载 JACG JAR 包."""
    JACG_VERSION = "0.9.0"
    JACG_REPO = "https://github.com/bytedance/java-all-call-graph/releases/download"
    download_url = f"{JACG_REPO}/v{JACG_VERSION}/java-all-call-graph-{JACG_VERSION}-jar-with-dependencies.jar"

    jar_path = Path.home() / ".jcia" / "jacg" / f"jacg-{JACG_VERSION}.jar"
    if jar_path.exists():
        return str(jar_path)

    # 下载逻辑...
    return str(jar_path)
```

##### 3. 调用链分析执行

```python
def _analyze_with_jacg(self, method: str, direction: str) -> CallChainGraph:
    """使用 JACG 执行调用链分析."""
    # 解析方法全限定名
    class_name, method_name, signature = self._parse_method(method)

    # 构建JACG命令
    cmd = [
        "java", "-jar", self._jacg_jar,
        "--input-dir", self._repo_path,
        "--class", class_name,
        "--method", method_name,
        "--direction", direction,  # upstream/downstream
        "--max-depth", str(self.max_depth),
        "--output-format", "json",
        "--output-file", str(self._output_file)
    ]

    # 执行命令
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    # 解析JSON输出
    return self._parse_jacg_output(result.stdout)
```

##### 4. 远程调用识别

这是关键点！JACG的输出需要进一步分析来识别远程调用：

```python
def _identify_remote_calls(self, call_chain: CallChainGraph) -> CallChainGraph:
    """识别和标记远程调用节点."""

    for node in self._traverse_nodes(call_chain.root):
        # 检查注解
        annotations = self._extract_annotations(node.class_name, node.method_name)

        # Dubbo服务调用识别
        if self._is_dubbo_reference(annotations):
            node.service = self._extract_dubbo_service(annotations)
            node.metadata["call_type"] = "dubbo"
            node.metadata["interface"] = self._get_interface_class(annotations)

        # gRPC调用识别
        elif self._is_grpc_call(node.method_name):
            node.service = self._extract_grpc_service(node.class_name)
            node.metadata["call_type"] = "grpc"

        # REST调用识别
        elif self._is_rest_call(node.method_name, annotations):
            node.service = self._extract_rest_endpoint(annotations)
            node.metadata["call_type"] = "rest"

        # Feign调用识别
        elif self._is_feign_client(node.class_name):
            node.service = self._extract_feign_service(node.class_name)
            node.metadata["call_type"] = "feign"

    return call_chain

def _is_dubbo_reference(self, annotations: list[dict]) -> bool:
    """检查是否是Dubbo服务引用."""
    for ann in annotations:
        if ann["type"] in ("@Reference", "@org.apache.dubbo.config.annotation.Reference"):
            return True
    return False

def _is_grpc_call(self, method_name: str) -> bool:
    """检查是否是gRPC调用."""
    # gRPC方法通常在Stub类中，以异步调用模式命名
    grpc_patterns = [".newFutureStub(", ".newBlockingStub(", ".getStub()"]
    return any(p in method_name for p in grpc_patterns)

def _is_rest_call(self, method_name: str, annotations: list[dict]) -> bool:
    """检查是否是REST调用."""
    # RestTemplate或WebClient调用
    if any(x in method_name for x in ["RestTemplate", "WebClient", ".exchange(", ".getFor"]):
        return True

    # Feign客户端
    for ann in annotations:
        if "FeignClient" in ann.get("type", ""):
            return True

    return False
```

##### 5. 注解解析器

```python
def _extract_annotations(self, class_name: str, method_name: str) -> list[dict]:
    """提取类和方法的注解信息."""
    # 使用ASM或Javassist解析Java字节码
    class_file = self._find_class_file(class_name)
    if not class_file:
        return []

    # 解析字节码获取注解
    reader = ClassReader(class_file)
    visitor = AnnotationCollectorVisitor()
    reader.accept(visitor, ClassReader.SKIP_DEBUG)

    return visitor.annotations

class AnnotationCollectorVisitor(ClassVisitor):
    """注解收集器."""

    def __init__(self):
        self.annotations = []

    def visitAnnotation(self, desc: str, visible: bool) -> AnnotationVisitor:
        ann_type = desc.replace("/", ".").replace("L", "").replace(";", "")
        self.annotations.append({"type": ann_type})
        return AnnotationCollectorVisitor()
```

##### 6. 服务拓扑构建

```python
def build_service_topology(self, repo_path: str) -> dict[str, ServiceNode]:
    """构建微服务拓扑图."""
    services = {}

    # 扫描所有Java文件
    for java_file in Path(repo_path).rglob("*.java"):
        content = java_file.read_text()

        # 识别服务提供者（@Service + Dubbo相关）
        if "@DubboService" in content or "@Service" in content:
            service = self._parse_dubbo_service(content, java_file)
            if service:
                services[service.name] = service

        # 识别服务消费者（@Reference）
        if "@Reference" in content:
            consumer = self._parse_dubbo_consumer(content, java_file)
            if consumer:
                services[consumer.name] = consumer

    # 分析服务间依赖
    for service in services.values():
        service.dependencies = self._analyze_service_dependencies(service, services)

    return services

@dataclass
class ServiceNode:
    """服务节点."""
    name: str
    type: str  # dubbo/grpc/rest
    interfaces: list[str]
    dependencies: list[str]
    endpoints: list[dict]
```

##### 7. 配置文件解析

```python
def _parse_dubbo_config(self, repo_path: str) -> dict:
    """解析Dubbo配置文件."""
    configs = {}

    # 查找Dubbo配置文件
    config_files = [
        "dubbo.properties",
        "dubbo.yml",
        "dubbo.yaml",
        "application.yml",
        "application.properties"
    ]

    for config_file in config_files:
        config_path = Path(repo_path) / "src" / "main" / "resources" / config_file
        if config_path.exists():
            if config_file.endswith((".yml", ".yaml")):
                configs.update(self._parse_yaml_config(config_path))
            else:
                configs.update(self._parse_properties_config(config_path))

    return configs
```

---

### 2. **SkyWalkingCallChainAdapter** - 动态调用链分析器

**接口**: `CallChainAnalyzer`
**位置**: `jcia/adapters/tools/skywalking_call_chain_adapter.py`

#### 核心功能

通过SkyWalking的分布式追踪数据构建真实的调用链：
- 支持跨服务调用分析
- 基于实际运行时的调用关系
- 识别高频调用路径

#### 技术选型

**SkyWalking OAP Server** + **GraphQL API**

#### 详细实现思路

##### 1. SkyWalking API集成

```python
class SkyWalkingCallChainAdapter(CallChainAnalyzer):
    """基于 SkyWalking 的动态调用链分析器."""

    def __init__(
        self,
        oap_server: str = "http://localhost:12800",
        api_token: str | None = None,
        time_range: int = 7  # 天
    ):
        self._server = oap_server
        self._token = api_token
        self._time_range = time_range
        self._graphql_endpoint = f"{oap_server}/graphql"
        self._cache = LRUCache(maxsize=1000)

    @property
    def supports_cross_service(self) -> bool:
        """支持跨服务分析."""
        return True
```

##### 2. 动态调用链查询

```python
def analyze_upstream(self, method: str, max_depth: int = 10) -> CallChainGraph:
    """分析上游调用者（基于实际追踪数据）."""
    query = """
    query($serviceName: String!, $endpointName: String!, $start: Long!, $end: Long!) {
        getTrace: queryBasicTraces(condition: {
            serviceName: $serviceName
            endpointName: $endpointName
            queryDuration: { start: $start, end: $end }
            traceState: ALL
        }) {
            traces {
                segments {
                    serviceId
                    serviceCode
                    spans {
                        spanId
                        parentSpanId
                        peer
                        operationName
                        type
                        component
                        tags {
                            key
                            value
                        }
                    }
                }
            }
        }
    }
    """

    service, endpoint = self._parse_method_to_endpoint(method)
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = end_time - (self._time_range * 24 * 3600 * 1000)

    response = self._execute_graphql(query, {
        "serviceName": service,
        "endpointName": endpoint,
        "start": start_time,
        "end": end_time
    })

    return self._build_call_graph_from_traces(response)
```

##### 3. 跨服务调用识别

```python
def _build_call_graph_from_traces(self, traces_data: dict) -> CallChainGraph:
    """从SkyWalking追踪数据构建调用图."""
    graph = CallChainGraph(root=CallChainNode(...))

    for trace in traces_data["getTrace"]["traces"]:
        for segment in trace["segments"]:
            service_name = segment["serviceCode"]

            for span in segment["spans"]:
                # 识别服务间调用
                if span["type"] == "Exit":
                    peer = span.get("peer", "")
                    call_type = self._identify_call_type(span["tags"])

                    # 添加跨服务边
                    node = CallChainNode(
                        class_name=service_name,
                        method_name=span["operationName"],
                        service=peer,
                        metadata={
                            "call_type": call_type,
                            "component": span["component"],
                            "span_id": span["spanId"]
                        }
                    )

                    graph.root.children.append(node)

    return graph

def _identify_call_type(self, tags: list[dict]) -> str:
    """根据标签识别调用类型."""
    tag_dict = {t["key"]: t["value"] for t in tags}

    if "rpc" in tag_dict.get("url", "").lower():
        return "rpc"
    elif tag_dict.get("db.type"):
        return "database"
    elif tag_dict.get("mq.type"):
        return "message_queue"
    elif "http" in tag_dict.get("protocol", "").lower():
        return "http"

    return "local"
```

##### 4. Dubbo调用识别

```python
def _identify_dubbo_calls(self, traces_data: dict) -> dict[str, DubboCall]:
    """识别Dubbo调用."""
    dubbo_calls = {}

    for trace in traces_data["getTrace"]["traces"]:
        for segment in trace["segments"]:
            for span in segment["spans"]:
                if span["component"] == "Dubbo":
                    # 解析Dubbo调用信息
                    dubbo_call = DubboCall(
                        interface=span["tags"]["dubbo.interface"],
                        method=span["tags"]["dubbo.method"],
                        version=span["tags"].get("dubbo.version"),
                        group=span["tags"].get("dubbo.group"),
                        consumer=segment["serviceCode"],
                        provider=span.get("peer", "unknown")
                    )
                    dubbo_calls[span["spanId"]] = dubbo_call

    return dubbo_calls

@dataclass
class DubboCall:
    """Dubbo调用记录."""
    interface: str
    method: str
    version: str | None
    group: str | None
    consumer: str
    provider: str
```

##### 5. 服务拓扑可视化

```python
def get_service_topology(self) -> ServiceTopology:
    """获取服务拓扑."""
    query = """
    query {
        services {
            key: id
            label: name
            metrics {
                label: service_cpm
                value: avg
            }
        }
        topology {
            id
            name
            type
            components {
                id
                name
                type
                detectPoints {
                    componentId
                    serviceId
                    type
                }
            }
            links {
                sourceId
                targetId
                label
                detectPoints {
                    sourceComponentId
                    targetComponentId
                    type
                }
            }
        }
    }
    """

    response = self._execute_graphql(query, {})
    return self._parse_topology(response)
```

##### 6. GraphQL请求封装

```python
def _execute_graphql(self, query: str, variables: dict) -> dict:
    """执行GraphQL查询."""
    headers = {
        "Content-Type": "application/json"
    }

    if self._token:
        headers["SW-TOKEN"] = self._token

    payload = {
        "query": query,
        "variables": variables
    }

    response = requests.post(
        self._graphql_endpoint,
        json=payload,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    if "errors" in data:
        raise RuntimeError(f"GraphQL error: {data['errors']}")

    return data["data"]

def _parse_method_to_endpoint(self, method: str) -> tuple[str, str]:
    """将方法全限定名转换为SkyWalking endpoint格式."""
    # com.example.UserService.getById -> UserService/getById
    parts = method.split(".")
    if len(parts) >= 2:
        service_name = parts[-2]
        endpoint_name = parts[-1]
        return service_name, endpoint_name

    return method, method
```

---

### 3. **STARTSTestSelectorAdapter** - STARTS算法测试选择器

**接口**: `TestSelector`
**位置**: `jcia/adapters/tools/starts_test_selector_adapter.py`

#### 核心功能

实现STARTS（Static Test Assignment for Regression Test Selection）算法：
- 基于类级别依赖关系
- 测试-代码映射分析
- 增量测试选择

#### 技术选型

**STARTS Maven Plugin** + **Java编译时分析**

#### 详细实现思路

##### 1. STARTS Maven插件集成

```python
class STARTSTestSelectorAdapter(TestSelector):
    """基于 STARTS 算法的测试选择器."""

    def __init__(self, project_path: Path, maven_adapter: MavenAdapter):
        self._project_path = project_path
        self._maven = maven_adapter
        self._starts_version = "1.4"
        self._dependency_cache: dict[str, list[str]] = {}
        self._test_code_mapping: dict[str, set[str]] = {}

    def select_tests(
        self,
        changed_methods: list[str],
        project_path: Path,
        **kwargs: Any
    ) -> list[TestCase]:
        """选择需要执行的测试用例."""
        # 1. 使用STARTS Maven插件分析变更影响
        impacted_tests = self._run_starts_select(changed_methods)

        # 2. 构建TestCase对象
        test_cases = []
        for test_info in impacted_tests:
            test_case = self._build_test_case(test_info)
            test_cases.append(test_case)

        return test_cases

    def _run_starts_select(self, changed_methods: list[str]) -> list[dict]:
        """运行STARTS选择."""
        # 构建STARTS命令
        cmd = [
            "mvn", "starts:select",
            "-Dchanged.methods=" + ",".join(changed_methods),
            f"-Dstarts.version={self._starts_version}",
            "-q"  # 安静模式
        ]

        result = self._maven.execute(args=cmd[1:])

        if not result.success:
            raise RuntimeError(f"STARTS execution failed: {result.stderr}")

        return self._parse_starts_output(result.stdout)
```

##### 2. 测试-代码映射分析

```python
def _build_test_code_mapping(self) -> dict[str, set[str]]:
    """构建测试到代码的映射关系."""
    if self._test_code_mapping:
        return self._test_code_mapping

    # 使用JaCoCo或ASM分析测试覆盖
    mapping = {}

    # 执行测试并收集覆盖率
    coverage_cmd = ["mvn", "clean", "test", "jacoco:dump"]
    self._maven.execute(args=coverage_cmd)

    # 解析JaCoCo XML报告
    jacoco_xml = self._project_path / "target" / "site" / "jacoco" / "jacoco.xml"
    if jacoco_xml.exists():
        mapping = self._parse_jacoco_xml(jacoco_xml)

    self._test_code_mapping = mapping
    return mapping

def _parse_jacoco_xml(self, xml_path: Path) -> dict[str, set[str]]:
    """解析JaCoCo覆盖率XML."""
    import xml.etree.ElementTree as ET

    mapping = {}
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # 遍历所有包和类
    for package in root.findall(".//package"):
        package_name = package.get("name")

        for class_elem in package.findall(".//class"):
            class_name = class_elem.get("name").replace("/", ".")

            # 找到覆盖这个类的测试
            for method in class_elem.findall(".//method"):
                test_name = f"{package_name}.{class_name.split('.')[-1]}Test"
                if test_name not in mapping:
                    mapping[test_name] = set()
                mapping[test_name].add(f"{class_name}.{method.get('name')}")

    return mapping
```

##### 3. 增量依赖分析

```python
def _analyze_class_dependencies(self, class_name: str) -> list[str]:
    """分析类依赖（增量）."""
    if class_name in self._dependency_cache:
        return self._dependency_cache[class_name]

    # 使用Java编译器API或ASM分析字节码
    class_file = self._find_class_file(class_name)

    try:
        with open(class_file, "rb") as f:
            class_bytes = f.read()

        reader = ClassReader(class_bytes)
        visitor = DependencyCollectorVisitor()
        reader.accept(visitor, ClassReader.EXPAND_FRAMES)

        dependencies = visitor.dependencies
        self._dependency_cache[class_name] = dependencies
        return dependencies
    except Exception as e:
        logger.warning(f"Failed to analyze dependencies for {class_name}: {e}")
        return []

class DependencyCollectorVisitor(ClassVisitor):
    """依赖收集器."""

    def __init__(self):
        self.dependencies = []

    def visit(self, version: int, access: int, name: str, signature: str,
              super_name: str, interfaces: list[str]) -> None:
        self.dependencies.append(super_name)
        self.dependencies.extend(interfaces)

    def visitMethod(self, name: str, desc: str, signature: str,
                   exceptions: list[str]) -> MethodVisitor:
        return MethodDependencyCollector(self.dependencies)
```

##### 4. 变更传播分析

```python
def _propagate_changes(self, changed_methods: list[str]) -> set[str]:
    """传播变更影响（STARTS算法核心）."""
    affected = set(changed_methods)
    work_queue = list(changed_methods)
    max_depth = 10
    depth = 0

    while work_queue and depth < max_depth:
        next_queue = []

        for method in work_queue:
            class_name = method.split(".")[-2]
            dependencies = self._analyze_class_dependencies(class_name)

            for dep in dependencies:
                if dep not in affected:
                    affected.add(dep)
                    next_queue.append(dep)

        work_queue = next_queue
        depth += 1

    return affected

def _select_affected_tests(self, affected_methods: set[str]) -> list[str]:
    """选择受影响的测试."""
    selected = []

    for test_class, covered_methods in self._test_code_mapping.items():
        # 检查测试覆盖的方法是否受影响
        if not covered_methods.isdisjoint(affected_methods):
            selected.append(test_class)

    return selected
```

##### 5. 配置文件生成

```python
def generate_starts_config(self, output_path: Path) -> None:
    """生成STARTS配置文件."""
    config = {
        "starts": {
            "version": self._starts_version,
            "includeDependencies": True,
            "maxDepth": 10,
            "outputFormat": "json"
        },
        "maven": {
            "surefirePluginVersion": "2.22.2",
            "failsafePluginVersion": "2.22.2"
        }
    }

    with open(output_path, "w") as f:
        json.dump(config, f, indent=2)
```

---

### 4. **MavenSurefireTestExecutor** - Maven测试执行器

**接口**: `TestExecutor`
**位置**: `jcia/adapters/test_runners/maven_surefire_test_executor.py`

#### 核心功能

执行Maven Surefire测试：
- 选择性测试执行
- 覆盖率收集
- 结果解析

#### 技术选型

**Maven Surefire Plugin** + **JaCoCo Plugin**

#### 详细实现思路

##### 1. Maven Surefire集成

```python
class MavenSurefireTestExecutor(TestExecutor):
    """基于 Maven Surefire 的测试执行器."""

    def __init__(self, project_path: Path, maven_adapter: MavenAdapter):
        self._project_path = project_path
        self._maven = maven_adapter
        self._surefire_reports = project_path / "target" / "surefire-reports"
        self._jacoco_reports = project_path / "target" / "site" / "jacoco"

    def execute_tests(
        self,
        test_cases: list[TestCase] | None = None,
        project_path: Path | None = None,
        **kwargs: Any,
    ) -> TestSuiteResult:
        """执行测试."""
        if not test_cases:
            # 执行所有测试
            return self._run_all_tests(**kwargs)

        # 执行选定的测试
        return self._run_selected_tests(test_cases, **kwargs)

    def _run_selected_tests(self, test_cases: list[TestCase], **kwargs: Any) -> TestSuiteResult:
        """运行选定的测试."""
        # 构建Surefire测试选择参数
        test_pattern = self._build_test_pattern(test_cases)

        cmd = [
            "mvn", "surefire:test",
            f"-Dtest={test_pattern}",
            "-DfailIfNoTests=false"
        ]

        # 添加覆盖率
        if kwargs.get("with_coverage", False):
            cmd.append("jacoco:prepare-agent")
            cmd.insert(-1, "jacoco:report")

        result = self._maven.execute(args=cmd[1:])

        return self._parse_test_results()

    def _build_test_pattern(self, test_cases: list[TestCase]) -> str:
        """构建Maven测试模式."""
        # Surefire支持通配符测试选择
        patterns = []

        for tc in test_cases:
            # 提取简单类名
            simple_class = tc.class_name.split(".")[-1]
            # Surefire模式: TestClass#testMethod
            if tc.method_name:
                patterns.append(f"{simple_class}#{tc.method_name}")
            else:
                patterns.append(f"{simple_class}")

        return ",".join(patterns)
```

##### 2. 测试结果解析

```python
def _parse_test_results(self) -> TestSuiteResult:
    """解析Surefire测试结果."""
    result = TestSuiteResult()

    if not self._surefire_reports.exists():
        return result

    for xml_file in self._surefire_reports.glob("TEST-*.xml"):
        test_suite = self._parse_test_suite_xml(xml_file)

        result.total_tests += test_suite["total"]
        result.passed_tests += test_suite["passed"]
        result.failed_tests += test_suite["failed"]
        result.skipped_tests += test_suite["skipped"]
        result.error_tests += test_suite["errors"]
        result.total_duration_ms += test_suite["duration"]

        result.test_results.extend(test_suite["cases"])

    return result

def _parse_test_suite_xml(self, xml_path: Path) -> dict:
    """解析单个测试套件XML."""
    import xml.etree.ElementTree as ET

    tree = ET.parse(xml_path)
    root = tree.getroot()

    test_suite = {
        "total": int(root.get("tests", 0)),
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "errors": 0,
        "duration": int(float(root.get("time", 0)) * 1000),
        "cases": []
    }

    for test_case in root.findall("testcase"):
        case = self._parse_test_case(test_case)
        test_suite["cases"].append(case)

        if case["status"] == TestStatus.PASSED:
            test_suite["passed"] += 1
        elif case["status"] == TestStatus.FAILED:
            test_suite["failed"] += 1
        elif case["status"] == TestStatus.SKIPPED:
            test_suite["skipped"] += 1
        elif case["status"] == TestStatus.ERROR:
            test_suite["errors"] += 1

    return test_suite

def _parse_test_case(self, element) -> dict:
    """解析单个测试用例."""
    class_name = element.get("classname", "")
    method_name = element.get("name", "")
    duration = int(float(element.get("time", 0)) * 1000)

    # 查找失败/错误信息
    failure = element.find("failure")
    error = element.find("error")

    if failure is not None:
        status = TestStatus.FAILED
        error_message = failure.get("message", "")
        stack_trace = failure.text or ""
    elif error is not None:
        status = TestStatus.ERROR
        error_message = error.get("message", "")
        stack_trace = error.text or ""
    elif element.find("skipped") is not None:
        status = TestStatus.SKIPPED
        error_message = None
        stack_trace = None
    else:
        status = TestStatus.PASSED
        error_message = None
        stack_trace = None

    return TestExecutionResult(
        test_class=class_name,
        test_method=method_name,
        status=status,
        duration_ms=duration,
        error_message=error_message,
        stack_trace=stack_trace
    )
```

##### 3. 覆盖率收集

```python
def execute_with_coverage(
    self,
    test_cases: list[TestCase] | None = None,
    project_path: Path | None = None,
    **kwargs: Any,
) -> TestSuiteResult:
    """执行测试并收集覆盖率."""
    # 配置JaCoCo
    self._configure_jacoco()

    # 执行测试
    result = self.execute_tests(test_cases, project_path, with_coverage=True, **kwargs)

    # 解析覆盖率数据
    coverage_data = self._parse_jacoco_coverage()
    result.coverage_percent = coverage_data.get("line_coverage", 0.0)

    return result

def _configure_jacoco(self) -> None:
    """配置JaCoCo插件."""
    pom_path = self._project_path / "pom.xml"

    # 检查是否已配置JaCoCo
    tree = ET.parse(pom_path)
    root = tree.getroot()

    if not root.find(".//{*}artifactId[text()='jacoco-maven-plugin']"):
        # 添加JaCoCo插件配置
        self._add_jacoco_plugin(root)
        tree.write(pom_path, encoding="utf-8", xml_declaration=True)

def _parse_jacoco_coverage(self) -> dict:
    """解析JaCoCo覆盖率数据."""
    jacoco_xml = self._jacoco_reports / "jacoco.xml"

    if not jacoco_xml.exists():
        return {"line_coverage": 0.0}

    import xml.etree.ElementTree as ET
    tree = ET.parse(jacoco_xml)
    root = tree.getroot()

    total_lines = 0
    covered_lines = 0

    for counter in root.findall(".//counter"):
        if counter.get("type") == "LINE":
            total_lines += int(counter.get("missed"))
            total_lines += int(counter.get("covered"))
            covered_lines += int(counter.get("covered"))

    line_coverage = (covered_lines / total_lines * 100) if total_lines > 0 else 0.0

    return {
        "line_coverage": line_coverage,
        "total_lines": total_lines,
        "covered_lines": covered_lines
    }
```

##### 4. 增量测试执行

```python
def execute_incremental_tests(
    self,
    baseline_file: Path,
    changed_methods: list[str],
    **kwargs: Any
) -> TestSuiteResult:
    """增量测试执行（仅运行受影响的测试）."""
    # 读取基线测试结果
    baseline = self._load_baseline(baseline_file)

    # 选择受影响的测试
    affected_tests = self._select_affected_tests(
        changed_methods, baseline["test_results"]
    )

    # 执行受影响的测试
    return self.execute_tests(affected_tests, **kwargs)

def _load_baseline(self, baseline_file: Path) -> dict:
    """加载基线测试结果."""
    with open(baseline_file) as f:
        return json.load(f)

def _select_affected_tests(
    self,
    changed_methods: list[str],
    baseline_tests: list[TestExecutionResult]
) -> list[TestCase]:
    """选择受影响的测试."""
    affected = []

    for test in baseline_tests:
        # 检查测试是否覆盖变更的方法
        if self._is_test_affected(test, changed_methods):
            affected.append(TestCase(
                class_name=test.test_class,
                method_name=test.test_method,
                test_type=TestType.UNIT
            ))

    return affected
```

---

### 5. **OpenAIAdapter** - OpenAI适配器

**接口**: `AITestGenerator`, `AIAnalyzer`
**位置**: `jcia/adapters/ai/openai_adapter.py`

#### 核心功能

集成OpenAI API：
- 测试用例生成
- 代码分析
- 代码解释

#### 技术选型

**OpenAI API** (GPT-4/GPT-3.5-turbo)

#### 详细实现思路

##### 1. OpenAI API集成

```python
class OpenAIAdapter(AITestGenerator, AIAnalyzer):
    """OpenAI 服务适配器."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4-turbo-preview",
        base_url: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 60
    ):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url or "https://api.openai.com/v1"
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout = timeout

    @property
    def provider(self) -> AIProvider:
        """返回AI服务提供商."""
        return AIProvider.OPENAI

    @property
    def model(self) -> str:
        """返回使用的模型名称."""
        return self._model
```

##### 2. 测试用例生成

```python
def generate_tests(
    self,
    request: TestGenerationRequest,
    project_path: Path,
    **kwargs: Any,
) -> TestGenerationResponse:
    """使用AI生成测试用例."""
    # 构建上下文
    context = self._build_generation_context(request, project_path)

    # 构建prompt
    messages = [
        {
            "role": "system",
            "content": """你是一个专业的Java测试工程师。你的任务是：
1. 为给定的Java类生成高质量的单元测试
2. 测试应覆盖所有边界条件和异常情况
3. 使用JUnit 5和Mockito框架
4. 生成的测试代码应该可以直接编译运行

输出格式：每个测试用例使用```java```代码块包裹。"""
        },
        {
            "role": "user",
            "content": self._build_test_generation_prompt(request, context)
        }
    ]

    # 调用OpenAI API
    response = self._call_openai_api(
        messages=messages,
        temperature=kwargs.get("temperature", self._temperature)
    )

    # 解析响应
    return self._parse_test_generation_response(response, request)

def _build_test_generation_prompt(
    self,
    request: TestGenerationRequest,
    context: dict
) -> str:
    """构建测试生成prompt."""
    prompt = f"""
# 代码生成任务

## 目标类
{chr(10).join(f'- {cls}' for cls in request.target_classes)}

## 相关代码
"""
    for class_name, code in request.code_snippets.items():
        prompt += f"\n### {class_name}\n```java\n{code}\n```\n"

    if context.get("dependencies"):
        prompt += "\n## 依赖信息\n"
        for dep in context["dependencies"]:
            prompt += f"- {dep}\n"

    if request.requirements:
        prompt += f"\n## 特殊要求\n{request.requirements}\n"

    prompt += """

请为以上类生成完整的单元测试。每个测试类应该：
1. 使用@Test注解标记测试方法
2. 使用@ExtendWith(MockitoExtension.class)启用Mockito
3. 为所有外部依赖创建Mock对象
4. 测试正常流程和异常情况
5. 使用assertThat或assertEquals进行断言
"""
    return prompt
```

##### 3. 覆盖率驱动的测试生成

```python
def generate_for_uncovered(
    self,
    coverage_data: dict[str, Any],
    project_path: Path,
    **kwargs: Any,
) -> TestGenerationResponse:
    """为未覆盖代码生成测试."""
    # 提取未覆盖的代码段
    uncovered = self._extract_uncovered_segments(coverage_data, project_path)

    if not uncovered:
        return TestGenerationResponse(
            test_cases=[],
            explanations=["没有未覆盖的代码"],
            confidence=1.0,
            tokens_used=0
        )

    # 为每个未覆盖段生成测试
    all_test_cases = []
    all_explanations = []

    for segment in uncovered:
        request = TestGenerationRequest(
            target_classes=[segment["class_name"]],
            code_snippets={
                segment["class_name"]: segment["code"]
            },
            context={
                "uncovered_lines": segment["lines"],
                "branch_coverage": segment.get("branch", 0)
            },
            requirements=f"""
请为以下代码生成测试，以覆盖第{segment['lines']}行：
重点覆盖未覆盖的分支和条件。
"""
        )

        response = self.generate_tests(request, project_path, **kwargs)
        all_test_cases.extend(response.test_cases)
        all_explanations.extend(response.explanations)

    return TestGenerationResponse(
        test_cases=all_test_cases,
        explanations=all_explanations,
        confidence=0.85,
        tokens_used=sum(r.tokens_used for r in [response])  # 简化处理
    )

def _extract_uncovered_segments(
    self,
    coverage_data: dict,
    project_path: Path
) -> list[dict]:
    """提取未覆盖的代码段."""
    segments = []

    for class_info in coverage_data.get("classes", []):
        if class_info["line_coverage"] < 100:
            # 读取源代码
            source_file = self._find_source_file(
                class_info["name"],
                project_path
            )

            if source_file:
                lines = source_file.read_text().split("\n")

                # 提取未覆盖的代码段
                uncovered_lines = [
                    i + 1  # 转换为1-based
                    for i, covered in enumerate(class_info["lines"])
                    if covered == 0
                ]

                # 提取上下文
                if uncovered_lines:
                    first_line = min(uncovered_lines)
                    last_line = min(max(uncovered_lines), first_line + 20)

                    segment = {
                        "class_name": class_info["name"],
                        "code": "\n".join(lines[first_line-1:last_line]),
                        "lines": uncovered_lines,
                        "branch": class_info.get("branch_coverage", 0)
                    }
                    segments.append(segment)

    return segments
```

##### 4. API调用封装

```python
def _call_openai_api(
    self,
    messages: list[dict],
    **kwargs: Any
) -> dict:
    """调用OpenAI API."""
    import openai

    client = openai.OpenAI(
        api_key=self._api_key,
        base_url=self._base_url,
        timeout=self._timeout
    )

    try:
        response = client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=kwargs.get("temperature", self._temperature),
            max_tokens=self._max_tokens,
            **kwargs
        )

        return {
            "choices": [{
                "message": {
                    "content": response.choices[0].message.content
                }
            }],
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }
    except openai.APIError as e:
        logger.error(f"OpenAI API error: {e}")
        raise
```

---

### 6. **SkyWalkingAdapter** - SkyWalking APM适配器

**接口**: 可选，主要用于动态分析和测试推荐
**位置**: `jcia/adapters/ai/skywalking_adapter.py`

**注意**: 这个适配器主要用于动态分析和测试推荐，与SkyWalkingCallChainAdapter不同。

#### 核心功能

基于SkyWalking数据：
- 测试用例推荐
- 性能瓶颈分析
- 异常追踪

#### 详细实现思路

##### 1. APM数据集成

```python
class SkyWalkingAdapter:
    """SkyWalking APM数据适配器."""

    def __init__(
        self,
        oap_server: str = "http://localhost:12800",
        api_token: str | None = None
    ):
        self._oap_server = oap_server
        self._token = api_token
        self._graphql_endpoint = f"{oap_server}/graphql"
```

##### 2. 测试推荐

```python
def recommend_tests(
    self,
    changed_methods: list[str],
    time_range: int = 7
) -> list[dict]:
    """基于APM数据推荐测试."""
    # 1. 查找相关服务endpoint
    endpoints = self._find_related_endpoints(changed_methods)

    # 2. 分析endpoint的调用频率和错误率
    endpoint_stats = self._analyze_endpoint_stats(endpoints, time_range)

    # 3. 生成测试推荐
    recommendations = []
    for stat in endpoint_stats:
        if stat["error_rate"] > 0.01 or stat["slow_calls"] > 10:
            recommendations.append({
                "endpoint": stat["endpoint"],
                "test_priority": "HIGH",
                "reason": f"错误率{stat['error_rate']:.2%}或慢调用{stat['slow_calls']}次",
                "suggested_tests": self._suggest_tests_for_endpoint(stat)
            })

    return recommendations
```

##### 3. 相关Endpoint查找

```python
def _find_related_endpoints(self, methods: list[str]) -> list[str]:
    """查找相关endpoint."""
    query = """
    query($endpoints: [String!]!) {
        endpoints: searchEndpoint(keyword: $endpoints) {
            key: id
            label: name
            serviceId
            serviceName
            type
        }
    }
    """

    # 将方法名转换为可能的endpoint
    endpoint_keywords = [
        m.split(".")[-1]
        for m in methods
    ]

    response = self._execute_graphql(query, {"endpoints": endpoint_keywords})
    return response.get("endpoints", [])
```

##### 4. Endpoint统计分析

```python
def _analyze_endpoint_stats(
    self,
    endpoints: list[str],
    time_range: int
) -> list[dict]:
    """分析endpoint统计."""
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = end_time - (time_range * 24 * 3600 * 1000)

    query = """
    query($ids: [ID!]!, $start: Long!, $end: Long!) {
        stats: queryEndpointStats(duration: { start: $start, end: $end }) {
            endpointId
            sla
            throughput
            responseTime: latency {
                avg
                p95
                p99
            }
            errorRate: errorRate {
                value
            }
        }
    }
    """

    response = self._execute_graphql(query, {
        "ids": endpoints,
        "start": start_time,
        "end": end_time
    })

    return self._process_stats(response["stats"])
```

##### 5. 异常追踪

```python
def analyze_exceptions(
    self,
    service_name: str,
    time_range: int = 7
) -> list[dict]:
    """分析服务异常."""
    query = """
    query($serviceId: ID!, $start: Long!, $end: Long!) {
        exceptions: queryLogs(condition: {
            keyword: "ERROR"
            duration: { start: $start, end: $end }
            serviceName: $serviceId
        }) {
            logs {
                timestamp
                serviceId
                endpointId
                traceId
                contentType: exception
                content: exception {
                    exceptionType
                    message
                    stackTrace {
                        className
                        methodName
                        lineNumber
                    }
                }
            }
        }
    }
    """

    end_time = int(datetime.now().timestamp() * 1000)
    start_time = end_time - (time_range * 24 * 3600 * 1000)

    response = self._execute_graphql(query, {
        "serviceId": service_name,
        "start": start_time,
        "end": end_time
    })

    return self._parse_exception_logs(response["exceptions"])
```

##### 6. GraphQL查询封装

```python
def _execute_graphql(self, query: str, variables: dict) -> dict:
    """执行GraphQL查询."""
    headers = {
        "Content-Type": "application/json"
    }

    if self._token:
        headers["SW-TOKEN"] = self._token

    payload = {
        "query": query,
        "variables": variables
    }

    response = requests.post(
        self._graphql_endpoint,
        json=payload,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    if "errors" in data:
        raise RuntimeError(f"GraphQL error: {data['errors']}")

    return data["data"]
```

---

## 实现优先级和时间估算

| 适配器 | 优先级 | 预估时间 | 复杂度 |
|--------|--------|----------|--------|
| 1. JavaAllCallGraphAdapter | P0 (核心) | 5-7天 | 高 |
| 2. MavenSurefireTestExecutor | P0 (核心) | 3-4天 | 中 |
| 3. STARTSTestSelectorAdapter | P1 (重要) | 4-5天 | 中高 |
| 4. SkyWalkingCallChainAdapter | P1 (重要) | 4-5天 | 中高 |
| 5. OpenAIAdapter | P2 (可选) | 2-3天 | 低 |
| 6. SkyWalkingAdapter (APM) | P3 (可选) | 3-4天 | 中 |

**总计**: 21-28天

---

## 关键技术难点和解决方案

### 难点1: Dubbo远程调用识别

**解决方案**:
- 注解分析: `@Reference`, `@Service`
- 配置文件解析: `dubbo.properties`, `spring.xml`
- 接口扫描: 查找`interface`定义
- 动态代理识别: 分析`Proxy`类

### 难点2: 跨服务调用链分析

**解决方案**:
- 使用SkyWalking的分布式追踪数据
- 构建服务拓扑图
- 使用TraceID关联跨服务调用
- 识别同步/异步调用

### 难点3: STARTS算法性能优化

**解决方案**:
- 增量依赖分析
- 结果缓存
- 并行处理
- 索引构建

### 难点4: 覆盖率数据精确性

**解决方案**:
- 使用JaCoCo离线模式
- 字节码级覆盖率
- 分支覆盖率分析
- 行号精确映射

---

## 测试策略

### 单元测试
- Mock外部工具调用
- 覆盖核心逻辑
- 边界条件测试

### 集成测试
- 真实Java项目测试
- Dubbo/gRPC服务测试
- Maven构建测试

### 性能测试
- 大型项目分析性能
- 内存占用测试
- 并发处理测试

---

## 依赖清单

### Java工具
- java-all-call-graph (JACG)
- JaCoCo
- ASM
- Maven Surefire Plugin

### Python库
- requests (已安装)
- openai (新增)
- pytest-mock (已安装)

### 外部服务
- SkyWalking OAP Server
- OpenAI API / Volcengine API

---

## 风险和缓解措施

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| JACG工具维护停滞 | 高 | 考虑替代方案(ASM/JavaParser) |
| 远程调用识别不完整 | 中 | 提供配置文件手动映射 |
| STARTS算法性能 | 中 | 增量分析和缓存 |
| SkyWalking API变化 | 低 | 版本兼容性检查 |
| OpenAI API限制 | 低 | 限流和重试机制 |

---

## 总结

这份计划详细说明了6个适配器的实现思路，重点包括：

1. **远程调用识别**: 通过注解分析、配置解析、字节码分析识别Dubbo/gRPC/REST调用
2. **跨服务分析**: 使用SkyWalking分布式追踪数据构建服务拓扑
3. **智能测试选择**: 基于STARTS算法和影响图的测试选择
4. **Maven集成**: 完整的测试执行和覆盖率收集

---

## 下一步行动

确认计划后，建议按以下顺序实施：

1. **Phase 1**: 实现JavaAllCallGraphAdapter（静态分析基础）
2. **Phase 2**: 实现MavenSurefireTestExecutor（测试执行基础）
3. **Phase 3**: 实现STARTSTestSelectorAdapter（智能测试选择）
4. **Phase 4**: 实现SkyWalkingCallChainAdapter（动态分析）
5. **Phase 5**: 实现OpenAIAdapter（AI增强，可选）
6. **Phase 6**: 实现SkyWalkingAdapter（APM集成，可选）

每个适配器实现完成后，需要：
- 编写单元测试
- 编写集成测试
- 更新文档
- 代码审查
