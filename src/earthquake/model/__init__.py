"""
Earthquake expected data calculator.

Reference: https://github.com/ExpTechTW/TREM-tauri/blob/main/src/scripts/helper/utils.ts
"""

from .intensity import calculate_expected_intensity, round_intensity
from .speed import speed_model

__all__ = ("calculate_expected_intensity", "round_intensity", "speed_model")
