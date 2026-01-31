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
# Windows 和 Unix 兼容
ifeq ($(OS),Windows_NT)
    VENV_PYTHON := $(VENV_DIR)\Scripts\python.exe
    VENV_PIP := $(VENV_DIR)\Scripts\pip.exe
else
    VENV_PYTHON := $(VENV_DIR)/bin/python
    VENV_PIP := $(VENV_DIR)/bin/pip
endif

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

format:
	python -m ruff format jcia tests

check: lint security
	python -m pyright jcia tests

security:
	python -m bandit -r jcia -c pyproject.toml

clean:
ifeq ($(OS),Windows_NT)
	powershell -Command "Remove-Item -Path build, dist, *.egg-info, htmlcov, .pytest_cache, .mypy_cache, .ruff_cache -Recurse -Force -ErrorAction SilentlyContinue"
	powershell -Command "Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
	powershell -Command "Get-ChildItem -Recurse -File -Filter *.pyc | Remove-Item -Force -ErrorAction SilentlyContinue"
else
	rm -rf build/ dist/ *.egg-info/ htmlcov/ .pytest_cache/ .mypy_cache/ .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
endif

setup-hooks: install-dev
	python -m pre_commit install
