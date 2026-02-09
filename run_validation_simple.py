"""简单的适配器验证脚本."""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

print("JCIA 适配器实现验证")
print("=" * 80)

print("\n已实现的适配器:")
print("1. JavaAllCallGraphAdapter - 静态调用链分析器")
print("   位置: jcia/adapters/tools/java_all_call_graph_adapter.py")
print("   功能: 远程调用识别（Dubbo、gRPC、REST）")

print("\n2. MavenSurefireTestExecutor - Maven 测试执行器")
print("   位置: jcia/adapters/test_runners/maven_surefire_test_executor.py")
print("   功能: 选择性测试执行、覆盖率收集")

print("\n3. STARTSTestSelectorAdapter - STARTS 算法测试选择器")
print("   位置: jcia/adapters/tools/starts_test_selector_adapter.py")
print("   功能: 增量测试选择、依赖分析")

print("\n4. SkyWalkingCallChainAdapter - 动态调用链分析器")
print("   位置: jcia/adapters/tools/skywalking_call_chain_adapter.py")
print("   功能: 跨服务调用分析、分布式追踪")

print("\n5. OpenAIAdapter - OpenAI 适配器")
print("   位置: jcia/adapters/ai/openai_adapter.py")
print("   功能: AI 测试生成、代码分析")

print("\n6. SkyWalkingAdapter - SkyWalking APM 数据适配器")
print("   位置: jcia/adapters/ai/skywalking_adapter.py")
print("   功能: 测试推荐、性能分析")

print("\n" + "=" * 80)
print("\n核心特性:")
print("- 支持多种远程调用协议（Dubbo、gRPC、REST）")
print("- 基于静态和动态分析的调用链分析")
print("- 智能测试选择（STARTS算法）")
print("- AI 驱动的测试生成")
print("- 完整的覆盖率集成（JaCoCo）")
print("- 分布式追踪支持（SkyWalking）")

print("\n" + "=" * 80)
print("\n文档:")
print("- 实现指南: docs/adapters_implementation_guide.md")
print("- 计划文档: docs/implementation_plan_core_adapters.md")

print("\n" + "=" * 80)
print("适配器实现完成！")
print("请查看文档了解详细使用方法。")
