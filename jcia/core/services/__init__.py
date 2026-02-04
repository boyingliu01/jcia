"""领域服务包."""

from jcia.core.services.change_comparison_service import ChangeComparisonService
from jcia.core.services.impact_analysis_service import ImpactAnalysisService
from jcia.core.services.test_selection_service import TestSelectionService

__all__ = [
    "ChangeComparisonService",
    "ImpactAnalysisService",
    "TestSelectionService",
]
