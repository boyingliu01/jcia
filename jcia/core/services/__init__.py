"""领域服务包."""

from jcia.core.services.analysis_fusion_service import AnalysisFusionService
from jcia.core.services.call_chain_builder import CallChainBuilder
from jcia.core.services.change_comparison_service import ChangeComparisonService
from jcia.core.services.impact_analysis_service import ImpactAnalysisService
from jcia.core.services.severity_calculator import (
    DimensionScore,
    MultiDimensionalSeverityCalculator,
    SeverityCalculationResult,
    SeverityDimension,
)
from jcia.core.services.severity_enhancer import SeverityEnhancer
from jcia.core.services.test_generator_service import TestGeneratorService
from jcia.core.services.test_selection_service import TestSelectionService

__all__ = [
    "AnalysisFusionService",
    "CallChainBuilder",
    "ChangeComparisonService",
    "DimensionScore",
    "ImpactAnalysisService",
    "MultiDimensionalSeverityCalculator",
    "SeverityCalculationResult",
    "SeverityDimension",
    "SeverityEnhancer",
    "TestGeneratorService",
    "TestSelectionService",
]
