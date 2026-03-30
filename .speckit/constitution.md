# 项目宪法

## 项目概述

项目名称：JCIA (Java Code Impact Analyzer)

JCIA 是一个用于分析 Java 项目中代码变更影响范围的工具。它识别受影响的类和方法，智能选择测试案例，并执行回归测试。采用 Clean Architecture（六边形架构）原则实现。

## 核心原则

### 1. 开发方法论

- **SDD (Specification-Driven Development)**: 先规格，后实现
- **TDD (Test-Driven Development)**: 先测试，后代码
- **Clean Architecture**: 六边形分层架构，依赖规则
- **Clean Code**: 可读性、可维护性优先
- **SOLID**: 面向对象设计原则

### 2. 代码规范

- 命名清晰表达意图（camelCase/snake_case）
- 函数单一职责，短小精悍
- 避免重复代码 (DRY)
- 注释解释"为什么"而非"是什么"
- 遵循 Python 最佳实践（PEP 8 + Ruff 规则）

### 3. 工程要求

- 所有提交必须通过 Ruff Lint 检查
- 所有提交必须有测试覆盖
- 新功能必须先写测试（TDD）
- 代码审查必须通过检查清单
- 童子军规则：每次提交改善代码质量

## 架构原则

### 分层结构

```
Entities（核心领域）→ Interfaces（抽象契约）→ Services（领域逻辑）→ Use Cases（应用编排）→ Adapters（外部集成）
```

### 依赖规则

- 依赖必须指向内层
- Entities 不依赖任何外部模块
- Services 只依赖 Entities
- Use Cases 依赖接口，不直接依赖适配器
- Adapters 作为外部系统的桥梁

## 质量标准

- 代码覆盖率：≥ 80%（Entities ≥ 95%, Services ≥ 85%, Adapters ≥ 75%）
- Ruff 所有规则必须通过
- Pyright 类型检查通过
- 所有测试必须通过
- 无已知 Bug 合并到主分支

## 核心功能

### 已实现功能

1. Git 变更分析（PyDriller）
2. 方法调用链分析（静态分析 + 反射检测）
3. 影响范围评估（多维度严重度评级）
4. 测试选择策略（STARTS、IMPACT_BASED、HYBRID）
5. 回归测试执行（Maven Surefire）
6. 报告生成（JSON、HTML、Markdown）

### 待完善功能

1. 远程调用分析（RPC、HTTP、消息队列）
2. CodeQL 语义分析集成
3. 运行时调用链分析（SkyWalking）
4. 多分析源融合引擎
5. AI 测试生成优化