from dataclasses import asdict

import pytest

from scour_complete import STATUS, run_case
from legacy.hec14_outlet_protection import EXAMPLES


def base(**changes):
    return {**asdict(EXAMPLES["culv1"]), **changes}


def test_status_on_standalone_report():
    case = run_case(base())
    assert case["report"].startswith(STATUS) and case["report"].endswith(STATUS)
    assert "option_1" not in case["legacy"]
    assert case["legacy_unverified_design_text"]["option_1"]
