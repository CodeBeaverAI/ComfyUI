import re
import pytest
from comfyui_version import __version__

def test_version_type():
    """Test that __version__ is a non-empty string."""
    assert isinstance(__version__, str), "__version__ should be a string"
    assert __version__, "__version__ should not be empty"

def test_version_format():
    """Test that __version__ matches semantic versioning format x.y.z."""
    pattern = r'^\d+\.\d+\.\d+$'
    assert re.match(pattern, __version__), f"__version__ '{__version__}' does not match format x.y.z"

def test_version_value():
    """Test that __version__ has the expected value."""
    expected_version = "0.3.19"
    assert __version__ == expected_version, f"Expected {expected_version}, got {__version__}"
def test_version_numeric_parts():
    """Test that __version__ splits into exactly three numeric components."""
    parts = __version__.split('.')
    assert len(parts) == 3, "Version should consist of three parts separated by '.'"
    for part in parts:
        assert part.isdigit(), f"Version component '{part}' is not numeric"
def test_no_leading_or_trailing_whitespace():
    """Test that __version__ does not have leading or trailing whitespace."""
    assert __version__ == __version__.strip(), "Version should not contain leading or trailing whitespace"
def test_version_non_negative_parts():
    """Test that each numeric part of __version__ is non-negative."""
    parts = __version__.split('.')
    for part in parts:
        value = int(part)
        assert value >= 0, f"Version part '{part}' is negative"
def test_version_tuple_conversion():
    """Test that __version__ can be converted to a tuple of integers (major, minor, patch)."""
    parts = __version__.split('.')
    version_tuple = tuple(int(part) for part in parts)
    assert version_tuple == (0, 3, 19), f"Version tuple {version_tuple} does not equal (0, 3, 19)"

def test_version_semantic_comparison():
    """Test a simple semantic version comparison by converting __version__ to a tuple and comparing with the next minor version."""
    parts = tuple(int(part) for part in __version__.split('.'))
    expected_next_minor = (parts[0], parts[1] + 1, 0)
    assert parts < expected_next_minor, "Current version should be less than the next minor version"
def test_version_round_trip():
    """Test that converting __version__ to a tuple and back to a string produces the original __version__."""
    parts = __version__.split('.')
    version_tuple = tuple(int(part) for part in parts)
    reconstructed = '.'.join(str(num) for num in version_tuple)
    assert reconstructed == __version__, f"Reconstructed version {reconstructed} does not match {__version__}"

def test_version_increment_patch():
    """Test that incrementing the patch part yields a version greater than the original semantically."""
    parts = __version__.split('.')
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    new_version_tuple = (major, minor, patch + 1)
    assert new_version_tuple > (major, minor, patch), "Incremented patch version should be greater than the original version"

def test_version_ordering():
    """Test that semantic version ordering is consistent when sorting a list of version strings."""
    versions = ["0.3.19", "0.3.20", "0.2.99", "1.0.0"]
    sorted_versions = sorted(versions, key=lambda v: tuple(int(x) for x in v.split('.')))
    expected_order = ["0.2.99", "0.3.19", "0.3.20", "1.0.0"]
    assert sorted_versions == expected_order, f"Sorted versions {sorted_versions} do not match expected order {expected_order}"

def test_version_compare_with_invalid_version(monkeypatch):
    """Test behavior when __version__ is temporarily set to an invalid version string."""
    import comfyui_version  # Import the module so monkeypatching the attribute affects it
    monkeypatch.setattr(comfyui_version, "__version__", "invalid.version")
    pattern = r'^\d+\.\d+\.\d+$'
    assert not re.match(pattern, comfyui_version.__version__), f"__version__ '{comfyui_version.__version__}' should not match the format x.y.z"