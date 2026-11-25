import pytest
from methods_apron import apron_d50
from scour_complete import run_case
from hec14_outlet_protection import EXAMPLES, riprap_d50_velocity
from dataclasses import asdict

@pytest.mark.parametrize("case", ["culv1", "culv2"])
def test_regression_cases_available(case):
    result = run_case(asdict(EXAMPLES[case]))
    assert result["report"]
    assert not result["recommendations"]

def test_fhwa_published_apron():
    result = apron_d50(85, 5, 1.6)
    assert result["tailwater_used_ft"] == 2
    assert result["d50_ft"] == pytest.approx(0.43, abs=0.005)

def test_manual_eq106():
    assert riprap_d50_velocity(10, 32.2, 2.65) == pytest.approx(0.6512, abs=0.0001)

def test_high_tailwater_rejected():
    with pytest.raises(ValueError):
        apron_d50(85, 5, 6)
