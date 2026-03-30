"""CodeQL adapter for semantic code analysis.

This module provides integration with CodeQL for advanced code analysis,
including call graph extraction, data flow analysis, and security scanning.
"""

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

from jcia.adapters.tools.codeql_models import (
    CodeQLAnalysisResult,
    CodeQLAnalysisStatus,
    CodeQLCall,
    CodeQLCallGraph,
    CodeQLDataFlowPath,
    CodeQLFinding,
    CodeQLFindingSeverity,
    CodeQLLocation,
    CodeQLMethod,
)
from jcia.core.interfaces.call_chain_analyzer import (
    AnalyzerType,
    CallChainAnalyzer,
    CallChainDirection,
    CallChainGraph,
    CallChainNode,
)

logger = logging.getLogger(__name__)

# Default QL queries for call graph extraction
CALL_GRAPH_QUERY = """
/**
 * @name Call Graph Extraction
 * @description Extracts method call relationships for impact analysis
 * @kind graph
 * @id java/call-graph-extraction
 */

import java

from Callable caller, Callable callee, MethodCall call
where call.getCallee() = callee and call.getCaller() = caller
select caller as caller, callee as callee, call as call
"""

METHOD_DECLARATIONS_QUERY = """
/**
 * @name Method Declarations
 * @description Extracts all method declarations
 * @kind table
 * @id java/method-declarations
 */

import java

from Callable method
select method.getName() as name,
       method.getSignature() as signature,
       method.getDeclaringType().getQualifiedName() as class_name,
       method.getFile().getRelativePath() as file,
       method.getLocation().getStartLine() as line
"""

ENTRY_POINTS_QUERY = """
/**
 * @name Entry Points
 * @description Identifies potential entry points (public methods, controllers, etc.)
 * @kind table
 * @id java/entry-points
 */

import java

from Callable method
where
  method.isPublic() and
  (
    method.getDeclaringType().getQualifiedName().matches("%Controller%") or
    method.getDeclaringType().getQualifiedName().matches("%Service%") or
    method.getAnAnnotation().getType().getName().matches("%Mapping%") or
    method.getName() = "main"
  )
select method.getName() as name,
       method.getDeclaringType().getQualifiedName() as class_name
"""


class CodeQLAdapter(CallChainAnalyzer):
    """CodeQL-based call chain analyzer for Java projects.

    This adapter uses CodeQL's semantic analysis capabilities to extract
    accurate call graphs, detect data flows, and identify security issues.

    Example:
        ```python
        adapter = CodeQLAdapter(repo_path="/path/to/java/project")
        adapter.create_database()
        graph = adapter.analyze_downstream("com.example.Service.process")
        ```
    """

    def __init__(
        self,
        repo_path: str,
        codeql_path: str | None = None,
        working_dir: Path | None = None,
        max_depth: int = 10,
    ) -> None:
        """Initialize the CodeQL adapter.

        Args:
            repo_path: Path to the Java repository
            codeql_path: Path to CodeQL CLI (auto-detected if None)
            working_dir: Working directory for CodeQL databases
            max_depth: Maximum call chain depth
        """
        self._repo_path = Path(repo_path).resolve()
        self._max_depth = max_depth
        self._working_dir = working_dir or (self._repo_path / ".jcia" / "codeql")
        self._working_dir.mkdir(parents=True, exist_ok=True)

        # Find CodeQL CLI
        self._codeql_path = codeql_path or self._find_codeql()
        if not self._codeql_path:
            logger.warning(
                "CodeQL CLI not found. Please install CodeQL or provide codeql_path."
            )

        # Database path
        self._database_path: Path | None = None

        # Cached analysis results
        self._call_graph: CodeQLCallGraph | None = None
        self._analysis_result: CodeQLAnalysisResult | None = None

        logger.info(f"CodeQLAdapter initialized for {self._repo_path}")

    @property
    def analyzer_type(self) -> AnalyzerType:
        """Return the analyzer type."""
        return AnalyzerType.STATIC

    @property
    def supports_cross_service(self) -> bool:
        """Whether this analyzer supports cross-service analysis."""
        return False

    def _find_codeql(self) -> str | None:
        """Find CodeQL CLI in PATH or common locations.

        Returns:
            Path to CodeQL CLI or None if not found
        """
        # Try to find in PATH
        codeql = shutil.which("codeql")
        if codeql:
            return codeql

        # Try common installation locations
        common_paths = [
            Path.home() / "codeql" / "codeql",
            Path("/usr/local/bin/codeql"),
            Path("/opt/codeql/codeql"),
            Path("C:/Program Files/CodeQL/codeql.exe"),
        ]

        for path in common_paths:
            if path.exists():
                return str(path)

        return None

    def is_available(self) -> bool:
        """Check if CodeQL is available.

        Returns:
            True if CodeQL CLI is found
        """
        return self._codeql_path is not None

    def create_database(
        self,
        source_root: Path | None = None,
        overwrite: bool = False,
        timeout: int = 600,
    ) -> Path:
        """Create a CodeQL database for the repository.

        Args:
            source_root: Source root directory (default: repo_path/src/main/java)
            overwrite: Whether to overwrite existing database
            timeout: Timeout in seconds

        Returns:
            Path to the created database

        Raises:
            RuntimeError: If CodeQL is not available or database creation fails
        """
        if not self._codeql_path:
            raise RuntimeError("CodeQL CLI not found")

        source = source_root or (self._repo_path / "src" / "main" / "java")
        if not source.exists():
            source = self._repo_path

        db_path = self._working_dir / "codeql-db"

        # Check if database already exists
        if db_path.exists() and not overwrite:
            logger.info(f"Using existing CodeQL database at {db_path}")
            self._database_path = db_path
            return db_path

        # Remove existing database if overwrite
        if db_path.exists():
            shutil.rmtree(db_path)

        # Create database
        cmd = [
            self._codeql_path,
            "database",
            "create",
            str(db_path),
            "--language=java",
            f"--source-root={source}",
            "--overwrite",
        ]

        logger.info(f"Creating CodeQL database at {db_path}")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self._repo_path,
            )

            if result.returncode != 0:
                logger.error(f"CodeQL database creation failed: {result.stderr}")
                raise RuntimeError(f"Failed to create CodeQL database: {result.stderr}")

            self._database_path = db_path
            logger.info(f"CodeQL database created successfully at {db_path}")
            return db_path

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"CodeQL database creation timed out after {timeout}s") from None

    def _run_query(
        self,
        query: str,
        output_format: str = "json",
    ) -> dict[str, Any]:
        """Run a CodeQL query and return results.

        Args:
            query: QL query string
            output_format: Output format (json, csv, etc.)

        Returns:
            Query results as dictionary

        Raises:
            RuntimeError: If query execution fails
        """
        if not self._database_path:
            raise RuntimeError("CodeQL database not created. Call create_database() first.")

        if not self._codeql_path:
            raise RuntimeError("CodeQL CLI not found")

        # Write query to temporary file
        query_file = self._working_dir / "temp_query.ql"
        query_file.write_text(query)

        # Output file
        output_file = self._working_dir / "query_results.json"

        cmd = [
            self._codeql_path,
            "database",
            "run-queries",
            str(self._database_path),
            str(query_file),
            "--format", output_format,
            "--output", str(output_file),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode != 0:
                logger.error(f"CodeQL query failed: {result.stderr}")
                raise RuntimeError(f"CodeQL query failed: {result.stderr}")

            # Read results
            if output_file.exists():
                results = json.loads(output_file.read_text())
                return results

            return {}

        except subprocess.TimeoutExpired:
            raise RuntimeError("CodeQL query timed out") from None

    def analyze_database(self) -> CodeQLAnalysisResult:
        """Perform full analysis on the CodeQL database.

        Returns:
            CodeQLAnalysisResult with call graph, findings, and data flows
        """
        if not self._database_path:
            # Try to create database
            try:
                self.create_database()
            except RuntimeError as e:
                return CodeQLAnalysisResult(
                    status=CodeQLAnalysisStatus.DATABASE_NOT_FOUND,
                    error_message=str(e),
                )

        try:
            # Extract call graph
            call_graph = self._extract_call_graph()

            # Run security queries
            findings = self._run_security_queries()

            # Create result
            self._analysis_result = CodeQLAnalysisResult(
                status=CodeQLAnalysisStatus.SUCCESS,
                call_graph=call_graph,
                findings=findings,
                database_path=self._database_path,
            )

            self._call_graph = call_graph
            return self._analysis_result

        except Exception as e:
            logger.exception("CodeQL analysis failed")
            return CodeQLAnalysisResult(
                status=CodeQLAnalysisStatus.FAILED,
                error_message=str(e),
            )

    def _extract_call_graph(self) -> CodeQLCallGraph:
        """Extract call graph from CodeQL database.

        Returns:
            CodeQLCallGraph with methods and calls
        """
        call_graph = CodeQLCallGraph()

        # Extract method declarations
        try:
            method_results = self._run_query(METHOD_DECLARATIONS_QUERY)

            for row in method_results.get("tuples", []):
                method = CodeQLMethod(
                    name=row.get("name", ""),
                    signature=row.get("signature"),
                    class_name=row.get("class_name"),
                    file=row.get("file"),
                    line=row.get("line"),
                )
                call_graph.methods.append(method)
        except Exception as e:
            logger.warning(f"Failed to extract method declarations: {e}")

        # Extract call relationships
        try:
            call_results = self._run_query(CALL_GRAPH_QUERY)

            for row in call_results.get("tuples", []):
                caller_data = row[0] if len(row) > 0 else {}
                callee_data = row[1] if len(row) > 1 else {}

                caller = CodeQLMethod(
                    name=caller_data.get("name", ""),
                    class_name=caller_data.get("class_name"),
                )
                callee = CodeQLMethod(
                    name=callee_data.get("name", ""),
                    class_name=callee_data.get("class_name"),
                )

                call = CodeQLCall(caller=caller, callee=callee)
                call_graph.calls.append(call)
        except Exception as e:
            logger.warning(f"Failed to extract call relationships: {e}")

        # Extract entry points
        try:
            entry_results = self._run_query(ENTRY_POINTS_QUERY)

            for row in entry_results.get("tuples", []):
                method = call_graph.find_method(row.get("name", ""))
                if method:
                    call_graph.entry_points.append(method)
        except Exception as e:
            logger.warning(f"Failed to extract entry points: {e}")

        logger.info(
            f"Extracted call graph: {len(call_graph.methods)} methods, "
            f"{len(call_graph.calls)} calls"
        )
        return call_graph

    def _run_security_queries(self) -> list[CodeQLFinding]:
        """Run security-focused CodeQL queries.

        Returns:
            List of security findings
        """
        findings: list[CodeQLFinding] = []

        # Run default security suite
        if not self._codeql_path or not self._database_path:
            return findings

        cmd = [
            self._codeql_path,
            "database",
            "analyze",
            str(self._database_path),
            "java-security-and-quality",
            "--format", "json",
            "--output", str(self._working_dir / "security_results.json"),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
            )

            if result.returncode == 0:
                output_file = self._working_dir / "security_results.json"
                if output_file.exists():
                    results = json.loads(output_file.read_text())

                    for sarif_run in results.get("runs", []):
                        for result_item in sarif_run.get("results", []):
                            finding = self._parse_sarif_result(result_item, sarif_run)
                            if finding:
                                findings.append(finding)

        except Exception as e:
            logger.warning(f"Security query execution failed: {e}")

        logger.info(f"Found {len(findings)} security findings")
        return findings

    def _parse_sarif_result(
        self,
        result: dict[str, Any],
        run: dict[str, Any],
    ) -> CodeQLFinding | None:
        """Parse a SARIF result into a CodeQLFinding.

        Args:
            result: SARIF result object
            run: SARIF run object (contains rule definitions)

        Returns:
            CodeQLFinding or None if parsing fails
        """
        try:
            rule_id = result.get("ruleId", "")
            rule_index = result.get("ruleIndex", 0)
            rules = run.get("tool", {}).get("driver", {}).get("rules", [])
            rule = rules[rule_index] if rule_index < len(rules) else {}

            message = result.get("message", {}).get("text", "")

            # Get location
            locations = result.get("locations", [])
            if not locations:
                return None

            physical_location = locations[0].get("physicalLocation", {})
            artifact = physical_location.get("artifactLocation", {})
            region = physical_location.get("region", {})

            location = CodeQLLocation(
                file=artifact.get("uri", ""),
                start_line=region.get("startLine", 0),
                start_column=region.get("startColumn", 0),
                end_line=region.get("endLine"),
                end_column=region.get("endColumn"),
            )

            # Map severity
            level = result.get("level", "note")
            severity_map = {
                "error": CodeQLFindingSeverity.ERROR,
                "warning": CodeQLFindingSeverity.WARNING,
                "note": CodeQLFindingSeverity.NOTE,
            }
            severity = severity_map.get(level, CodeQLFindingSeverity.RECOMMENDATION)

            return CodeQLFinding(
                rule_id=rule_id,
                rule_name=rule.get("name", rule_id),
                severity=severity,
                message=message,
                location=location,
            )

        except Exception as e:
            logger.debug(f"Failed to parse SARIF result: {e}")
            return None

    def analyze_upstream(self, method: str, max_depth: int = 10) -> CallChainGraph:
        """Analyze upstream callers of a method.

        Args:
            method: Method name (fully qualified)
            max_depth: Maximum depth to trace

        Returns:
            CallChainGraph with upstream callers
        """
        logger.debug(f"Analyzing upstream for method: {method}")

        # Ensure analysis is done
        if not self._call_graph:
            self.analyze_database()

        if not self._call_graph:
            return self._create_empty_graph(method, CallChainDirection.UPSTREAM)

        # Parse method name
        class_name, method_name = self._parse_method(method)

        # Create root node
        root_node = CallChainNode(
            class_name=class_name or "",
            method_name=method_name,
        )
        root_node.metadata["call_depth"] = 0
        root_node.metadata["severity"] = "HIGH"

        graph = CallChainGraph(
            root=root_node,
            direction=CallChainDirection.UPSTREAM,
            max_depth=max_depth,
        )

        # Find callers using BFS
        visited: set[str] = set()
        queue: list[tuple[str, int, CallChainNode]] = [(method, 0, root_node)]

        while queue:
            current_method, depth, parent_node = queue.pop(0)

            if depth >= max_depth:
                continue

            if current_method in visited:
                continue

            visited.add(current_method)

            # Get callers from CodeQL call graph
            callers = self._call_graph.get_callers(current_method)

            for caller in callers:
                caller_key = caller.full_name
                if caller_key not in visited:
                    caller_node = CallChainNode(
                        class_name=caller.class_name or "",
                        method_name=caller.name,
                    )
                    caller_node.metadata["call_depth"] = depth + 1
                    caller_node.metadata["severity"] = self._get_severity_by_depth(depth + 1)
                    parent_node.children.append(caller_node)
                    queue.append((caller_key, depth + 1, caller_node))

        return graph

    def analyze_downstream(self, method: str, max_depth: int = 10) -> CallChainGraph:
        """Analyze downstream callees of a method.

        Args:
            method: Method name (fully qualified)
            max_depth: Maximum depth to trace

        Returns:
            CallChainGraph with downstream callees
        """
        logger.debug(f"Analyzing downstream for method: {method}")

        # Ensure analysis is done
        if not self._call_graph:
            self.analyze_database()

        if not self._call_graph:
            return self._create_empty_graph(method, CallChainDirection.DOWNSTREAM)

        # Parse method name
        class_name, method_name = self._parse_method(method)

        # Create root node
        root_node = CallChainNode(
            class_name=class_name or "",
            method_name=method_name,
        )
        root_node.metadata["call_depth"] = 0
        root_node.metadata["severity"] = "HIGH"

        graph = CallChainGraph(
            root=root_node,
            direction=CallChainDirection.DOWNSTREAM,
            max_depth=max_depth,
        )

        # Find callees using BFS
        visited: set[str] = set()
        queue: list[tuple[str, int, CallChainNode]] = [(method, 0, root_node)]

        while queue:
            current_method, depth, parent_node = queue.pop(0)

            if depth >= max_depth:
                continue

            if current_method in visited:
                continue

            visited.add(current_method)

            # Get callees from CodeQL call graph
            callees = self._call_graph.get_callees(current_method)

            for callee in callees:
                callee_key = callee.full_name
                if callee_key not in visited:
                    callee_node = CallChainNode(
                        class_name=callee.class_name or "",
                        method_name=callee.name,
                    )
                    callee_node.metadata["call_depth"] = depth + 1
                    callee_node.metadata["severity"] = self._get_severity_by_depth(depth + 1)
                    parent_node.children.append(callee_node)
                    queue.append((callee_key, depth + 1, callee_node))

        return graph

    def analyze_both_directions(
        self, method: str, max_depth: int = 10
    ) -> tuple[CallChainGraph, CallChainGraph]:
        """Analyze both upstream and downstream.

        Args:
            method: Method name (fully qualified)
            max_depth: Maximum depth to trace

        Returns:
            Tuple of (upstream graph, downstream graph)
        """
        upstream = self.analyze_upstream(method, max_depth)
        downstream = self.analyze_downstream(method, max_depth)
        return upstream, downstream

    def build_full_graph(self) -> CallChainGraph:
        """Build the complete call graph.

        Returns:
            CallChainGraph with all methods and calls
        """
        # Ensure analysis is done
        if not self._call_graph:
            self.analyze_database()

        if not self._call_graph:
            root_node = CallChainNode(class_name="", method_name="__empty__")
            return CallChainGraph(
                root=root_node,
                direction=CallChainDirection.BOTH,
                max_depth=self._max_depth,
            )

        # Create virtual root
        root_node = CallChainNode(
            class_name="",
            method_name="__full_graph__",
        )
        root_node.metadata["call_depth"] = 0
        root_node.metadata["severity"] = "LOW"

        graph = CallChainGraph(
            root=root_node,
            direction=CallChainDirection.BOTH,
            max_depth=self._max_depth,
        )

        # Add all methods as children of root
        for method in self._call_graph.methods:
            method_node = CallChainNode(
                class_name=method.class_name or "",
                method_name=method.name,
            )
            method_node.metadata["call_depth"] = 1
            method_node.metadata["severity"] = "LOW"
            root_node.children.append(method_node)

        return graph

    def _parse_method(self, method: str) -> tuple[str | None, str]:
        """Parse a fully qualified method name.

        Args:
            method: Method name (e.g., "com.example.Service.process")

        Returns:
            Tuple of (class_name, method_name)
        """
        if "." in method:
            parts = method.rsplit(".", 1)
            return parts[0], parts[1]
        return None, method

    def _create_empty_graph(
        self, method: str, direction: CallChainDirection
    ) -> CallChainGraph:
        """Create an empty call graph with just the root node.

        Args:
            method: Method name
            direction: Graph direction

        Returns:
            Empty CallChainGraph
        """
        class_name, method_name = self._parse_method(method)
        root_node = CallChainNode(
            class_name=class_name or "",
            method_name=method_name,
        )
        root_node.metadata["call_depth"] = 0
        return CallChainGraph(
            root=root_node,
            direction=direction,
            max_depth=self._max_depth,
        )

    def _get_severity_by_depth(self, depth: int) -> str:
        """Get severity based on call depth.

        Args:
            depth: Call depth

        Returns:
            Severity string
        """
        if depth == 0:
            return "HIGH"
        if depth == 1:
            return "MEDIUM"
        return "LOW"

    def get_security_findings(self) -> list[CodeQLFinding]:
        """Get all security findings from the last analysis.

        Returns:
            List of CodeQLFinding objects
        """
        if not self._analysis_result:
            self.analyze_database()
        return self._analysis_result.findings if self._analysis_result else []

    def get_data_flows(self) -> list[CodeQLDataFlowPath]:
        """Get all data flow paths from the last analysis.

        Returns:
            List of CodeQLDataFlowPath objects
        """
        if not self._analysis_result:
            self.analyze_database()
        return self._analysis_result.data_flows if self._analysis_result else []

    def cleanup(self) -> None:
        """Clean up temporary files and databases."""
        if self._working_dir.exists():
            shutil.rmtree(self._working_dir)
            logger.info(f"Cleaned up CodeQL working directory: {self._working_dir}")
        self._database_path = None
        self._call_graph = None
        self._analysis_result = None
