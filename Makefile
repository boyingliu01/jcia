.PHONY: help venv install install-dev test test-unit test-integration lint format check security clean setup-hooks docs

help:
	@echo "JCIA - Java Code Impact Analyzer"
	@echo ""
	@echo "Available targets:"
	@echo "  venv          - 创建Python虚拟环境"
	@echo "  install       - 安装生产依赖"
	@echo "  install-dev   - 安装开发依赖"
	@echo "  setup-hooks   - 设置pre-commit钩子"
	@echo "  test          - 运行所有测试"
	@echo "  test-unit     - 仅运行单元测试"
	@echo "  test-integration - 运行集成测试"
	@echo "  lint          - 运行代码检查(ruff)"
	@echo "  format        - 格式化代码(ruff format)"
	@echo "  check         - 运行所有检查(lint + type + security)"
	@echo "  security      - 运行安全扫描(bandit)"
	@echo "  clean         - 清理构建产物"

# 虚拟环境路径
VENV_DIR := .venv
VENV_PYTHON := $(VENV_DIR)\Scripts\python.exe
VENV_PIP := $(VENV_DIR)\Scripts\pip.exe

# 发布守卫脚本：#20-C 起与 jcia/tests 同标准做文件级 lint/format/类型检查（对齐 ci.yml）。
# scripts/ 其余文件属历史遗留（不在 canonical 范围），故用文件级而非目录级。
GUARDS := scripts/check_dist_placeholders.py scripts/check_wheel_assets.py


venv:
	python -m venv $(VENV_DIR)
	python -m pip install --upgrade pip

install: venv
	python -m pip install -r requirements.txt

install-dev: venv
	python -m pip install -e ".[dev]"

test:
	python -m pytest tests/ -v --cov=jcia --cov-report=term-missing

test-unit:
	python -m pytest tests/unit -v --cov=jcia --cov-report=term-missing

test-integration:
	python -m pytest tests/integration -v

lint:
	python -m ruff check jcia tests
	python -m ruff check --select I jcia tests
	python -m ruff check $(GUARDS)

lint-strict:
	@echo "Running strict lint checks..."
	python -m ruff check --select ALL jcia tests

format:
	python -m ruff format jcia tests
	python -m ruff format $(GUARDS)

arch-check:
	@echo "Checking architecture contracts (import-linter)..."
	lint-imports

check: lint arch-check security typecheck

check-strict: lint-strict security typecheck-strict
	@echo "All strict checks passed!"

typecheck:
	python -m pyright jcia tests $(GUARDS)

typecheck-strict:
	@echo "Running strict type checking..."
	python -m pyright --level error jcia tests

security:
	python -m bandit -r jcia -c pyproject.toml

security-strict:
	@echo "Running strict security checks..."
	python -m bandit -r jcia -c pyproject.toml -ll

mypy-check:
	python -m mypy jcia tests $(GUARDS)

complexity:
	@echo "Checking code complexity..."
	python -m ruff check --select C90 jcia tests

unused:
	@echo "Checking for unused code..."
	python -m ruff check --select F,ARG jcia tests

docstrings:
	@echo "Checking docstrings..."
	python -m ruff check --select D jcia tests

static-analysis-full: format lint-strict typecheck-strict security-strict mypy-check complexity unused
	@echo "Full static analysis complete!"

clean:
	powershell -Command "Remove-Item -Path build, dist, *.egg-info, htmlcov, .pytest_cache, .mypy_cache, .ruff_cache -Recurse -Force -ErrorAction SilentlyContinue"
	powershell -Command "Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
	powershell -Command "Get-ChildItem -Recurse -File -Filter *.pyc | Remove-Item -Force -ErrorAction SilentlyContinue"


setup-hooks: install-dev
	python -m pre_commit install
