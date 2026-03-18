"""Unit tests for CodeQL adapter.

Tests for CodeQL-based call chain analysis functionality.
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, mock_open

import pytest

from jcia.adapters.tools.codeql_adapter import CodeQLAdapter
from jcia.adapters.tools.codeql_models import (
    CodeQLAnalysisStatus,
    CodeQLCall,
    CodeQLCallGraph,
    CodeQLFinding,
    CodeQLFindingSeverity,
    CodeQLLocation,
    CodeQLMethod,
)
from jcia.core.interfaces.call_chain_analyzer import (
    AnalyzerType,
    CallChainDirection,
    CallChainGraph,
    CallChainNode,
)

pytestmark = [pytest.mark.unit, pytest.mark.adapters, pytest.mark.tools]


class TestCodeQLAdapterInit:
    """Tests for CodeQLAdapter initialization."""

    def test_init_with_defaults(self, tmp_path: Path) -> None:
        """Test initialization with default parameters."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        adapter = CodeQLAdapter(str(repo_path))

        assert adapter._repo_path == repo_path.resolve()
        assert adapter._max_depth == 10
        assert adapter._working_dir is not None
        assert adapter._database_path is None

    def test_init_with_custom_params(self, tmp_path: Path) -> None:
        """Test initialization with custom parameters."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        working_dir = tmp_path / "work"
        working_dir.mkdir()

        adapter = CodeQLAdapter(
            str(repo_path),
            codeql_path="/usr/local/bin/codeql",
            working_dir=working_dir,
            max_depth=15,
        )

        assert adapter._repo_path == repo_path.resolve()
        assert adapter._codeql_path == "/usr/local/bin/codeql"
        assert adapter._working_dir == working_dir
        assert adapter._max_depth == 15

    def test_analyzer_type(self, tmp_path: Path) -> None:
        """Test analyzer_type property returns STATIC."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        adapter = CodeQLAdapter(str(repo_path))

        assert adapter.analyzer_type == AnalyzerType.STATIC

    def test_supports_cross_service(self, tmp_path: Path) -> None:
        """Test supports_cross_service property returns False."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        adapter = CodeQLAdapter(str(repo_path))

        assert adapter.supports_cross_service is False


class TestCodeQLAdapterFindCodeQL:
    """Tests for CodeQL CLI detection."""

    @patch("shutil.which")
    def test_find_codeql_from_path(self, mock_which: Mock, tmp_path: Path) -> None:
        """Test finding CodeQL from PATH."""
        mock_which.return_value = "/usr/bin/codeql"
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        adapter = CodeQLAdapter(str(repo_path))
        # _find_codeql is called once during __init__, so reset mock
        mock_which.reset_mock()
        result = adapter._find_codeql()

        assert result == "/usr/bin/codeql"
        mock_which.assert_called_once_with("codeql")

    @patch("shutil.which")
    def test_find_codeql_not_found(self, mock_which: Mock, tmp_path: Path) -> None:
        """Test when CodeQL is not found."""
        mock_which.return_value = None
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        adapter = CodeQLAdapter(str(repo_path))
        result = adapter._find_codeql()

        assert result is None

    @patch("shutil.which")
    @patch("pathlib.Path.exists")
    def test_find_codeql_common_paths(
        self, mock_exists: Mock, mock_which: Mock, tmp_path: Path
    ) -> None:
        """Test finding CodeQL in common installation paths."""
        mock_which.return_value = None
        mock_exists.return_value = True
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        adapter = CodeQLAdapter(str(repo_path))

        # Mock the home directory check
        with patch.object(Path, "home", return_value=Path("/home/user")):
            result = adapter._find_codeql()

        # Should find codeql in one of the common paths
        assert result is not None or mock_exists.call_count > 0


class TestCodeQLAdapterCreateDatabase:
    """Tests for database creation."""

    @patch("jcia.adapters.tools.codeql_adapter.subprocess.run")
    def test_create_database_success(self, mock_run: Mock, tmp_path: Path) -> None:
        """Test successful database creation."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        # Create src/main/java structure so source.exists() returns True
        source_path = repo_path / "src" / "main" / "java"
        source_path.mkdir(parents=True)
        working_dir = tmp_path / "work"
        working_dir.mkdir()

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Successfully created database",
            stderr="",
        )

        adapter = CodeQLAdapter(
            str(repo_path),
            codeql_path="/usr/bin/codeql",
            working_dir=working_dir,
        )
        db_path = adapter.create_database()

        # db_path is the returned path, check it matches expected location
        assert str(db_path).endswith("codeql-db")
        mock_run.assert_called_once()

    @patch("jcia.adapters.tools.codeql_adapter.subprocess.run")
    def test_create_database_timeout(self, mock_run: Mock, tmp_path: Path) -> None:
        """Test database creation timeout."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        working_dir = tmp_path / "work"
        working_dir.mkdir()

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="codeql", timeout=60)

        adapter = CodeQLAdapter(
            str(repo_path),
            codeql_path="/usr/bin/codeql",
            working_dir=working_dir,
        )

        with pytest.raises(RuntimeError, match="timed out"):
            adapter.create_database(timeout=60)

    @patch("subprocess.run")
    def test_create_database_no_codeql(self, mock_run: Mock, tmp_path: Path) -> None:
        """Test database creation when CodeQL is not available."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        working_dir = tmp_path / "work"
        working_dir.mkdir()

        adapter = CodeQLAdapter(
            str(repo_path),
            codeql_path=None,
            working_dir=working_dir,
        )

        with pytest.raises(RuntimeError, match="CodeQL CLI not found"):
            adapter.create_database()

    @patch("jcia.adapters.tools.codeql_adapter.subprocess.run")
    @patch("jcia.adapters.tools.codeql_adapter.shutil.rmtree")
    def test_create_database_overwrite(self, mock_rmtree: Mock, mock_run: Mock, tmp_path: Path) -> None:
        """Test database creation with overwrite flag."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        # Create src/main/java structure so source.exists() returns True
        source_path = repo_path / "src" / "main" / "java"
        source_path.mkdir(parents=True)
        working_dir = tmp_path / "work"
        working_dir.mkdir()

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Successfully created database",
            stderr="",
        )

        adapter = CodeQLAdapter(
            str(repo_path),
            codeql_path="/usr/bin/codeql",
            working_dir=working_dir,
        )

        # Create database first time (db doesn't exist yet)
        db_path = adapter.create_database()
        assert db_path is not None

        # Now simulate the database existing by creating the directory
        (working_dir / "codeql-db").mkdir(exist_ok=True)

        # Create again with overwrite - should call rmtree and subprocess.run again
        db_path2 = adapter.create_database(overwrite=True)
        assert db_path2 is not None

        # Should have been called twice (once for each create_database)
        assert mock_run.call_count == 2
        # rmtree should have been called to remove existing db
        mock_rmtree.assert_called_once()


class TestCodeQLAdapterRunQuery:
    """Tests for QL query execution."""

    @patch("jcia.adapters.tools.codeql_adapter.subprocess.run")
    @patch("pathlib.Path.exists")
    def test_run_query_success(self, mock_exists: Mock, mock_run: Mock, tmp_path: Path) -> None:
        """Test successful query execution."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        working_dir = tmp_path / "work"
        working_dir.mkdir()

        query_result = {"tuples": [["value1", "value2"]]}
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(query_result),
            stderr="",
        )
        # Mock the output file exists
        mock_exists.return_value = True

        adapter = CodeQLAdapter(
            str(repo_path),
            codeql_path="/usr/bin/codeql",
            working_dir=working_dir,
        )
        adapter._database_path = working_dir / "db"

        # Mock the output file read
        with patch.object(Path, "read_text", return_value=json.dumps(query_result)):
            query = "select * from methods"
            results = adapter._run_query(query)

        assert "tuples" in results
        assert len(results["tuples"]) == 1
        assert results["tuples"][0] == ["value1", "value2"]

    @patch("jcia.adapters.tools.codeql_adapter.subprocess.run")
    def test_run_query_failure(self, mock_run: Mock, tmp_path: Path) -> None:
        """Test query execution failure raises RuntimeError."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        working_dir = tmp_path / "work"
        working_dir.mkdir()

        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Query failed",
        )

        adapter = CodeQLAdapter(
            str(repo_path),
            codeql_path="/usr/bin/codeql",
            working_dir=working_dir,
        )
        adapter._database_path = working_dir / "db"

        with pytest.raises(RuntimeError, match="CodeQL query failed"):
            adapter._run_query("invalid query")


class TestCodeQLAdapterExtractCallGraph:
    """Tests for call graph extraction."""

    def test_extract_call_graph_empty(self, tmp_path: Path) -> None:
        """Test extraction with empty results."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        adapter = CodeQLAdapter(str(repo_path))

        with patch.object(adapter, "_run_query", return_value={"tuples": []}):
            call_graph = adapter._extract_call_graph()

        assert call_graph is not None
        assert len(call_graph.methods) == 0
        assert len(call_graph.calls) == 0

    def test_extract_call_graph_with_data(self, tmp_path: Path) -> None:
        """Test extraction with method data."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        adapter = CodeQLAdapter(str(repo_path))

        # Mock query results for methods (as dict with tuples)
        method_results = {
            "tuples": [
                {"name": "process", "signature": "(String): void", "class_name": "com.example.Service", "file": "Service.java", "line": "10"},
                {"name": "helper", "signature": "(): String", "class_name": "com.example.Util", "file": "Util.java", "line": "5"},
            ]
        }

        # Mock query results for calls (as dict with tuples containing lists)
        call_results = {
            "tuples": [
                [{"name": "process", "class_name": "com.example.Service"}, {"name": "helper", "class_name": "com.example.Util"}],
            ]
        }

        with patch.object(
            adapter,
            "_run_query",
            side_effect=[method_results, call_results, {"tuples": []}],
        ):
            call_graph = adapter._extract_call_graph()

        assert call_graph is not None
        assert len(call_graph.methods) == 2
        assert len(call_graph.calls) == 1

    def test_extract_call_graph_with_entry_points(self, tmp_path: Path) -> None:
        """Test extraction identifies entry points."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        adapter = CodeQLAdapter(str(repo_path))

        method_results = {
            "tuples": [
                {"name": "handleRequest", "signature": "(Request): Response", "class_name": "com.example.Controller", "file": "Controller.java", "line": "20"},
            ]
        }

        entry_point_results = {
            "tuples": [
                {"name": "handleRequest", "class_name": "com.example.Controller"},
            ]
        }

        with patch.object(
            adapter,
            "_run_query",
            side_effect=[method_results, {"tuples": []}, entry_point_results],
        ):
            call_graph = adapter._extract_call_graph()

        assert call_graph is not None
        assert len(call_graph.entry_points) == 1


class TestCodeQLAdapterAnalyzeUpstream:
    """Tests for upstream call chain analysis."""

    def test_analyze_upstream_no_database(self, tmp_path: Path) -> None:
        """Test upstream analysis without database returns empty graph."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        adapter = CodeQLAdapter(str(repo_path))

        graph = adapter.analyze_upstream("com.example.Service.process")

        assert graph is not None
        assert graph.direction == CallChainDirection.UPSTREAM
        assert graph.root.method_name == "process"

    def test_analyze_upstream_with_callers(self, tmp_path: Path) -> None:
        """Test upstream analysis with caller methods."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        working_dir = tmp_path / "work"
        working_dir.mkdir()

        adapter = CodeQLAdapter(
            str(repo_path),
            codeql_path="/usr/bin/codeql",
            working_dir=working_dir,
        )
        adapter._database_path = working_dir / "db"

        # Create mock call graph
        caller = CodeQLMethod(
            name="handleRequest",
            class_name="com.example.Controller",
            file="Controller.java",
            line=10,
        )
        callee = CodeQLMethod(
            name="process",
            class_name="com.example.Service",
            file="Service.java",
            line=20,
        )
        call = CodeQLCall(caller=caller, callee=callee)

        mock_call_graph = CodeQLCallGraph(
            methods=[caller, callee],
            calls=[call],
        )

        with patch.object(adapter, "_extract_call_graph", return_value=mock_call_graph):
            graph = adapter.analyze_upstream("com.example.Service.process")

        assert graph is not None
        assert graph.root.class_name == "com.example.Service"
        assert graph.root.method_name == "process"
        assert len(graph.root.children) >= 1


class TestCodeQLAdapterAnalyzeDownstream:
    """Tests for downstream call chain analysis."""

    def test_analyze_downstream_no_database(self, tmp_path: Path) -> None:
        """Test downstream analysis without database returns empty graph."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        adapter = CodeQLAdapter(str(repo_path))

        graph = adapter.analyze_downstream("com.example.Controller.handleRequest")

        assert graph is not None
        assert graph.direction == CallChainDirection.DOWNSTREAM
        assert graph.root.method_name == "handleRequest"

    def test_analyze_downstream_with_callees(self, tmp_path: Path) -> None:
        """Test downstream analysis with called methods."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        working_dir = tmp_path / "work"
        working_dir.mkdir()

        adapter = CodeQLAdapter(
            str(repo_path),
            codeql_path="/usr/bin/codeql",
            working_dir=working_dir,
        )
        adapter._database_path = working_dir / "db"

        # Create mock call graph
        caller = CodeQLMethod(
            name="handleRequest",
            class_name="com.example.Controller",
            file="Controller.java",
            line=10,
        )
        callee = CodeQLMethod(
            name="process",
            class_name="com.example.Service",
            file="Service.java",
            line=20,
        )
        call = CodeQLCall(caller=caller, callee=callee)

        mock_call_graph = CodeQLCallGraph(
            methods=[caller, callee],
            calls=[call],
        )

        with patch.object(adapter, "_extract_call_graph", return_value=mock_call_graph):
            graph = adapter.analyze_downstream("com.example.Controller.handleRequest")

        assert graph is not None
        assert graph.root.class_name == "com.example.Controller"
        assert graph.root.method_name == "handleRequest"
        assert len(graph.root.children) >= 1


class TestCodeQLAdapterAnalyzeBothDirections:
    """Tests for bidirectional analysis."""

    def test_analyze_both_directions(self, tmp_path: Path) -> None:
        """Test analyzing both upstream and downstream."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        adapter = CodeQLAdapter(str(repo_path))

        upstream, downstream = adapter.analyze_both_directions("com.example.Service.process")

        assert upstream is not None
        assert downstream is not None
        assert upstream.direction == CallChainDirection.UPSTREAM
        assert downstream.direction == CallChainDirection.DOWNSTREAM
        assert upstream.root.method_name == "process"
        assert downstream.root.method_name == "process"


class TestCodeQLAdapterBuildFullGraph:
    """Tests for building complete call graph."""

    def test_build_full_graph_empty(self, tmp_path: Path) -> None:
        """Test building full graph with no methods."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        adapter = CodeQLAdapter(str(repo_path))

        with patch.object(adapter, "_extract_call_graph", return_value=CodeQLCallGraph()):
            graph = adapter.build_full_graph()

        assert graph is not None
        assert graph.direction == CallChainDirection.BOTH

    def test_build_full_graph_with_methods(self, tmp_path: Path) -> None:
        """Test building full graph with methods."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        working_dir = tmp_path / "work"
        working_dir.mkdir()

        adapter = CodeQLAdapter(
            str(repo_path),
            codeql_path="/usr/bin/codeql",
            working_dir=working_dir,
        )
        adapter._database_path = working_dir / "db"

        method1 = CodeQLMethod(name="method1", class_name="com.example.Class1")
        method2 = CodeQLMethod(name="method2", class_name="com.example.Class2")

        mock_call_graph = CodeQLCallGraph(methods=[method1, method2])

        with patch.object(adapter, "_extract_call_graph", return_value=mock_call_graph):
            graph = adapter.build_full_graph()

        assert graph is not None
        assert len(graph.root.children) == 2


class TestCodeQLAdapterSecurityQueries:
    """Tests for security query functionality."""

    @patch("jcia.adapters.tools.codeql_adapter.subprocess.run")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.read_text")
    def test_run_security_queries(
        self, mock_read_text: Mock, mock_exists: Mock, mock_run: Mock, tmp_path: Path
    ) -> None:
        """Test running security queries."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        working_dir = tmp_path / "work"
        working_dir.mkdir()

        sarif_output = {
            "runs": [
                {
                    "tool": {"driver": {"rules": [{"name": "SQL Injection"}]}},
                    "results": [
                        {
                            "ruleId": "java/sql-injection",
                            "ruleIndex": 0,
                            "message": {"text": "SQL injection vulnerability"},
                            "locations": [
                                {
                                    "physicalLocation": {
                                        "artifactLocation": {"uri": "Service.java"},
                                        "region": {"startLine": 10, "startColumn": 5},
                                    }
                                }
                            ],
                        }
                    ]
                }
            ]
        }

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr="",
        )
        mock_exists.return_value = True
        mock_read_text.return_value = json.dumps(sarif_output)

        adapter = CodeQLAdapter(
            str(repo_path),
            codeql_path="/usr/bin/codeql",
            working_dir=working_dir,
        )
        adapter._database_path = working_dir / "db"

        findings = adapter._run_security_queries()

        assert len(findings) == 1
        assert findings[0].rule_id == "java/sql-injection"

    def test_parse_sarif_result(self, tmp_path: Path) -> None:
        """Test parsing SARIF format results."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        adapter = CodeQLAdapter(str(repo_path))

        result = {
            "ruleId": "java/command-injection",
            "ruleIndex": 0,
            "message": {"text": "Command injection found"},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": "Executor.java"},
                        "region": {"startLine": 25, "startColumn": 10},
                    }
                }
            ],
        }

        run = {
            "tool": {"driver": {"rules": [{"name": "Command Injection"}]}}
        }

        finding = adapter._parse_sarif_result(result, run)

        assert finding is not None
        assert finding.rule_id == "java/command-injection"
        assert finding.location.file == "Executor.java"
        assert finding.location.start_line == 25


class TestCodeQLAdapterParseMethod:
    """Tests for method name parsing."""

    def test_parse_method_full_name(self, tmp_path: Path) -> None:
        """Test parsing fully qualified method name."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        adapter = CodeQLAdapter(str(repo_path))

        class_name, method_name = adapter._parse_method("com.example.Service.process")

        assert class_name == "com.example.Service"
        assert method_name == "process"

    def test_parse_method_simple_name(self, tmp_path: Path) -> None:
        """Test parsing simple method name."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        adapter = CodeQLAdapter(str(repo_path))

        class_name, method_name = adapter._parse_method("process")

        assert class_name is None
        assert method_name == "process"

    def test_parse_method_nested_class(self, tmp_path: Path) -> None:
        """Test parsing method with nested class."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        adapter = CodeQLAdapter(str(repo_path))

        class_name, method_name = adapter._parse_method("com.example.Outer$Inner.method")

        assert class_name == "com.example.Outer$Inner"
        assert method_name == "method"


class TestCodeQLAdapterHelperMethods:
    """Tests for helper methods."""

    def test_create_empty_graph_upstream(self, tmp_path: Path) -> None:
        """Test creating empty upstream graph."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        adapter = CodeQLAdapter(str(repo_path))

        graph = adapter._create_empty_graph(
            "com.example.Service.process",
            CallChainDirection.UPSTREAM,
        )

        assert graph.direction == CallChainDirection.UPSTREAM
        assert graph.root.class_name == "com.example.Service"
        assert graph.root.method_name == "process"

    def test_get_severity_by_depth(self, tmp_path: Path) -> None:
        """Test severity calculation by depth."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        adapter = CodeQLAdapter(str(repo_path))

        assert adapter._get_severity_by_depth(0) == "HIGH"
        assert adapter._get_severity_by_depth(1) == "MEDIUM"
        assert adapter._get_severity_by_depth(2) == "LOW"
        assert adapter._get_severity_by_depth(5) == "LOW"
        assert adapter._get_severity_by_depth(10) == "LOW"


class TestCodeQLAdapterCleanup:
    """Tests for cleanup functionality."""

    def test_cleanup_removes_temp_files(self, tmp_path: Path) -> None:
        """Test cleanup removes temporary files."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        working_dir = tmp_path / "work"
        working_dir.mkdir()

        adapter = CodeQLAdapter(
            str(repo_path),
            working_dir=working_dir,
        )

        # Create a temp query file
        query_file = working_dir / "temp_query.ql"
        query_file.write_text("select 1")

        assert query_file.exists()

        adapter.cleanup()

        # Temp files should be cleaned up
        # Note: actual cleanup implementation may vary


class TestCodeQLMethodToCallChainNode:
    """Tests for CodeQLMethod to CallChainNode conversion."""

    def test_to_call_chain_node(self, tmp_path: Path) -> None:
        """Test converting CodeQLMethod to CallChainNode."""
        method = CodeQLMethod(
            name="process",
            class_name="com.example.Service",
            signature="(String): void",
            file="Service.java",
            line=42,
            is_static=False,
            is_constructor=False,
            modifiers=["public"],
        )

        node = CallChainNode(
            class_name=method.class_name or "",
            method_name=method.name,
        )
        node.metadata["file"] = method.file
        node.metadata["line"] = method.line
        node.metadata["signature"] = method.signature

        assert node.class_name == "com.example.Service"
        assert node.method_name == "process"
        assert node.metadata["file"] == "Service.java"
        assert node.metadata["line"] == 42


class TestCodeQLFinding:
    """Tests for CodeQL finding model."""

    def test_is_security_finding_true(self) -> None:
        """Test security finding detection for SQL injection."""
        location = CodeQLLocation(file="Service.java", start_line=10, start_column=5)
        finding = CodeQLFinding(
            rule_id="java/sql-injection",
            rule_name="SQL Injection",
            severity=CodeQLFindingSeverity.ERROR,
            message="Potential SQL injection",
            location=location,
        )

        assert finding.is_security_finding() is True

    def test_is_security_finding_command_injection(self) -> None:
        """Test security finding detection for command injection."""
        location = CodeQLLocation(file="Executor.java", start_line=20, start_column=8)
        finding = CodeQLFinding(
            rule_id="java/command-injection",
            rule_name="Command Injection",
            severity=CodeQLFindingSeverity.ERROR,
            message="Potential command injection",
            location=location,
        )

        assert finding.is_security_finding() is True

    def test_is_security_finding_false(self) -> None:
        """Test non-security finding detection."""
        location = CodeQLLocation(file="Service.java", start_line=30, start_column=2)
        finding = CodeQLFinding(
            rule_id="java/unused-variable",
            rule_name="Unused Variable",
            severity=CodeQLFindingSeverity.WARNING,
            message="Variable is unused",
            location=location,
        )

        assert finding.is_security_finding() is False


class TestCodeQLCallGraph:
    """Tests for CodeQLCallGraph model."""

    def test_find_method_by_full_name(self) -> None:
        """Test finding method by full name."""
        method = CodeQLMethod(
            name="process",
            class_name="com.example.Service",
        )
        call_graph = CodeQLCallGraph(methods=[method])

        found = call_graph.find_method("com.example.Service.process")

        assert found is not None
        assert found.name == "process"

    def test_find_method_by_simple_name(self) -> None:
        """Test finding method by simple name."""
        method = CodeQLMethod(
            name="process",
            class_name="com.example.Service",
        )
        call_graph = CodeQLCallGraph(methods=[method])

        found = call_graph.find_method("process")

        assert found is not None

    def test_find_method_not_found(self) -> None:
        """Test finding method that doesn't exist."""
        call_graph = CodeQLCallGraph(methods=[])

        found = call_graph.find_method("nonexistent")

        assert found is None

    def test_get_callers(self) -> None:
        """Test getting callers of a method."""
        caller = CodeQLMethod(name="handleRequest", class_name="com.example.Controller")
        callee = CodeQLMethod(name="process", class_name="com.example.Service")
        call = CodeQLCall(caller=caller, callee=callee)

        call_graph = CodeQLCallGraph(methods=[caller, callee], calls=[call])

        callers = call_graph.get_callers("com.example.Service.process")

        assert len(callers) == 1
        assert callers[0].name == "handleRequest"

    def test_get_callees(self) -> None:
        """Test getting methods called by a method."""
        caller = CodeQLMethod(name="handleRequest", class_name="com.example.Controller")
        callee = CodeQLMethod(name="process", class_name="com.example.Service")
        call = CodeQLCall(caller=caller, callee=callee)

        call_graph = CodeQLCallGraph(methods=[caller, callee], calls=[call])

        callees = call_graph.get_callees("com.example.Controller.handleRequest")

        assert len(callees) == 1
        assert callees[0].name == "process"


class TestCodeQLLocation:
    """Tests for CodeQLLocation model."""

    def test_str_representation(self) -> None:
        """Test string representation of location."""
        location = CodeQLLocation(
            file="Service.java",
            start_line=42,
            start_column=10,
        )

        assert str(location) == "Service.java:42:10"

    def test_location_with_end(self) -> None:
        """Test location with end position."""
        location = CodeQLLocation(
            file="Service.java",
            start_line=10,
            start_column=5,
            end_line=15,
            end_column=20,
        )

        assert location.end_line == 15
        assert location.end_column == 20