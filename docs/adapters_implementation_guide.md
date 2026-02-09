# JCIA 适配器实现说明

## 概述

本项目实现了 JCIA (Java Code Impact Analyzer) 的核心适配器，用于分析 Java 代码变更影响、智能选择测试用例和生成测试代码。

## 已实现的适配器

### 1. JavaAllCallGraphAdapter - 静态调用链分析器

**功能**：
- 基于 java-all-call-graph 的静态调用链分析
- 远程调用识别（Dubbo、gRPC、REST、Feign）
- 服务拓扑构建
- 注解解析

**位置**：`jcia/adapters/tools/java_all_call_graph_adapter.py`

**使用示例**：
```python
from jcia.adapters.tools.java_all_call_graph_adapter import JavaAllCallGraphAdapter

adapter = JavaAllCallGraphAdapter(repo_path="/path/to/java/project")

# 分析上游调用
upstream = adapter.analyze_upstream("com.example.UserService.getUser", max_depth=5)

# 分析下游调用
downstream = adapter.analyze_downstream("com.example.UserService.getUser", max_depth=5)

# 构建服务拓扑
topology = adapter.build_service_topology()
```

**远程调用识别**：
- **Dubbo**: 通过 `@Reference` 和 `@DubboService` 注解识别
- **gRPC**: 通过 Stub 类和 gRPC 特定方法识别
- **REST**: 通过 RestTemplate、WebClient 调用识别
- **Feign**: 通过 `@FeignClient` 注解识别

---

### 2. MavenSurefireTestExecutor - Maven 测试执行器

**功能**：
- 选择性测试执行
- JaCoCo 覆盖率收集
- 测试结果解析（Surefire XML）
- 增量测试执行

**位置**：`jcia/adapters/test_runners/maven_surefire_test_executor.py`

**使用示例**：
```python
from jcia.adapters.maven.maven_adapter import MavenAdapter
from jcia.adapters.test_runners.maven_surefire_test_executor import (
    MavenSurefireTestExecutor,
)

# 初始化 Maven 适配器
maven_adapter = MavenAdapter(project_path="/path/to/maven/project")

# 初始化测试执行器
executor = MavenSurefireTestExecutor(
    project_path="/path/to/maven/project",
    maven_adapter=maven_adapter,
)

# 执行所有测试
result = executor.execute_tests()

# 执行选定测试
from jcia.core.entities.test_case import TestCase

test_cases = [
    TestCase(
        class_name="com.example.UserServiceTest",
        method_name="testGetUser",
        test_type=TestType.UNIT,
    )
]
result = executor.execute_tests(test_cases=test_cases)

# 执行测试并收集覆盖率
result = executor.execute_with_coverage(test_cases=test_cases)
print(f"覆盖率: {result.coverage_percent:.2f}%")

# 获取覆盖率报告
coverage = executor.get_coverage_report(project_path="/path/to/maven/project")
```

---

### 3. STARTSTestSelectorAdapter - STARTS 算法测试选择器

**功能**：
- 基于 STARTS 算法的增量测试选择
- 测试-代码映射分析
- 类依赖关系分析
- 变更传播分析

**位置**：`jcia/adapters/tools/starts_test_selector_adapter.py`

**使用示例**：
```python
from jcia.adapters.maven.maven_adapter import MavenAdapter
from jcia.adapters.tools.starts_test_selector_adapter import (
    STARTSTestSelectorAdapter,
)

# 初始化 Maven 适配器
maven_adapter = MavenAdapter(project_path="/path/to/maven/project")

# 初始化 STARTS 选择器
selector = STARTSTestSelectorAdapter(
    project_path="/path/to/maven/project",
    maven_adapter=maven_adapter,
)

# 选择受影响的测试
changed_methods = ["com.example.UserService.getUser"]
selected_tests = selector.select_tests(
    changed_methods=changed_methods,
    project_path="/path/to/maven/project",
)

# 获取测试统计
stats = selector.get_test_statistics()
print(f"测试类数: {stats['total_test_classes']}")
print(f"缓存大小: {stats['cache_size']}")
```

---

### 4. SkyWalkingCallChainAdapter - 动态调用链分析器

**功能**：
- 基于 SkyWalking 分布式追踪的动态调用链分析
- 跨服务调用分析
- Dubbo 调用识别
- 服务拓扑获取

**位置**：`jcia/adapters/tools/skywalking_call_chain_adapter.py`

**使用示例**：
```python
from jcia.adapters.tools.skywalking_call_chain_adapter import (
    SkyWalkingCallChainAdapter,
)

# 初始化 SkyWalking 适配器
adapter = SkyWalkingCallChainAdapter(
    oap_server="http://localhost:12800",
    api_token="your-token",  # 可选
    time_range=7,  # 天
)

# 分析上游调用（基于实际追踪数据）
upstream = adapter.analyze_upstream("com.example.UserService.getUser", max_depth=5)

# 分析下游调用
downstream = adapter.analyze_downstream("com.example.UserService.getUser", max_depth=5)

# 构建完整调用图
full_graph = adapter.build_full_graph()

# 获取服务拓扑
topology = adapter.get_service_topology()
```

**跨服务调用支持**：
- 通过 SkyWalking 的 GraphQL API 获取分布式追踪数据
- 使用 TraceID 关联跨服务调用
- 识别同步/异步调用
- 支持多种调用类型（Dubbo、gRPC、REST、数据库、消息队列）

---

### 5. OpenAIAdapter - OpenAI 适配器

**功能**：
- 使用 OpenAI API 生成测试用例
- 为未覆盖代码生成测试
- 代码分析
- 测试用例优化

**位置**：`jcia/adapters/ai/openai_adapter.py`

**使用示例**：
```python
from jcia.adapters.ai.openai_adapter import OpenAIAdapter
from jcia.core.interfaces.ai_service import TestGenerationRequest

# 初始化 OpenAI 适配器
adapter = OpenAIAdapter(
    api_key="your-openai-api-key",
    model="gpt-4-turbo-preview",
)

# 生成测试用例
request = TestGenerationRequest(
    target_classes=["com.example.UserService"],
    code_snippets={
        "com.example.UserService": """
public class UserService {
    public User getUser(String id) {
        // 实现代码
    }
}
"""
    },
    requirements="生成覆盖正常和异常情况的测试",
)

response = adapter.generate_tests(
    request=request,
    project_path="/path/to/project",
)

for test_case in response.test_cases:
    print(f"测试类: {test_case.class_name}")
    print(f"代码:\n{test_case.metadata.get('test_code', '')}")

# 为未覆盖代码生成测试
coverage_data = {
    "classes": [
        {
            "name": "com.example.UserService",
            "line_coverage": 50,
            "lines": [1, 0, 1, 1, 0],  # 0 = 未覆盖
        }
    ]
}

response = adapter.generate_for_uncovered(
    coverage_data=coverage_data,
    project_path="/path/to/project",
)

# 优化测试用例
refined_test = adapter.refine_test(
    test_case=test_case,
    feedback="需要增加边界条件测试",
    project_path="/path/to/project",
)

# 分析代码
from jcia.core.interfaces.ai_service import CodeAnalysisRequest

analysis_request = CodeAnalysisRequest(
    code="public class UserService {\n    // ...\n}",
    analysis_type="quality",
)

analysis_response = adapter.analyze_code(analysis_request)
for finding in analysis_response.findings:
    print(f"问题: {finding['content']}")

for suggestion in analysis_response.suggestions:
    print(f"建议: {suggestion}")
```

---

### 6. SkyWalkingAdapter - SkyWalking APM 数据适配器

**功能**：
- 基于 APM 数据的测试推荐
- 性能瓶颈分析
- 异常追踪
- 服务健康状态查询

**位置**：`jcia/adapters/ai/skywalking_adapter.py`

**使用示例**：
```python
from jcia.adapters.ai.skywalking_adapter import SkyWalkingAdapter

# 初始化 SkyWalking 适配器
adapter = SkyWalkingAdapter(
    oap_server="http://localhost:12800",
    api_token="your-token",  # 可选
)

# 基于变更推荐测试
changed_methods = ["com.example.UserService.getUser"]
recommendations = adapter.recommend_tests(
    changed_methods=changed_methods,
    time_range=7,  # 天
)

for rec in recommendations:
    print(f"端点: {rec['endpoint']}")
    print(f"优先级: {rec['test_priority']}")
    print(f"原因: {rec['reason']}")
    for test in rec.get('suggested_tests', []):
        print(f"  建议: {test}")

# 分析异常
exceptions = adapter.analyze_exceptions(
    service_name="user-service",
    time_range=7,
)

for exc in exceptions:
    print(f"异常类型: {exc['exception_type']}")
    print(f"消息: {exc['message']}")
    print(f"堆栈: {exc['stack_trace']}")

# 获取服务健康状态
health = adapter.get_service_health(service_names=["user-service", "order-service"])
for svc in health['services']:
    status = svc['healthCheck'].get('status', 'UNKNOWN')
    print(f"服务: {svc['label']} - 状态: {status}")

# 分析性能趋势
trends = adapter.analyze_performance_trends(
    service_name="user-service",
    time_range=30,  # 天
)

print(f"服务: {trends['service_name']}")
print(f"指标点数: {len(trends['metrics'])}")
```

---

## 测试验证

### 运行验证脚本

```bash
# 使用 Jenkins 工作空间路径验证所有适配器
python run_jenkins_validation.py --jenkins-workspace /path/to/project

# 使用当前目录验证
python run_jenkins_validation.py

# 查看帮助
python run_jenkins_validation.py --help
```

### 验证报告

验证完成后，会在 `validation_report/` 目录生成以下报告：

- `validation_report.json` - JSON 格式的详细验证结果
- `validation_report.md` - Markdown 格式的验证报告
- `validation_report.html` - HTML 格式的可视化报告

---

## 依赖要求

### Python 依赖

```bash
pip install requests  # HTTP 客户端（用于 SkyWalking 和 OpenAI 适配器）
pip install openai     # OpenAI API 客户端（可选）
```

### Java 工具

- **Java 8+** - 运行 JACG
- **Maven 3.2+** - Maven Surefire 和 JaCoCo 插件
- **java-all-call-graph** - 自动下载或手动安装

### 外部服务

- **SkyWalking OAP Server** (可选) - 用于动态调用链分析
- **OpenAI API** (可选) - 用于 AI 测试生成

### 环境变量

```bash
# OpenAI API 配置（可选）
export OPENAI_API_KEY="sk-..."

# SkyWalking 配置（可选）
export SW_OAP_SERVER="http://localhost:12800"
export SW_TOKEN="your-token"
```

---

## 配置文件

### jcia.yaml

```yaml
# 调用链分析器
call_chain:
  type: static  # static | dynamic | hybrid
  max_depth: 10
  enable_remote_call_detection: true

# 测试执行
test_execution:
  maven:
    surefire_version: "2.22.2"
    jacoco_version: "0.8.11"
    timeout: 300  # 秒

# STARTS 选择器
starts:
  version: "1.4"
  enable_caching: true

# SkyWalking
skywalking:
  oap_server: "http://localhost:12800"
  api_token: ""  # 可选
  time_range_days: 7
  timeout: 30  # 秒

# OpenAI
openai:
  api_key: ""  # 建议使用环境变量
  model: "gpt-4-turbo-preview"
  temperature: 0.7
  max_tokens: 4096
  timeout: 60  # 秒
```

---

## 集成到 JCIA

### 在使用用例中使用

```python
from jcia.core.use_cases.analyze_impact import AnalyzeImpactUseCase

# 使用 JavaAllCallGraphAdapter
from jcia.adapters.tools.java_all_call_graph_adapter import JavaAllCallGraphAdapter

call_chain_analyzer = JavaAllCallGraphAdapter(repo_path="/path/to/project")

use_case = AnalyzeImpactUseCase(
    change_analyzer=PyDrillerAdapter(repo_path="/path/to/project"),
    call_chain_analyzer=call_chain_analyzer,
)

# 执行影响分析
response = use_case.execute(request)
```

### CLI 集成

```bash
# 使用特定适配器
jcia analyze --repo-path /path/to/project --call-chain-analyzer java-all-call-graph

# 使用动态调用链分析
jcia analyze --repo-path /path/to/project --call-chain-analyzer skywalking
```

---

## 故障排除

### 常见问题

#### 1. JavaAllCallGraphAdapter 失败

**问题**: `RuntimeError: Cannot download JACG`

**解决方案**:
- 检查网络连接
- 手动下载 JACG JAR: https://github.com/bytedance/java-all-call-graph/releases
- 设置环境变量: `JACG_JAR=/path/to/jacg.jar`

#### 2. MavenSurefireTestExecutor 测试失败

**问题**: `Maven test execution failed`

**解决方案**:
- 检查 `pom.xml` 是否存在
- 确保项目可以正常构建: `mvn clean compile`
- 检查 Java 版本是否兼容

#### 3. SkyWalking 适配器连接失败

**问题**: `RuntimeError: Failed to execute GraphQL query`

**解决方案**:
- 确认 OAP Server 是否运行
- 检查 OAP Server 地址是否正确
- 检查防火墙设置
- 使用正确的 API Token

#### 4. OpenAIAdapter API 调用失败

**问题**: `RuntimeError: OpenAI API error`

**解决方案**:
- 确认 API Key 是否有效
- 检查账户余额
- 确认网络连接
- 考虑使用代理或备用端点

---

## 性能优化

### 缓存策略

- **JavaAllCallGraphAdapter**: 分析结果缓存
- **STARTSTestSelectorAdapter**: 类依赖和测试-代码映射缓存
- **SkyWalkingCallChainAdapter**: GraphQL 查询结果缓存

### 并发处理

- MavenSurefireTestExecutor 支持并行测试执行
- 多个分析器可以并发初始化

---

## 贡献

欢迎贡献！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

---

## 许可证

MIT License

---

## 联系方式

- 问题反馈: [GitHub Issues](https://github.com/your-org/jcia/issues)
- 邮箱: support@example.com

---

## 更新日志

### v1.0.0 (2026-02-08)

**新增**:
- 实现 JavaAllCallGraphAdapter
- 实现 MavenSurefireTestExecutor
- 实现 STARTSTestSelectorAdapter
- 实现 SkyWalkingCallChainAdapter
- 实现 OpenAIAdapter
- 实现 SkyWalkingAdapter
- 添加验证脚本和报告生成

**修复**:
- 修复远程调用识别逻辑
- 修复覆盖率报告解析

**文档**:
- 添加详细的使用文档
- 添加故障排除指南
