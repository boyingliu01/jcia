# 实现计划

## 技术方案

### 架构设计

采用 **六边形架构（Hexagonal Architecture）**，保持现有架构风格：

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI/API                              │  应用层
├─────────────────────────────────────────────────────────────┤
│                     Use Cases                                │
│   AnalyzeImpactUseCase | GenerateTestsUseCase               │
├─────────────────────────────────────────────────────────────┤
│                     Services                                 │  领域层
│   CallChainBuilder | ImpactAnalysisService                  │
│   RemoteCallAnalyzer | AnalysisFusionService                │
├─────────────────────────────────────────────────────────────┤
│                     Entities                                 │  核心层
│   ChangeSet | ImpactGraph | RemoteCallNode | SeverityRating │
├─────────────────────────────────────────────────────────────┤
│                     Interfaces                               │  契约层
│   RemoteCallAnalyzer | FusionEngine | SeverityCalculator    │
├─────────────────────────────────────────────────────────────┤
│                     Adapters                                 │  适配层
│   DubboAnalyzer | FeignAnalyzer | HttpClientAnalyzer        │
│   CodeQLAdapter | SkyWalkingAdapter | FusionAdapter         │
└─────────────────────────────────────────────────────────────┘
```

### 技术栈

- **核心语言**: Python 3.10+
- **代码解析**: tree-sitter-java（增量解析）
- **静态分析**: 自研 + CodeQL（可选）
- **运行时分析**: SkyWalking API（可选）
- **测试框架**: pytest + pytest-asyncio
- **代码质量**: Ruff + Pyright + Bandit
- **依赖管理**: uv / pip

## 实现步骤

### 步骤1：远程调用实体设计（1天）

- 任务描述：设计 RemoteCallNode、RemoteEndpoint 等实体
- 预估时间：4h
- 依赖关系：无
- TDD流程：先写实体测试

### 步骤2：远程调用分析接口定义（1天）

- 任务描述：定义 RemoteCallAnalyzer 接口契约
- 预估时间：4h
- 依赖关系：步骤1完成
- TDD流程：先写接口测试

### 步骤3：Dubbo RPC 分析适配器（2天）

- 任务描述：实现 Dubbo 远程调用检测
- 预估时间：8h
- 依赖关系：步骤2完成
- TDD流程：
  - 编写测试用例（各种 Dubbo 注解场景）
  - 实现适配器
  - 验证检测准确率

### 步骤4：Feign HTTP 分析适配器（2天）

- 任务描述：实现 Feign 客户端调用检测
- 预估时间：8h
- 依赖关系：步骤2完成
- TDD流程：同步骤3

### 步骤5：消息队列调用分析（2天）

- 任务描述：实现 MQ 监听器调用检测
- 预估时间：8h
- 依赖关系：步骤2完成
- 支持：RabbitMQ、Kafka、RocketMQ

### 步骤6：分析融合服务（2天）

- 任务描述：实现 AnalysisFusionService
- 预估时间：8h
- 依赖关系：步骤3-5完成
- 功能：合并静态、远程、运行时分析结果

### 步骤7：严重度评级增强（1天）

- 任务描述：增强 SeverityCalculator 支持远程调用因素
- 预估时间：4h
- 依赖关系：步骤6完成

### 步骤8：集成测试与文档（1天）

- 任务描述：端到端测试、更新文档
- 预估时间：4h
- 依赖关系：全部步骤完成

## 风险评估

### 风险1：远程调用检测准确率不足

- 概率：中
- 影响：高
- 缓解措施：使用多源验证（静态+运行时），编写大量测试用例

### 集险2：跨服务边界标记复杂

- 概率：中
- 影响：中
- 缓解措施：设计清晰的服务边界模型，参考 SkyWalking 数据

### 风险3：性能下降

- 概率：低
- 影响：中
- 缓解措施：增量分析、结果缓存、并行处理

## 验证方法

1. **单元测试**：每个适配器覆盖率 ≥ 85%
2. **集成测试**：端到端分析流程测试
3. **真实项目验证**：在 Jenkins 等开源项目验证
4. **性能基准**：对比分析时间变化