# 任务列表

## 进行中的任务

- [ ] 远程调用实体设计
  - 描述：设计 RemoteCallNode、RemoteEndpoint 实体类
  - 优先级：高
  - 预估时间：4h
  - TDD：先写测试，再实现

## 待办任务

### Phase 1: 实体与接口（基础层）

- [ ] RemoteCallNode 实体测试
  - 描述：编写 RemoteCallNode 的单元测试
  - 优先级：高
  - 预估时间：1h

- [ ] RemoteCallNode 实体实现
  - 描述：实现 RemoteCallNode 实体类
  - 优先级：高
  - 预估时间：2h
  - 依赖：测试通过

- [ ] RemoteEndpoint 实体测试
  - 描述：编写 RemoteEndpoint 的单元测试
  - 优先级：高
  - 预估时间：1h

- [ ] RemoteEndpoint 实体实现
  - 描述：实现 RemoteEndpoint 实体类
  - 优先级：高
  - 预估时间：2h
  - 依赖：测试通过

- [ ] RemoteCallAnalyzer 接口定义
  - 描述：定义 RemoteCallAnalyzer 抽象接口
  - 优先级：高
  - 预估时间：2h

### Phase 2: 远程调用适配器（适配层）

- [ ] DubboAnalyzerAdapter 测试
  - 描述：编写 Dubbo RPC 检测的测试用例
  - 优先级：高
  - 预估时间：3h

- [ ] DubboAnalyzerAdapter 实现
  - 描述：实现 Dubbo 远程调用检测
  - 优先级：高
  - 预估时间：5h
  - 依赖：测试通过

- [ ] FeignAnalyzerAdapter 测试
  - 描述：编写 Feign 客户端检测的测试用例
  - 优先级：高
  - 预估时间：3h

- [ ] FeignAnalyzerAdapter 实现
  - 描述：实现 Feign HTTP 调用检测
  - 优先级：高
  - 预估时间：5h
  - 依赖：测试通过

- [ ] HttpClientAnalyzerAdapter 测试
  - 描述：编写 RestTemplate/OkHttp 检测的测试用例
  - 优先级：中
  - 预估时间：2h

- [ ] HttpClientAnalyzerAdapter 实现
  - 描述：实现 HTTP Client 调用检测
  - 优先级：中
  - 预估时间：4h
  - 依赖：测试通过

- [ ] MQListenerAnalyzerAdapter 测试
  - 描述：编写消息队列监听器检测的测试用例
  - 优先级：中
  - 预估时间：2h

- [ ] MQListenerAnalyzerAdapter 实现
  - 描述：实现 MQ 监听器调用检测
  - 优先级：中
  - 预估时间：4h
  - 依赖：测试通过

### Phase 3: 服务层融合（领域层）

- [ ] AnalysisFusionService 测试
  - 描述：编写分析融合服务的测试用例
  - 优先级：高
  - 预估时间：3h

- [ ] AnalysisFusionService 实现
  - 描述：实现多源分析结果融合
  - 优先级：高
  - 预估时间：5h
  - 依赖：测试通过

- [ ] SeverityEnhancer 测试
  - 描述：编写严重度增强器的测试用例
  - 优先级：中
  - 预估时间：2h

- [ ] SeverityEnhancer 实现
  - 描述：实现远程调用严重度评级增强
  - 优先级：中
  - 预估时间：3h
  - 依赖：测试通过

### Phase 4: 集成与验证

- [ ] 端到端集成测试
  - 描述：编写完整的分析流程集成测试
  - 优先级：高
  - 预估时间：4h

- [ ] 真实项目验证
  - 描述：在 Jenkins 等开源项目验证分析结果
  - 优先级：中
  - 预估时间：4h

- [ ] 文档更新
  - 描述：更新 README、CLAUDE.md、API 文档
  - 优先级：中
  - 预估时间：2h

- [ ] 性能基准测试
  - 描述：对比分析前后的性能变化
  - 优先级：低
  - 预估时间：2h

## 已完成任务

（待填充）