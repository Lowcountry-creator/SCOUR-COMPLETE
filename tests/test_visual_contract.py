from dataclasses import asdict
from scour_complete import run_case
from hec14_outlet_protection import EXAMPLES
from visuals import export_velocity_plot

def test_velocity_plot(tmp_path):
    case = run_case(asdict(EXAMPLES["culv1"]))
    path = tmp_path / "velocity.png"
    export_velocity_plot(case, path)
    assert path.stat().st_size > 0
