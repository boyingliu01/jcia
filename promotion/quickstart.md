# JCIA 快速开始指南

## 5步快速上手JCIA

---

## 第一步：安装JCIA（2分钟）

### 方式一：使用pip安装（推荐）

```bash
# 基础安装
pip install jcia

# 验证安装
jcia --version
```

### 方式二：从源码安装

```bash
# 克隆仓库
git clone https://github.com/your-org/jcia.git
cd jcia

# 安装依赖
pip install -r requirements.txt

# 安装JCIA
pip install -e .

# 验证安装
jcia --version
```

### 方式三：使用Docker

```bash
# 拉取镜像
docker pull jcia/jcia:latest

# 运行分析
docker run -v /path/to/repo:/repo jcia/jcia analyze --repo-path /repo
```

### 常见问题

**Q: pip安装时出现权限错误？**

```bash
# 方案1：使用--user参数
pip install --user jcia

# 方案2：使用虚拟环境
python -m venv jcia-env
source jcia-env/bin/activate  # Windows: jcia-env\Scripts\activate
pip install jcia
```

---

## 第二步：基本配置（3分钟）

### 快速配置

在项目根目录创建 `.jcia.yaml` 配置文件：

```bash
# 创建配置文件
touch .jcia.yaml
```

复制以下基础配置：

```yaml
# =====================================
# JCIA 基础配置文件
# =====================================

# 项目信息
project:
  name: "my-java-project"
  language: "java"
  version: "1.0.0"

# 分析配置
analysis:
  # 最大调用深度（推荐5-10）
  max_depth: 8

  # 分析策略: fast/standard/detailed
  strategy: "standard"

  # 融合策略: bayesian/voting/weighted
  fusion_strategy: "weighted"

  # 是否包含测试代码
  include_tests: false

  # 排除模式（使用glob语法）
  exclude_patterns:
    - "*.md"
    - "*.txt"
    - "*.properties"
    - "**/test/**"
    - "**/target/**"
    - "**/build/**"

# 严重程度评估配置
severity:
  # 各维度权重（总和应为1.0）
  weights:
    depth: 0.20        # 调用深度
    scope: 0.25        # 影响范围
    criticality: 0.25  # 业务关键度
    sensitivity: 0.15  # 数据敏感性
    history: 0.15      # 历史缺陷

# 测试选择配置
test_selection:
  # 选择策略: all/starts/impact_based/hybrid
  strategy: "impact_based"

  # 覆盖率阈值（0.0-1.0）
  coverage_threshold: 0.8

  # 最大选择用例数
  max_tests: 200

# 报告配置
report:
  # 默认输出格式: html/json/markdown/csv/xml
  default_format: "html"

  # 报告输出目录
  output_dir: "reports/jcia"

  # 是否包含代码片段
  include_code_snippets: true

  # 是否包含建议措施
  include_recommendations: true

  # 是否生成趋势图
  include_trends: true

# 集成配置
integration:
  jenkins:
    enabled: false
    webhook_url: ""

  gitlab:
    enabled: false
    token: ""
    project_id: ""

  sonarqube:
    enabled: false
    url: ""
    token: ""

# 缓存配置
cache:
  enabled: true
  dir: ".jcia/cache"
  max_size: "1GB"
  ttl: "7d"

# 日志配置
logging:
  level: "INFO"  # DEBUG/INFO/WARNING/ERROR
  file: ".jcia/jcia.log"
  max_size: "10MB"
  max_files: 5
```

### 验证配置

```bash
# 检查配置是否正确
jcia config --validate

# 查看当前配置
jcia config --show

# 测试配置
jcia config --test
```

---

## 第三步：运行示例分析（5分钟）

### 场景1：分析最近一次提交

```bash
# 进入项目目录
cd /path/to/your-java-project

# 分析最近一次提交的影响
jcia analyze \
    --repo-path . \
    --from-commit HEAD~1 \
    --to-commit HEAD \
    --output-format html \
    --output-dir reports/

# 查看报告
open reports/impact_analysis.html  # macOS
# 或
xdg-open reports/impact_analysis.html  # Linux
# 或
start reports/impact_analysis.html  # Windows
```

### 场景2：分析特定提交范围

```bash
# 分析多个提交的影响
jcia analyze \
    --repo-path . \
    --from-commit abc1234 \
    --to-commit def5678 \
    --output-format html \
    --output-dir reports/
```

### 场景3：分析特定分支

```bash
# 比较两个分支的差异
jcia analyze \
    --repo-path . \
    --from-commit main \
    --to-commit feature/new-feature \
    --output-format html \
    --output-dir reports/
```

### 场景4：生成不同格式的报告

```bash
# 同时生成多种格式
jcia analyze \
    --repo-path . \
    --from-commit HEAD~1 \
    --to-commit HEAD \
    --output-formats html,json,markdown \
    --output-dir reports/
```

### 输出文件说明

```
reports/
├── impact_analysis.html       # HTML可视化报告
├── impact_analysis.json       # JSON格式数据
├── impact_analysis.md         # Markdown文档
├── impact_analysis.csv        # CSV表格数据
├── impact_analysis.xml        # XML格式
├── summary.json               # 分析摘要
├── recommendations.md         # 建议措施
└── charts/                   # 趋势图表
    ├── impact_trend.png
    ├── severity_distribution.png
    └── test_coverage.png
```

---

## 第四步：解读分析结果（5分钟）

### 1. 查看HTML报告

打开 `impact_analysis.html`，你会看到以下区域：

#### 概览区域
```
┌─────────────────────────────────────────────────────┐
│  分析概览                                            │
├─────────────────────────────────────────────────────┤
│  分析时间: 2024-01-15 14:30:25                       │
│  提交范围: abc1234 → def5678                         │
│  变更文件: 5个                                       │
│  变更方法: 12个                                      │
│  影响方法: 35个                                      │
│  最大深度: 6层                                       │
│  平均严重度: 6.5/10 (中)                              │
└─────────────────────────────────────────────────────┘
```

#### 变更详情
```
┌─────────────────────────────────────────────────────┐
│  变更文件列表                                        │
├─────────────────────────────────────────────────────┤
│  🔴 OrderService.java        严重度: 8.5 (高)        │
│     └─ createOrder()         新增方法               │
│     └─ processPayment()      修改: +15/-5 行        │
│                                                      │
│  🟡 UserController.java      严重度: 5.5 (中)        │
│     └─ login()               修改: +8/-2 行         │
│                                                      │
│  🟢 Utils.java                 严重度: 2.0 (低)        │
│     └─ formatDate()          修改: +3/-3 行         │
└─────────────────────────────────────────────────────┘
```

#### 影响分析
```
┌─────────────────────────────────────────────────────┐
│  影响分析                                            │
├─────────────────────────────────────────────────────┤
│  OrderService.createOrder() 的影响路径:              │
│                                                      │
│  Level 1: OrderService.createOrder() [变更点]        │
│      ↓                                               │
│  Level 2: PaymentService.process()                   │
│      ↓                                               │
│  Level 3: PaymentGateway.charge()                    │
│      ↓                                               │
│  Level 4: DatabaseService.update()                   │
│                                                      │
│  影响范围: 4个模块，12个方法                          │
│  关键路径: OrderService → PaymentService            │
│  风险等级: 🔴 高 (8.5/10)                             │
└─────────────────────────────────────────────────────┘
```

#### 建议措施
```
┌─────────────────────────────────────────────────────┐
│  建议措施                                            │
├─────────────────────────────────────────────────────┤
│  基于分析结果，我们建议采取以下措施:                  │
│                                                      │
│  🔴 高优先级:                                        │
│  1. 对 OrderService.createOrder() 进行全面单元测试    │
│  2. 执行支付流程的端到端测试                          │
│  3. 进行代码审查，特别关注事务处理逻辑                  │
│                                                      │
│  🟡 中优先级:                                        │
│  1. 验证 UserController.login() 的边界情况           │
│  2. 检查是否有相关的集成测试需要更新                    │
│                                                      │
│  🟢 低优先级:                                        │
│  1. 确认 Utils.formatDate() 的变更不会影响其他模块    │
│                                                      │
│  预计测试时间: 从4小时减少到1小时（节省75%）          │
└─────────────────────────────────────────────────────┘
```

### 2. 查看JSON报告

JSON报告适合程序处理，包含完整的数据：

```python
import json

# 读取JSON报告
with open('reports/impact_analysis.json', 'r') as f:
    report = json.load(f)

# 获取概览信息
print(f"分析时间: {report['summary']['analysis_time']}")
print(f"变更文件数: {report['summary']['changed_files']}")
print(f"影响方法数: {report['summary']['impacted_methods']}")

# 获取高风险变更
high_risk_changes = [
    change for change in report['changes']
    if change['severity']['score'] >= 7.0
]

print(f"\n高风险变更 ({len(high_risk_changes)}个):")
for change in high_risk_changes:
    print(f"  - {change['file']} ({change['severity']['level']})")

# 获取测试建议
test_recommendations = report.get('recommendations', {}).get('tests', [])
print(f"\n测试建议 ({len(test_recommendations)}条):")
for rec in test_recommendations:
    print(f"  - [{rec['priority']}] {rec['description']}")
```

### 3. 理解严重程度评级

```python
# 严重程度解读指南
def interpret_severity(score, dimensions):
    """
    解读严重程度评分

    评分维度：
    - depth (0-10): 调用深度评分
    - scope (0-10): 影响范围评分
    - criticality (0-10): 业务关键度
    - sensitivity (0-10): 数据敏感性
    - history (0-10): 历史缺陷评分
    """

    # 等级划分
    if score >= 9:
        level = "CRITICAL"
        emoji = "🔴"
        action = "必须进行全面测试和代码审查"
    elif score >= 7:
        level = "HIGH"
        emoji = "🟠"
        action = "建议进行全面测试"
    elif score >= 5:
        level = "MEDIUM"
        emoji = "🟡"
        action = "进行常规测试"
    elif score >= 3:
        level = "LOW"
        emoji = "🟢"
        action = "简单验证即可"
    else:
        level = "MINIMAL"
        emoji = "⚪"
        action = "可选验证"

    # 找出主要贡献维度
    main_factors = [
        (name, value) for name, value in dimensions.items()
        if value >= 7
    ]
    main_factors.sort(key=lambda x: x[1], reverse=True)

    report = f"""
{emoji} 严重程度: {level} ({score}/10)

📊 维度评分:
"""
    for name, value in dimensions.items():
        bar = "█" * int(value) + "░" * (10 - int(value))
        report += f"  {name:15} [{bar}] {value}/10\n"

    report += f"\n🔍 主要影响因素:\n"
    if main_factors:
        for name, value in main_factors[:3]:
            report += f"  • {name}: {value}/10\n"
    else:
        report += "  • 无明显高风险因素\n"

    report += f"\n💡 建议措施: {action}\n"

    return report


# 使用示例
dimensions = {
    "depth": 8.0,
    "scope": 9.0,
    "criticality": 8.5,
    "sensitivity": 6.0,
    "history": 7.5
}
score = sum(v * w for v, w in zip(dimensions.values(), [0.2, 0.25, 0.25, 0.15, 0.15]))
print(interpret_severity(score, dimensions))
```

---

## 第五步：下一步行动

### 学习路径建议

```
第1周：基础使用
├── 完成本快速开始指南的所有步骤
├── 在自己的项目上运行JCIA分析
├── 阅读生成的报告，理解各项指标
└── 记录使用过程中遇到的问题

第2周：进阶配置
├── 学习配置文件的高级选项
├── 根据项目特点调整分析参数
├── 尝试不同的融合策略
└── 集成到本地开发流程

第3周：团队集成
├── 在团队中分享使用经验
├── 协助配置CI/CD集成
├── 建立团队的分析报告模板
└── 收集反馈，持续改进

第4周：高级应用
├── 开发自定义分析插件
├── 集成到现有的监控体系
├── 建立长期的趋势分析
└── 培养团队其他成员成为JCIA专家
```

### 推荐资源

**官方文档：**
- [完整用户手册](https://github.com/your-org/jcia/blob/main/docs/)
- [API参考文档](https://github.com/your-org/jcia/blob/main/docs/api.md)
- [配置参考](https://github.com/your-org/jcia/blob/main/docs/configuration.md)

**视频教程：**
- [JCIA入门视频（15分钟）](https://github.com/your-org/jcia#tutorials)
- [高级配置教程（30分钟）](https://github.com/your-org/jcia#tutorials)
- [CI/CD集成实战（45分钟）](https://github.com/your-org/jcia#tutorials)

**社区支持：**
- GitHub Issues: https://github.com/your-org/jcia/issues
- 邮箱：jcia-dev@example.org

### 常见问题速查

**Q: 如何更新到最新版本？**
```bash
pip install --upgrade jcia
```

**Q: 如何卸载JCIA？**
```bash
pip uninstall jcia
```

**Q: 分析失败如何排查？**
```bash
# 启用调试模式
jcia analyze --repo-path . --verbose --debug

# 查看日志
tail -f .jcia/jcia.log
```

**Q: 如何获取帮助？**
```bash
# 查看帮助
jcia --help

# 查看子命令帮助
jcia analyze --help
jcia test --help
jcia config --help
```

---

## 恭喜！

您已经完成了JCIA快速开始指南的所有步骤。现在您可以：

1. ✅ 在自己的项目中运行JCIA分析
2. ✅ 理解分析报告的各项指标
3. ✅ 配置适合您项目的参数
4. ✅ 集成到您的开发工作流

**下一步建议：**

- 在实际项目中试用JCIA
- 与团队分享您的使用经验
- 探索更多高级功能
- 参与JCIA社区，提供反馈

**需要帮助？**

- 📧 邮箱：jcia-dev@example.org
- 🐛 Issues：https://github.com/your-org/jcia/issues
- 📖 文档：https://github.com/your-org/jcia

---

*JCIA - 让代码变更的影响范围一目了然*
