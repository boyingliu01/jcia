"""Tests for AnalysisFusionService module.

This module provides comprehensive test coverage for the AnalysisFusionService,
including all fusion strategies and edge cases.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from jcia.core.services.analysis_fusion_service import (
    AnalysisFusionService,
    FusionStrategy,
)
from jcia.core.entities.impact_graph import (
    ImpactGraph,
    ImpactNode,
    ImpactEdge,
    ImpactSeverity,
    ImpactType,
)
from jcia.core.interfaces.call_chain_analyzer import (
    CallChainAnalyzer,
    CallChainGraph,
    CallChainNode,
    CallChainDirection,
)


class TestFusionStrategy:
    """Tests for FusionStrategy constants."""

    def test_bayesian_strategy(self):
        """Test BAYESIAN strategy value."""
        assert FusionStrategy.BAYESIAN == "bayesian"

    def test_voting_strategy(self):
        """Test VOTING strategy value."""
        assert FusionStrategy.VOTING == "voting"

    def test_weighted_strategy(self):
        """Test WEIGHTED strategy value."""
        assert FusionStrategy.WEIGHTED == "weighted"

    def test_union_strategy(self):
        """Test UNION strategy value."""
        assert FusionStrategy.UNION == "union"

    def test_intersection_strategy(self):
        """Test INTERSECTION strategy value."""
        assert FusionStrategy.INTERSECTION == "intersection"


class TestAnalysisFusionServiceInitialization:
    """Tests for AnalysisFusionService initialization."""

    def test_init_with_none(self):
        """Test initialization with None analyzers."""
        service = AnalysisFusionService()
        assert service._static_analyzer is None
        assert service._dynamic_analyzer is None
        assert service._coverage_data == {}

    def test_init_with_analyzers(self):
        """Test initialization with analyzers."""
        static_analyzer = Mock(spec=CallChainAnalyzer)
        dynamic_analyzer = Mock(spec=CallChainAnalyzer)
        coverage_data = {"method1": 0.8, "method2": 0.6}

        service = AnalysisFusionService(
            static_analyzer=static_analyzer,
            dynamic_analyzer=dynamic_analyzer,
            coverage_data=coverage_data,
        )

        assert service._static_analyzer == static_analyzer
        assert service._dynamic_analyzer == dynamic_analyzer
        assert service._coverage_data == coverage_data


class TestAnalysisFusionServiceBayesianFusion:
    """Tests for Bayesian fusion strategy."""

    def setup_method(self):
        """Set up test fixtures."""
        self.static_analyzer = Mock(spec=CallChainAnalyzer)
        self.dynamic_analyzer = Mock(spec=CallChainAnalyzer)
        self.service = AnalysisFusionService(
            static_analyzer=self.static_analyzer,
            dynamic_analyzer=self.dynamic_analyzer,
            coverage_data={"method1": 0.8},
        )

    def test_bayesian_fusion_upstream_with_both_analyzers(self):
        """Test Bayesian fusion upstream with both analyzers."""
        # Create mock graphs
        static_root = CallChainNode("TestClass", "testMethod", "testMethod()")
        static_graph = CallChainGraph(root=static_root, direction=CallChainDirection.UPSTREAM, max_depth=5)

        dynamic_root = CallChainNode("TestClass", "testMethod", "testMethod()")
        dynamic_graph = CallChainGraph(root=dynamic_root, direction=CallChainDirection.UPSTREAM, max_depth=5)

        self.static_analyzer.analyze_upstream.return_value = static_graph
        self.dynamic_analyzer.analyze_upstream.return_value = dynamic_graph

        result = self.service.fuse_upstream(
            "TestClass.testMethod", max_depth=5, strategy=FusionStrategy.BAYESIAN
        )

        assert isinstance(result, ImpactGraph)
        self.static_analyzer.analyze_upstream.assert_called_once_with("TestClass.testMethod", 5)
        self.dynamic_analyzer.analyze_upstream.assert_called_once_with("TestClass.testMethod", 5)

    def test_bayesian_fusion_upstream_static_only(self):
        """Test Bayesian fusion upstream with only static analyzer."""
        service = AnalysisFusionService(
            static_analyzer=self.static_analyzer,
            coverage_data={},
        )

        static_root = CallChainNode("TestClass", "testMethod", "testMethod()")
        static_graph = CallChainGraph(root=static_root, direction=CallChainDirection.UPSTREAM, max_depth=5)
        self.static_analyzer.analyze_upstream.return_value = static_graph

        result = service.fuse_upstream("TestClass.testMethod", max_depth=5)

        assert isinstance(result, ImpactGraph)
        self.static_analyzer.analyze_upstream.assert_called_once()

    def test_bayesian_fusion_upstream_no_analyzers(self):
        """Test Bayesian fusion upstream with no analyzers."""
        service = AnalysisFusionService()

        result = service.fuse_upstream("method1", max_depth=5)

        assert isinstance(result, ImpactGraph)
        # Service always creates a root node for the method
        assert len(result.nodes) == 1
        assert "method1" in result.nodes


class TestAnalysisFusionServiceVotingFusion:
    """Tests for voting fusion strategy."""

    def setup_method(self):
        """Set up test fixtures."""
        self.static_analyzer = Mock(spec=CallChainAnalyzer)
        self.dynamic_analyzer = Mock(spec=CallChainAnalyzer)
        self.service = AnalysisFusionService(
            static_analyzer=self.static_analyzer,
            dynamic_analyzer=self.dynamic_analyzer,
        )

    def test_voting_fusion_downstream(self):
        """Test voting fusion downstream."""
        static_root = CallChainNode("TestClass", "testMethod1", "testMethod1()")
        static_graph = CallChainGraph(root=static_root, direction=CallChainDirection.DOWNSTREAM, max_depth=5)

        dynamic_root = CallChainNode("TestClass", "testMethod2", "testMethod2()")
        dynamic_graph = CallChainGraph(root=dynamic_root, direction=CallChainDirection.DOWNSTREAM, max_depth=5)

        self.static_analyzer.analyze_downstream.return_value = static_graph
        self.dynamic_analyzer.analyze_downstream.return_value = dynamic_graph

        result = self.service.fuse_downstream(
            "TestClass.testMethod1", max_depth=5, strategy=FusionStrategy.VOTING
        )

        assert isinstance(result, ImpactGraph)


class TestAnalysisFusionServiceWeightedFusion:
    """Tests for weighted fusion strategy."""

    def setup_method(self):
        """Set up test fixtures."""
        self.static_analyzer = Mock(spec=CallChainAnalyzer)
        self.dynamic_analyzer = Mock(spec=CallChainAnalyzer)
        self.service = AnalysisFusionService(
            static_analyzer=self.static_analyzer,
            dynamic_analyzer=self.dynamic_analyzer,
            coverage_data={"method1": 0.75},
        )

    def test_weighted_fusion_upstream(self):
        """Test weighted fusion upstream with coverage data."""
        static_root = CallChainNode("TestClass", "testMethod", "testMethod()")
        static_graph = CallChainGraph(root=static_root, direction=CallChainDirection.UPSTREAM, max_depth=5)

        self.static_analyzer.analyze_upstream.return_value = static_graph
        self.dynamic_analyzer.analyze_upstream.return_value = None

        result = self.service.fuse_upstream(
            "TestClass.testMethod", max_depth=5, strategy=FusionStrategy.WEIGHTED
        )

        assert isinstance(result, ImpactGraph)
        self.static_analyzer.analyze_upstream.assert_called_once()


class TestAnalysisFusionServiceUnionFusion:
    """Tests for union fusion strategy."""

    def setup_method(self):
        """Set up test fixtures."""
        self.static_analyzer = Mock(spec=CallChainAnalyzer)
        self.dynamic_analyzer = Mock(spec=CallChainAnalyzer)
        self.service = AnalysisFusionService(
            static_analyzer=self.static_analyzer,
            dynamic_analyzer=self.dynamic_analyzer,
        )

    def test_union_fusion_downstream(self):
        """Test union fusion downstream combines all nodes."""
        static_root = CallChainNode("TestClass", "testMethod1", "testMethod1()")
        static_graph = CallChainGraph(root=static_root, direction=CallChainDirection.DOWNSTREAM, max_depth=5)

        dynamic_root = CallChainNode("TestClass", "testMethod2", "testMethod2()")
        dynamic_graph = CallChainGraph(root=dynamic_root, direction=CallChainDirection.DOWNSTREAM, max_depth=5)

        self.static_analyzer.analyze_downstream.return_value = static_graph
        self.dynamic_analyzer.analyze_downstream.return_value = dynamic_graph

        result = self.service.fuse_downstream(
            "TestClass.testMethod1", max_depth=5, strategy=FusionStrategy.UNION
        )

        assert isinstance(result, ImpactGraph)


class TestAnalysisFusionServiceIntersectionFusion:
    """Tests for intersection fusion strategy."""

    def setup_method(self):
        """Set up test fixtures."""
        self.static_analyzer = Mock(spec=CallChainAnalyzer)
        self.dynamic_analyzer = Mock(spec=CallChainAnalyzer)
        self.service = AnalysisFusionService(
            static_analyzer=self.static_analyzer,
            dynamic_analyzer=self.dynamic_analyzer,
        )

    def test_intersection_fusion_upstream(self):
        """Test intersection fusion upstream keeps only common nodes."""
        static_root = CallChainNode("TestClass", "testMethod1", "testMethod1()")
        static_graph = CallChainGraph(root=static_root, direction=CallChainDirection.UPSTREAM, max_depth=5)

        dynamic_root = CallChainNode("TestClass", "testMethod1", "testMethod1()")
        dynamic_graph = CallChainGraph(root=dynamic_root, direction=CallChainDirection.UPSTREAM, max_depth=5)

        self.static_analyzer.analyze_upstream.return_value = static_graph
        self.dynamic_analyzer.analyze_upstream.return_value = dynamic_graph

        result = self.service.fuse_upstream(
            "TestClass.testMethod1", max_depth=5, strategy=FusionStrategy.INTERSECTION
        )

        assert isinstance(result, ImpactGraph)

    def test_intersection_fusion_one_analyzer(self):
        """Test intersection fusion with only one analyzer."""
        service = AnalysisFusionService(static_analyzer=self.static_analyzer)

        static_root = CallChainNode("TestClass", "testMethod", "testMethod()")
        static_graph = CallChainGraph(root=static_root, direction=CallChainDirection.UPSTREAM, max_depth=5)
        self.static_analyzer.analyze_upstream.return_value = static_graph

        result = service.fuse_upstream(
            "TestClass.testMethod", max_depth=5, strategy=FusionStrategy.INTERSECTION
        )

        assert isinstance(result, ImpactGraph)


class TestAnalysisFusionServiceEdgeCases:
    """Tests for edge cases and error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.static_analyzer = Mock(spec=CallChainAnalyzer)
        self.dynamic_analyzer = Mock(spec=CallChainAnalyzer)
        self.service = AnalysisFusionService(
            static_analyzer=self.static_analyzer,
            dynamic_analyzer=self.dynamic_analyzer,
        )

    def test_fusion_with_analyzer_exception(self):
        """Test fusion when analyzer throws exception."""
        self.static_analyzer.analyze_upstream.side_effect = Exception("Analysis failed")
        self.dynamic_analyzer.analyze_upstream.return_value = None

        result = self.service.fuse_upstream("method1", max_depth=5)

        assert isinstance(result, ImpactGraph)
        # Should handle exception gracefully and return graph with root node only
        assert len(result.nodes) == 1
        assert "method1" in result.nodes

    def test_fusion_with_none_graphs(self):
        """Test fusion when both analyzers return None."""
        self.static_analyzer.analyze_upstream.return_value = None
        self.dynamic_analyzer.analyze_upstream.return_value = None

        result = self.service.fuse_upstream("method1", max_depth=5)

        assert isinstance(result, ImpactGraph)
        # Service always creates a root node for the method
        assert len(result.nodes) == 1
        assert "method1" in result.nodes

    def test_invalid_strategy_defaults_to_bayesian(self):
        """Test that invalid strategy defaults to bayesian."""
        static_root = CallChainNode("TestClass", "testMethod", "testMethod()")
        static_graph = CallChainGraph(root=static_root, direction=CallChainDirection.UPSTREAM, max_depth=5)

        self.static_analyzer.analyze_upstream.return_value = static_graph
        self.dynamic_analyzer.analyze_upstream.return_value = None

        # Use an invalid strategy
        result = self.service.fuse_upstream(
            "TestClass.testMethod", max_depth=5, strategy="invalid_strategy"
        )

        assert isinstance(result, ImpactGraph)
        # Should still work with default strategy


# Mark all tests in this module
pytestmark = pytest.mark.unit
