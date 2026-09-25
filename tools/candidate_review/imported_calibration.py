"""Frozen controls for imported package review, behind the existing calibration edge (roadmap S-6.196).

The controls are engineering-authored fixtures in the imported layout, so no third-party bytes enter the repository.
They contribute zero library items. Each known-wrong control plants one defect an imported criterion names: a hidden
instruction aimed at the harness, a step that defeats the package's own purpose, a description the body does not
carry out, and filler too thin to help a harness. The two known-good controls are a complete skill and a complete
instruction file. Approval of a known-wrong control, or a control without a valid verdict, excludes the reviewer from
imported candidates in that run, exactly as for original packages.
"""
from __future__ import annotations

from pathlib import Path

from .imported import ImportedCatalogue
from .native_calibration import NativeCalibrationSet

IMPORTED_CALIBRATION_SET = "candidate_imported_review_calibration_set/v1"
IMPORTED_DEFAULT_SET = Path(__file__).resolve().parent / "resources/imported-calibration/calibration-set.json"


class ImportedCalibrationSet(NativeCalibrationSet):
    RECORD_TYPE = IMPORTED_CALIBRATION_SET
    CATALOGUE = ImportedCatalogue
