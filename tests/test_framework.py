from scour_complete import run_batch, run_case
from hec14_outlet_protection import EXAMPLES
from dataclasses import asdict

def test_legacy_not_promoted():
    result = run_case(asdict(EXAMPLES["culv1"]))
    assert result["recommendations"] == []
    assert result["blockers"]
    assert result["report"]

def test_batch_isolates_invalid_case():
    result = run_batch([{}, asdict(EXAMPLES["culv1"])])
    assert "error" in result[0]
    assert "legacy" in result[1]
