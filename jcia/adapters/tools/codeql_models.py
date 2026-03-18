"""CodeQL analysis data models.

This module provides data models for CodeQL analysis results,
including call graph, data flow, and security findings.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class CodeQLAnalysisStatus(Enum):
    """Status of CodeQL analysis."""

    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    DATABASE_NOT_FOUND = "database_not_found"
    CODEQL_NOT_FOUND = "codeql_not_found"


class CodeQLFindingSeverity(Enum):
    """Severity levels for CodeQL findings."""

    ERROR = "error"
    WARNING = "warning"
    NOTE = "note"
    RECOMMENDATION = "recommendation"


@dataclass
class CodeQLLocation:
    """Source code location from CodeQL analysis.

    Attributes:
        file: Source file path
        start_line: Start line number
        start_column: Start column number
        end_line: End line number (optional)
        end_column: End column number (optional)
    """

    file: str
    start_line: int
    start_column: int
    end_line: int | None = None
    end_column: int | None = None

    def __str__(self) -> str:
        """Return string representation."""
        return f"{self.file}:{self.start_line}:{self.start_column}"


@dataclass
class CodeQLMethod:
    """Method information from CodeQL analysis.

    Attributes:
        name: Method name
        signature: Full method signature
        class_name: Containing class name (fully qualified)
        file: Source file path
        line: Line number
        is_static: Whether the method is static
        is_constructor: Whether this is a constructor
        modifiers: List of modifiers (public, private, etc.)
    """

    name: str
    signature: str | None = None
    class_name: str | None = None
    file: str | None = None
    line: int | None = None
    is_static: bool = False
    is_constructor: bool = False
    modifiers: list[str] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        """Return fully qualified method name."""
        if self.class_name:
            return f"{self.class_name}.{self.name}"
        return self.name

    def to_call_chain_format(self) -> str:
        """Convert to call chain analysis format."""
        if self.signature:
            return f"{self.full_name}{self.signature}"
        return self.full_name


@dataclass
class CodeQLCall:
    """Method call information from CodeQL analysis.

    Attributes:
        caller: Calling method
        callee: Called method
        location: Source location of the call
        is_virtual: Whether this is a virtual/polymorphic call
        is_static: Whether this is a static method call
    """

    caller: CodeQLMethod
    callee: CodeQLMethod
    location: CodeQLLocation | None = None
    is_virtual: bool = False
    is_static: bool = False


@dataclass
class CodeQLDataFlowPath:
    """Data flow path from CodeQL taint tracking.

    Attributes:
        source: Source location of tainted data
        sink: Sink location where data is used
        path: List of nodes in the flow path
        source_type: Type of source (user input, file, etc.)
        sink_type: Type of sink (sql, command, etc.)
    """

    source: CodeQLLocation
    sink: CodeQLLocation
    path: list[CodeQLLocation] = field(default_factory=list)
    source_type: str | None = None
    sink_type: str | None = None


@dataclass
class CodeQLFinding:
    """Security or quality finding from CodeQL analysis.

    Attributes:
        rule_id: CodeQL rule identifier
        rule_name: Human-readable rule name
        severity: Finding severity
        message: Description of the finding
        location: Source location
        path: Data flow path (for data flow findings)
        fix_suggestions: Suggested fixes
        metadata: Additional metadata
    """

    rule_id: str
    rule_name: str
    severity: CodeQLFindingSeverity
    message: str
    location: CodeQLLocation
    path: CodeQLDataFlowPath | None = None
    fix_suggestions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_security_finding(self) -> bool:
        """Check if this is a security-related finding."""
        security_prefixes = ("java/sql", "java/command", "java/xss", "java/csrf",
                           "java/path", "java/ldap", "java/ssrf", "java/unsafe")
        return any(self.rule_id.startswith(prefix) for prefix in security_prefixes)


@dataclass
class CodeQLCallGraph:
    """Call graph from CodeQL analysis.

    Attributes:
        methods: All methods in the codebase
        calls: All method calls
        entry_points: Identified entry point methods
        call_depths: Maximum call depth for each method
    """

    methods: list[CodeQLMethod] = field(default_factory=list)
    calls: list[CodeQLCall] = field(default_factory=list)
    entry_points: list[CodeQLMethod] = field(default_factory=list)
    call_depths: dict[str, int] = field(default_factory=dict)

    def find_method(self, name: str) -> CodeQLMethod | None:
        """Find a method by name.

        Args:
            name: Method name (simple or qualified)

        Returns:
            CodeQLMethod if found, None otherwise
        """
        # Try full name first
        for method in self.methods:
            if method.full_name == name:
                return method

        # Try simple name
        for method in self.methods:
            if method.name == name:
                return method

        return None

    def get_callers(self, method_name: str) -> list[CodeQLMethod]:
        """Get all callers of a method.

        Args:
            method_name: Target method name

        Returns:
            List of calling methods
        """
        callers = []
        for call in self.calls:
            if call.callee.full_name == method_name or call.callee.name == method_name:
                callers.append(call.caller)
        return callers

    def get_callees(self, method_name: str) -> list[CodeQLMethod]:
        """Get all methods called by a method.

        Args:
            method_name: Caller method name

        Returns:
            List of called methods
        """
        callees = []
        for call in self.calls:
            if call.caller.full_name == method_name or call.caller.name == method_name:
                callees.append(call.callee)
        return callees


@dataclass
class CodeQLAnalysisResult:
    """Complete result from CodeQL analysis.

    Attributes:
        status: Analysis status
        call_graph: Extracted call graph
        findings: Security and quality findings
        data_flows: Detected data flow paths
        duration_ms: Analysis duration in milliseconds
        error_message: Error message if failed
        database_path: Path to the CodeQL database
        metadata: Additional metadata
    """

    status: CodeQLAnalysisStatus
    call_graph: CodeQLCallGraph | None = None
    findings: list[CodeQLFinding] = field(default_factory=list)
    data_flows: list[CodeQLDataFlowPath] = field(default_factory=list)
    duration_ms: float = 0.0
    error_message: str | None = None
    database_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_successful(self) -> bool:
        """Check if analysis was successful."""
        return self.status == CodeQLAnalysisStatus.SUCCESS

    def get_security_findings(self) -> list[CodeQLFinding]:
        """Get all security-related findings."""
        return [f for f in self.findings if f.is_security_finding()]

    def get_high_severity_findings(self) -> list[CodeQLFinding]:
        """Get all high severity findings."""
        return [f for f in self.findings if f.severity == CodeQLFindingSeverity.ERROR]


@dataclass
class CodeQLDatabaseInfo:
    """Information about a CodeQL database.

    Attributes:
        path: Path to the database
        language: Database language (java, python, etc.)
        source_root: Original source root
        creation_time: Database creation time
        size_mb: Database size in megabytes
        version: CodeQL version used to create
    """

    path: Path
    language: str
    source_root: str
    creation_time: str | None = None
    size_mb: float = 0.0
    version: str | None = None

    def exists(self) -> bool:
        """Check if the database exists."""
        return self.path.exists()

    def is_valid(self) -> bool:
        """Check if the database is valid."""
        # Check for required database files
        db_files = ["codeql-database.yml"]
        return all((self.path / f).exists() for f in db_files)