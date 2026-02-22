# JCIA 常见问题解答（FAQ）

---

## 目录

1. [安装问题](#一安装问题)
2. [使用问题](#二使用问题)
3. [性能问题](#三性能问题)
4. [集成问题](#四集成问题)
5. [配置问题](#五配置问题)
6. [故障排查](#六故障排查)

---

## 一、安装问题

### Q1: JCIA支持哪些操作系统？

**A:** JCIA支持以下操作系统：

| 操作系统 | 版本要求 | 支持状态 |
|---------|---------|---------|
| Windows | Windows 10/11, Windows Server 2016+ | 完全支持 |
| macOS | macOS 10.15 (Catalina) 及以上 | 完全支持 |
| Linux | Ubuntu 18.04+, CentOS 7+, Debian 9+ | 完全支持 |

**注意：** 需要Python 3.8或更高版本。

---

### Q2: 安装时出现"pip不是内部或外部命令"错误？

**A:** 这是因为Python的Scripts目录没有添加到系统PATH中。

**解决方案：**

**Windows:**
```cmd
# 方法1：使用Python启动器
python -m pip install jcia

# 方法2：添加PATH（以Python 3.11为例）
setx PATH "%PATH%;C:\Users\YourName\AppData\Local\Programs\Python\Python311\Scripts"
# 重新打开命令提示符
```

**macOS/Linux:**
```bash
# 方法1：使用python -m pip
python3 -m pip install jcia

# 方法2：添加PATH（添加到~/.bashrc或~/.zshrc）
export PATH="$PATH:$HOME/.local/bin"
source ~/.bashrc  # 或 source ~/.zshrc
```

---

### Q3: 安装时出现依赖冲突怎么办？

**A:** 依赖冲突通常是因为现有环境中已安装了不同版本的依赖包。

**解决方案：**

**方法1：使用虚拟环境（推荐）**
```bash
# 创建虚拟环境
python -m venv jcia-env

# 激活虚拟环境
# Windows:
jcia-env\Scripts\activate
# macOS/Linux:
source jcia-env/bin/activate

# 安装JCIA
pip install jcia
```

**方法2：使用--force-reinstall**
```bash
pip install --force-reinstall jcia
```

**方法3：使用conda环境**
```bash
conda create -n jcia python=3.11
conda activate jcia
pip install jcia
```

---

### Q4: 从源码安装时出现"No module named 'jcia'"？

**A:** 这是因为没有正确安装，只是下载了源码。

**正确的源码安装方式：**

```bash
# 克隆仓库
git clone https://github.com/your-org/jcia.git
cd jcia

# 方法1：使用pip安装（推荐）
pip install -e .

# 方法2：使用setup.py
python setup.py install

# 方法3：开发模式（修改代码后立即生效）
pip install -e ".[dev]"
```

---

## 二、使用问题

### Q1: 如何分析特定提交范围的影响？

**A:** 使用`--from-commit`和`--to-commit`参数指定提交范围。

**基本用法：**

```bash
# 分析两个commit之间的变更
jcia analyze \
    --repo-path /path/to/repo \
    --from-commit abc1234 \
    --to-commit def5678

# 分析最近的N个commit
jcia analyze \
    --repo-path /path/to/repo \
    --from-commit HEAD~5 \
    --to-commit HEAD

# 分析单个commit
jcia analyze \
    --repo-path /path/to/repo \
    --from-commit HEAD~1 \
    --to-commit HEAD
```

**高级用法：**

```bash
# 分析特定分支的变更
jcia analyze \
    --repo-path /path/to/repo \
    --from-commit main \
    --to-commit feature/new-feature \
    --branch feature/new-feature

# 排除特定文件
jcia analyze \
    --repo-path /path/to/repo \
    --from-commit HEAD~3 \
    --to-commit HEAD \
    --exclude "*.md,*.txt,*.properties"
```

---

### Q2: 如何生成不同格式的报告？

**A:** 使用`--output-format`参数指定报告格式。

**支持的格式：**

```bash
# HTML格式（推荐，可视化效果好）
jcia analyze --repo-path . --output-format html --output report.html

# JSON格式（适合程序处理）
jcia analyze --repo-path . --output-format json --output report.json

# Markdown格式（适合文档）
jcia analyze --repo-path . --output-format markdown --output report.md

# CSV格式（适合表格分析）
jcia analyze --repo-path . --output-format csv --output report.csv

# XML格式（适合与现有工具集成）
jcia analyze --repo-path . --output-format xml --output report.xml
```

**同时输出多种格式：**

```bash
# 一次分析，生成多种格式报告
jcia analyze \
    --repo-path . \
    --from-commit HEAD~2 \
    --to-commit HEAD \
    --output-formats html,json,markdown \
    --output-dir reports/
```

---

### Q3: 如何解释分析报告中的严重程度评级？

**A:** JCIA使用6维度评估系统计算严重程度。

**严重程度等级：**

| 等级 | 分数 | 含义 | 建议措施 |
|------|------|------|----------|
| 🔴 **极高** | 9-10 | 核心业务逻辑变更，影响面广 | 必须全面测试，代码审查 |
| 🟠 **高** | 7-8 | 重要功能变更，影响多个模块 | 重点测试，关注边界情况 |
| 🟡 **中** | 5-6 | 一般功能变更，影响范围有限 | 常规测试即可 |
| 🟢 **低** | 3-4 | 工具类/配置类变更 | 简单验证 |
| ⚪ **极低** | 1-2 | 文档/注释变更 | 可选验证 |

**6维度评估详情：**

```
┌─────────────────────────────────────────────────────────────┐
│                    严重程度评估详情                          │
├─────────────────────────────────────────────────────────────┤
│ 综合评分: 7.5/10 (高)                                        │
├─────────────────────────────────────────────────────────────┤
│ 维度评分明细:                                                │
│                                                             │
│ 调用深度    ████████░░  8.0/10 (权重20%) 影响较大           │
│ 影响范围    █████████░  9.0/10 (权重25%) 影响多个模块        │
│ 业务关键度  ████████░░  8.0/10 (权重25%) 核心业务逻辑        │
│ 数据敏感性  ██████░░░░  6.0/10 (权重15%) 涉及用户数据        │
│ 历史缺陷    ███████░░░  7.0/10 (权重15%) 该区域曾有bug      │
├─────────────────────────────────────────────────────────────┤
│ 关键影响路径:                                                │
│ UserController.login() → AuthService.authenticate()        │
│                       → UserService.validateUser()           │
│                       → Database.updateLastLogin()           │
└─────────────────────────────────────────────────────────────┘
```

---

### Q4: 如何自定义分析参数？

**A:** 通过配置文件或命令行参数自定义。

**方式1：配置文件（推荐）**

创建 `.jcia.yaml` 文件：

```yaml
# JCIA 配置文件

# 分析配置
analysis:
  # 最大调用深度
  max_depth: 10

  # 融合策略: bayesian/voting/weighted
  fusion_strategy: "weighted"

  # 是否包含测试代码
  include_tests: false

  # 排除的文件模式
  exclude_patterns:
    - "*.md"
    - "*.txt"
    - "*.properties"
    - "**/test/**"
    - "**/target/**"

# 严重程度评估配置
severity:
  # 各维度权重
  weights:
    depth: 0.20
    scope: 0.25
    criticality: 0.25
    sensitivity: 0.15
    history: 0.15

  # 阈值设置
  thresholds:
    critical: 9.0
    high: 7.0
    medium: 5.0
    low: 3.0

# 测试选择配置
test_selection:
  # 选择策略: all/starts/impact_based/hybrid
  strategy: "impact_based"

  # 覆盖率阈值
  coverage_threshold: 0.8

  # 最大选择用例数
  max_tests: 200

# 报告配置
report:
  # 默认输出格式
  default_format: "html"

  # 是否包含代码片段
  include_code_snippets: true

  # 是否包含建议措施
  include_recommendations: true

# 集成配置
integration:
  jenkins:
    enabled: true
    webhook_url: ""

  gitlab:
    enabled: false
    token: ""
    project_id: ""
```

**方式2：命令行参数**

```bash
# 指定最大深度
jcia analyze --repo-path . --max-depth 15

# 指定融合策略
jcia analyze --repo-path . --fusion-strategy bayesian

# 指定输出格式
jcia analyze --repo-path . --output-format json

# 排除特定文件
jcia analyze --repo-path . --exclude "*.md,*.txt"

# 指定配置文件
jcia analyze --repo-path . --config /path/to/custom-config.yaml
```

---

## 三、性能问题

### Q1: 分析大型项目需要多长时间？

**A:** 分析时间取决于项目规模和配置参数。

**典型性能数据：**

| 项目规模 | 代码行数 | 全量分析时间 | 增量分析时间 |
|---------|---------|-------------|-------------|
| 小型项目 | <10万行 | 1-2分钟 | 10-30秒 |
| 中型项目 | 10-50万行 | 3-5分钟 | 30-60秒 |
| 大型项目 | 50-100万行 | 5-10分钟 | 1-2分钟 |
| 超大型项目 | >100万行 | 10-20分钟 | 2-5分钟 |

**优化建议：**

```bash
# 1. 使用增量分析（只分析变更部分）
jcia analyze --repo-path . --from-commit HEAD~1 --to-commit HEAD --incremental

# 2. 限制分析深度
jcia analyze --repo-path . --max-depth 5

# 3. 排除不需要分析的文件
jcia analyze --repo-path . --exclude "**/test/**,**/target/**"

# 4. 使用并行分析（如果硬件支持）
jcia analyze --repo-path . --parallel --workers 4

# 5. 缓存分析结果
jcia analyze --repo-path . --cache-dir .jcia-cache
```

---

### Q2: 分析过程中内存不足怎么办？

**A:** 可以通过配置优化内存使用。

**解决方案：**

**方法1：增加JVM内存（如果是Java相关分析）**

```bash
export JAVA_OPTS="-Xmx4g -Xms2g"
jcia analyze --repo-path .
```

**方法2：限制分析范围**

```yaml
# .jcia.yaml
analysis:
  # 限制最大文件数
  max_files: 1000

  # 限制单个文件大小（MB）
  max_file_size: 10

  # 排除大文件
  exclude_large_files: true

  # 分批处理
  batch_size: 100
```

**方法3：使用流式分析**

```bash
# 流式分析模式，减少内存占用
jcia analyze --repo-path . --streaming-mode
```

**方法4：增加系统内存或交换空间**

```bash
# Linux: 创建交换文件
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

### Q3: 如何提高分析准确率？

**A:** 通过调整配置和提供更多上下文信息。

**优化建议：**

**1. 调整分析策略**

```yaml
# .jcia.yaml
analysis:
  # 使用更精确的分析策略
  strategy: "detailed"  # 可选: fast/standard/detailed

  # 启用多策略融合
  fusion_strategy: "bayesian"  # bayesian/voting/weighted

  # 增加分析深度
  max_depth: 10

  # 启用上下文分析
  context_analysis: true
```

**2. 提供业务上下文**

```yaml
# .jcia.yaml
# 标注关键业务类
business_context:
  critical_classes:
    - "com.example.order.OrderService"
    - "com.example.payment.PaymentGateway"
    - "com.example.user.AuthService"

  core_modules:
    - "order-management"
    - "payment-processing"
    - "user-authentication"

  data_access_layer:
    - "com.example.dao.*"
    - "com.example.repository.*"
```

**3. 使用历史数据校准**

```yaml
# .jcia.yaml
calibration:
  # 使用历史分析结果校准
  use_historical_data: true

  # 历史数据路径
  historical_data_path: ".jcia/history"

  # 自动校准频率
  auto_calibrate: true
  calibration_interval: "weekly"
```

**4. 验证和反馈**

```bash
# 运行分析时收集反馈
jcia analyze --repo-path . --collect-feedback

# 根据实际结果标记预测准确性
jcia feedback --analysis-id <id> --actual-impact "high" --notes "确实影响了支付模块"
```

---

## 四、集成问题

### Q1: 如何集成到Jenkins？

**A:** 通过Jenkins Pipeline或自由风格项目集成。

**方式一：Pipeline方式（推荐）**

```groovy
pipeline {
    agent any

    environment {
        JCIA_HOME = tool name: 'jcia', type: 'com.cloudbees.jenkins.plugins.customtools.CustomTool'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.GIT_COMMIT = sh(
                        script: 'git rev-parse HEAD',
                        returnStdout: true
                    ).trim()
                    env.GIT_PREVIOUS_COMMIT = sh(
                        script: 'git rev-parse HEAD~1',
                        returnStdout: true
                    ).trim()
                }
            }
        }

        stage('JCIA Impact Analysis') {
            steps {
                sh '''
                    ${JCIA_HOME}/bin/jcia analyze \
                        --repo-path . \
                        --from-commit ${GIT_PREVIOUS_COMMIT} \
                        --to-commit ${GIT_COMMIT} \
                        --output-format html \
                        --output-dir reports/jcia/
                '''
            }
            post {
                always {
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'reports/jcia',
                        reportFiles: 'impact_analysis.html',
                        reportName: 'JCIA Impact Analysis Report'
                    ])
                }
            }
        }

        stage('JCIA Test Selection') {
            steps {
                sh '''
                    ${JCIA_HOME}/bin/jcia test \
                        --repo-path . \
                        --strategy impact_based \
                        --output reports/jcia/test-selection.json
                '''
                script {
                    def testSelection = readJSON file: 'reports/jcia/test-selection.json'
                    env.SELECTED_TESTS = testSelection.selected_tests.join(',')
                    env.TEST_REDUCTION = testSelection.reduction_percentage
                    echo "Selected ${testSelection.selected_tests.size()} tests (${env.TEST_REDUCTION}% reduction)"
                }
            }
        }

        stage('Run Selected Tests') {
            when {
                expression { env.SELECTED_TESTS?.trim() }
            }
            steps {
                sh 'mvn test -Dtest=${SELECTED_TESTS}'
            }
            post {
                always {
                    junit 'target/surefire-reports/*.xml'
                }
            }
        }
    }

    post {
        always {
            cleanWs()
        }
        failure {
            emailext (
                subject: "JCIA Analysis Failed: ${env.JOB_NAME} - ${env.BUILD_NUMBER}",
                body: "查看详情: ${env.BUILD_URL}",
                to: "${env.CHANGE_AUTHOR_EMAIL}"
            )
        }
    }
}
```

**方式二：自由风格项目**

1. 在Jenkins中创建新的自由风格项目
2. 在"构建环境"中配置JCIA工具
3. 在"构建"步骤中添加"执行Shell"或"执行Windows批处理命令"：

```bash
# Linux/macOS
jcia analyze \
    --repo-path $WORKSPACE \
    --from-commit $GIT_PREVIOUS_COMMIT \
    --to-commit $GIT_COMMIT \
    --output-format html \
    --output-dir $WORKSPACE/reports/

# Windows
jcia analyze ^
    --repo-path %WORKSPACE% ^
    --from-commit %GIT_PREVIOUS_COMMIT% ^
    --to-commit %GIT_COMMIT% ^
    --output-format html ^
    --output-dir %WORKSPACE%\reports\
```

4. 在"构建后操作"中添加"发布HTML报告"

---

### Q2: 如何集成到GitLab CI？

**A:** 通过`.gitlab-ci.yml`文件配置。

**基础配置：**

```yaml
# .gitlab-ci.yml

stages:
  - analyze
  - test
  - report

variables:
  JCIA_OUTPUT_DIR: "reports/jcia"
  GIT_DEPTH: 0  # 需要完整历史用于分析

# 安装JCIA阶段
.install_jcia: &install_jcia
  before_script:
    - pip install jcia

# JCIA影响分析
jcia_impact_analysis:
  stage: analyze
  <<: *install_jcia
  script:
    - mkdir -p $JCIA_OUTPUT_DIR
    - |
      jcia analyze \
        --repo-path . \
        --from-commit $CI_COMMIT_BEFORE_SHA \
        --to-commit $CI_COMMIT_SHA \
        --output-format html \
        --output-dir $JCIA_OUTPUT_DIR/
  artifacts:
    name: "jcia-analysis-$CI_COMMIT_SHORT_SHA"
    paths:
      - $JCIA_OUTPUT_DIR/
    expire_in: 30 days
    reports:
      # GitLab 14.0+ 支持外部报告集成
      junit: $JCIA_OUTPUT_DIR/test-results.xml
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
  tags:
    - docker

# JCIA测试选择
jcia_test_selection:
  stage: test
  <<: *install_jcia
  needs:
    - job: jcia_impact_analysis
      artifacts: true
  script:
    - |
      jcia test \
        --repo-path . \
        --strategy impact_based \
        --output $JCIA_OUTPUT_DIR/test-selection.json
    # 导出选中的测试列表到环境变量
    - export SELECTED_TESTS=$(cat $JCIA_OUTPUT_DIR/test-selection.json | jq -r '.selected_tests | join(",")')
    - echo "SELECTED_TESTS=$SELECTED_TESTS" >> build.env
  artifacts:
    paths:
      - $JCIA_OUTPUT_DIR/test-selection.json
    reports:
      dotenv: build.env
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"

# 运行选中的测试
run_selected_tests:
  stage: test
  needs:
    - job: jcia_test_selection
      artifacts: true
  script:
    - |
      if [ -n "$SELECTED_TESTS" ]; then
        echo "Running selected tests: $SELECTED_TESTS"
        mvn test -Dtest=$SELECTED_TESTS
      else
        echo "No tests selected, running smoke tests only"
        mvn test -Dtest=*SmokeTest
      fi
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"

# 生成合并请求报告
mr_report:
  stage: report
  needs:
    - job: jcia_impact_analysis
      artifacts: true
    - job: run_selected_tests
  script:
    - |
      # 生成MR摘要
      cat > $JCIA_OUTPUT_DIR/mr_summary.md << EOF
      ## JCIA 影响分析报告

      **提交:** $CI_COMMIT_SHORT_SHA
      **分支:** $CI_MERGE_REQUEST_SOURCE_BRANCH_NAME → $CI_MERGE_REQUEST_TARGET_BRANCH_NAME

      ### 分析摘要

      $(cat $JCIA_OUTPUT_DIR/summary.json | jq -r '.summary')

      ### 建议措施

      $(cat $JCIA_OUTPUT_DIR/recommendations.txt)

      [查看完整报告]($CI_JOB_URL/artifacts/browse/reports/jcia/)
      EOF
    - cat $JCIA_OUTPUT_DIR/mr_summary.md
  artifacts:
    paths:
      - $JCIA_OUTPUT_DIR/mr_summary.md
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  tags:
    - docker
```

---

由于篇幅限制，我将继续创建剩余的FAQ内容。让我完成性能、集成、配置和故障排查部分：
