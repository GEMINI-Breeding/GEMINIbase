"""Tests for gemini.api.enums module."""
import pytest
from gemini.api.enums import (
    GEMINIDataFormat,
    GEMINISensorType,
    GEMINIDatasetType,
    GEMINIDataType,
    GEMINITraitLevel,
)


class TestGEMINIDataFormat:
    """Tests for the GEMINIDataFormat enum."""

    def test_default_value(self):
        assert GEMINIDataFormat.Default.value == 0

    def test_all_members_exist(self):
        expected = {
            "Default": 0, "TXT": 1, "JSON": 2, "CSV": 3, "TSV": 4,
            "XML": 5, "HTML": 6, "PDF": 7, "JPEG": 8, "PNG": 9,
            "GIF": 10, "BMP": 11, "TIFF": 12, "WAV": 13, "MP3": 14,
            "MPEG": 15, "AVI": 16, "MP4": 17, "OGG": 18, "WEBM": 19,
            "NPY": 20,
        }
        for name, value in expected.items():
            member = GEMINIDataFormat[name]
            assert member.value == value

    def test_member_count(self):
        assert len(GEMINIDataFormat) == 21

    def test_lookup_by_value(self):
        assert GEMINIDataFormat(3) == GEMINIDataFormat.CSV


class TestGEMINISensorType:
    """Tests for the GEMINISensorType enum."""

    def test_default_value(self):
        assert GEMINISensorType.Default.value == 0

    def test_all_members_exist(self):
        expected = {
            "Default": 0, "RGB": 1, "NIR": 2, "Thermal": 3,
            "Multispectral": 4, "Weather": 5, "GPS": 6, "Calibration": 7,
            "Depth": 8, "IMU": 9, "Disparity": 10, "Confidence": 11,
        }
        for name, value in expected.items():
            member = GEMINISensorType[name]
            assert member.value == value

    def test_member_count(self):
        assert len(GEMINISensorType) == 12

    def test_lookup_by_value(self):
        assert GEMINISensorType(1) == GEMINISensorType.RGB


class TestGEMINIDatasetType:
    """Tests for the GEMINIDatasetType enum."""

    def test_default_value(self):
        assert GEMINIDatasetType.Default.value == 0

    def test_all_members_exist(self):
        expected = {
            "Default": 0, "Sensor": 1, "Trait": 2, "Script": 3,
            "Model": 4, "Procedure": 5, "Other": 6,
        }
        for name, value in expected.items():
            member = GEMINIDatasetType[name]
            assert member.value == value

    def test_member_count(self):
        assert len(GEMINIDatasetType) == 7


class TestGEMINIDataType:
    """Tests for the GEMINIDataType enum."""

    def test_default_value(self):
        assert GEMINIDataType.Default.value == 0

    def test_all_members_exist(self):
        expected = {
            "Default": 0, "Text": 1, "Web": 2, "Document": 3,
            "Image": 4, "Audio": 5, "Video": 6, "Binary": 7, "Other": 8,
        }
        for name, value in expected.items():
            member = GEMINIDataType[name]
            assert member.value == value

    def test_member_count(self):
        assert len(GEMINIDataType) == 9


class TestGEMINITraitLevel:
    """Tests for the GEMINITraitLevel enum."""

    def test_default_value(self):
        assert GEMINITraitLevel.Default.value == 0

    def test_all_members_exist(self):
        expected = {"Default": 0, "Plot": 1, "Plant": 2}
        for name, value in expected.items():
            member = GEMINITraitLevel[name]
            assert member.value == value

    def test_member_count(self):
        assert len(GEMINITraitLevel) == 3
