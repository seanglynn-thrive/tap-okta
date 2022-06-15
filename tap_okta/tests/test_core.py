"""Tests standard tap features using the built-in SDK tests library."""

from singer_sdk.testing import get_standard_tap_tests
from tap_okta.tap import Tapokta
import os

SAMPLE_CONFIG = {
    "api_key": os.getenv("api_key"),
}


# Run standard built-in tap tests from the SDK:
def test_standard_tap_tests():
    """Run standard tap tests from the SDK."""
    print(f"SAMPLE_CONFIG: {SAMPLE_CONFIG}")
    tests = get_standard_tap_tests(Tapokta, config=SAMPLE_CONFIG)
    for test in tests:
        test()
