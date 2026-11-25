"""Regression tests: script output against the source workbook.

Expected values are the Excel-computed cells from
Outlet_Protection_Calcs (US176 Culverts 1, 2 and 4). Tolerances are tight
because the formulas are the same; any drift means a formula changed.
"""

import math

import pytest

import hec14_outlet_protection as h

REL = 1e-9


def close(a, b):
    return math.isclose(a, b, rel_tol=REL, abs_tol=1e-9)


# ---------------------------------------------------------------- Culvert 1


@pytest.fixture(scope="module")
def c1():
    return h.analyze(h.EXAMPLES["culv1"])


def test_c1_block2(c1):
    assert c1.D == 6
    assert close(c1.yc, 4.01683089043345)
    assert c1.regime == "Supercritical at brink; tailwater submerges jet"
    assert close(c1.Vo_check, 16.315306122449)
    assert c1.Vo_check_result == "OK"
    assert close(c1.Fr, 1.71875194603423)
    assert close(c1.TW_ye, 1.83571428571429)
    assert c1.tailwater_case == "High tailwater"


def test_c1_block3(c1):
    assert c1.apron_applicable.startswith("Not applicable")
    assert c1.basin_applicable == "Applicable, Fr < 3"
    assert c1.jump_basin == "Possible, Fr >= 1.7"


def test_c1_block4(c1):
    assert c1.C0_envelope == 2.4
    assert c1.C0_best_fit == 3
    t = c1.trial
    assert close(t.D50_ye, 0.267857142857143)
    assert close(t.hs_envelope, 1.82127899163151)
    assert close(t.hs_D50, 2.42837198884201)
    assert close(t.hs_best_fit, 0.141278991631508)
    assert t.result == "Valid basin"
    exp = {
        "A": (3.95512822630484, 7.91025645260969, "Valid basin"),
        "B": (1.82127899163151, 2.42837198884201, "Valid basin"),
        "C": (-0.408424830227905, 0, "No pool"),
        "D": (-1.44276146657469, 0, "No pool"),
    }
    for s in c1.classes:
        hs, ratio, res = exp[s.label[-1]]
        assert close(s.hs_envelope, hs)
        assert close(s.hs_D50, ratio)
        assert s.result == res
    assert c1.largest_valid_class == "B"
    assert c1.smallest_no_pool_class == "C"
    assert c1.tie_to_hy8 == "Ties to HY-8"
    assert c1.trial_gives == h.GIVES_BASIN


def test_c1_block5(c1):
    assert c1.LB == 56
    assert c1.basin_applies == "Yes"
    assert close(c1.hs, 1.82127899163151)
    assert c1.Ls == 42
    assert c1.La == 14
    assert c1.Lb == 56
    assert close(c1.Wb, 51.3333333333333)
    assert c1.t_approach == 2.25
    assert c1.t_pool == 1.5


def test_c1_block6(c1):
    assert c1.decay_L == [56, 112, 168, 224]
    assert close(c1.decay_ratio[0], 0.719424019607843)
    assert close(c1.decay_ratio[3], 0.190073529411765)


def test_c1_block7(c1):
    assert c1.V_target == 7.02
    assert close(c1.L_target, 104.015982564475)
    assert c1.L_min == 56
    assert c1.L_adopted == 108
    assert close(c1.L_perm, 175.785234899329)


def test_c1_block8(c1):
    exp = [
        (16.32, 1.73450913608131, "D (1.80)", "Yes"),
        (11.741, 0.89773148929042, "C (1.30)", "Yes"),
        (6.235, 0.253168226049313, "B (0.75)", "No"),
        (4.145, 0.111888474496518, "B (0.75)", "No"),
    ]
    for reach, (V, d50, cls, within) in zip(c1.reaches, exp):
        assert reach.V == V
        assert close(reach.D50_required, d50)
        assert reach.scdot_class == cls
        assert reach.within_protection == within
    assert c1.headwall_class_lined == "D"


def test_c1_block9(c1):
    assert close(c1.tau, 6.7675296)
    assert c1.shear_result == "Exceeds vegetated lining"
    assert close(c1.D50_channel, 1.39850419084462)
    assert c1.channel_class == "D"
    assert c1.channel_finding.startswith("Channel is faster than permissible")


def test_c1_block10(c1):
    assert c1.option_1 == ("Class D 0 to 56 ft. Class C 56 to 108 ft. "
                           "Bottom and both banks.")
    assert c1.option_2 == (
        "Class B basin: pool 1.8 ft deep, 42 ft pool + 14 ft apron, 51 ft "
        "wide at the downstream end. Sec 10.3 classes from block 8 beyond "
        "the basin to the protection length.")


# ---------------------------------------------------------------- Culvert 2


@pytest.fixture(scope="module")
def c2():
    return h.analyze(h.EXAMPLES["culv2"])


def test_c2_no_pool_full_barrel(c2):
    assert c2.D == 5
    assert close(c2.yc, 2.70593796724437)
    assert c2.regime == "Barrel full at outlet"
    assert close(c2.Fr, 0.397995755150746)
    assert close(c2.TW_ye, 1.054)
    assert close(c2.trial.hs_envelope, -7.14156157194183)
    assert c2.trial.result == "No pool"
    assert c2.classes[0].D50_ye == pytest.approx(0.1)  # Class A at the limit
    assert c2.classes[0].result == "No pool"
    assert c2.largest_valid_class == h.NONE_OF_A_TO_D
    assert c2.smallest_no_pool_class == "A"
    assert c2.tie_to_hy8 == "Enter HY-8 Pool Depth (HS) in block 1 to check"
    assert c2.trial_gives == h.GIVES_LINED
    assert c2.basin_applies == "No"
    assert c2.hs is None


def test_c2_length_and_classes(c2):
    assert c2.LB == 48
    assert c2.V_target == 4  # permissible governs, channel slower
    assert close(c2.L_target, 57.3306613226453)
    assert c2.L_adopted == 60
    assert close(c2.L_perm, 57.3306613226453)
    assert [x.scdot_class for x in c2.reaches] == ["B (0.75)"] * 4
    assert [x.within_protection for x in c2.reaches] == ["Yes", "Yes", "No",
                                                         "No"]
    assert c2.headwall_class_lined == "B"


def test_c2_no_slope(c2):
    assert c2.tau == "Enter channel slope in block 1"
    assert c2.shear_result == "n/a"
    assert c2.D50_channel == "n/a"
    assert c2.channel_finding.startswith(
        "Channel velocity is at or below permissible. Bed shear not checked")
    assert c2.option_1 == ("Class B 0 to 48 ft. Class B 48 to 60 ft. "
                           "Bottom and both banks.")
    assert c2.option_2.startswith("Not available.")


# ---------------------------------------------------------------- Culvert 4


@pytest.fixture(scope="module")
def c4():
    return h.analyze(h.EXAMPLES["culv4"])


def test_c4_subcritical_tw_equals_ye(c4):
    assert c4.regime == "Subcritical at brink"
    assert close(c4.Fr, 0.723513314601949)
    assert c4.TW_ye == 1  # TW/ye exactly 1.0 lands on the Eq. 10.2 branch
    assert c4.C0_envelope == 2.4
    assert c4.C0_best_fit == 3
    assert close(c4.trial.hs_envelope, -3.35097297915204)
    assert c4.trial_gives == h.GIVES_LINED


def test_c4_length_shear(c4):
    assert c4.LB == 56
    assert close(c4.L_target, 106.22238425082)
    assert c4.L_adopted == 108
    assert close(c4.tau, 0.741312)
    assert c4.shear_result == "OK for vegetated lining"
    assert c4.D50_channel == "n/a"
    assert c4.channel_finding.startswith(
        "Channel velocity and bed shear are within the vegetated lining")
    assert c4.option_1 == ("Class B 0 to 56 ft. Class B 56 to 108 ft. "
                           "Bottom and both banks.")


# ---------------------------------------------------------------- Units


def test_c0_branches():
    assert h.c0_envelope(0.5) == 1.4
    assert close(h.c0_envelope(0.75), 1.4)  # 4*0.75-1.6
    assert close(h.c0_envelope(0.9), 2.0)
    assert h.c0_envelope(1.0) == pytest.approx(2.4)
    assert h.c0_envelope(1.5) == 2.4
    assert h.c0_best_fit(0.5) == 2.0
    assert close(h.c0_best_fit(0.9), 2.6)
    assert h.c0_best_fit(1.5) == 3.0


def test_ceiling_matches_excel():
    assert h._ceiling(56, 6) == 60 or h._ceiling(56, 6) == 56
    # Excel CEILING(56,6) = 60; 56 is not a multiple of 6.
    assert h._ceiling(56, 6) == 60
    assert h._ceiling(54, 6) == 54
    assert h._ceiling(104.016, 6) == 108
    assert h._ceiling(60.0000000001, 6) == 60


def test_interp_beyond_4lb():
    assert h._interp_length(1.0, 16.0, [12, 8, 6, 5], 50) == "beyond 4 LB"
    assert h._interp_length(20.0, 16.0, [12, 8, 6, 5], 50) == 0.0
    assert h._interp_length(12.0, 16.0, [12, 8, 6, 5], 50) == 50


def test_class_index():
    assert h._class_index_for_d50(0.3) == 1
    assert h._class_index_for_d50(0.5) == 1  # d50 >= required
    assert h._class_index_for_d50(0.51) == 2
    assert h._class_index_for_d50(1.9) == 5
    assert h._class_name(5) == h.LARGER_THAN_D


def test_low_tailwater_path():
    inp = h.Inputs(Q=100, Wo=6, rise=4, embedment=0, yo=1.5, Vo=11.1,
                   TW=0.5, V_channel=3, V_perm=4, V_LB=[8, 6, 4, 3])
    r = h.analyze(inp)
    assert r.tailwater_case == "Low tailwater"
    assert r.L_target == "n/a, low tailwater"
    assert r.L_adopted == "n/a, low tailwater"
    assert r.option_1 == "See block 7."
    assert all(x.within_protection == "See block 7" for x in r.reaches)


def test_lb_gated_on_valid_basin():
    """LB falls back to 4 Wo unless the trial stone gives a valid basin.

    Culvert 1 inputs with a 0.25 ft stone: D50/ye = 0.089 < 0.1, so hs is
    positive but Eq. 10.1 does not apply. The workbook used Ls + La here;
    this port uses 4 Wo.
    """
    inp = h.Inputs(**{**h.asdict(h.EXAMPLES["culv1"]), "D50_trial": 0.25})
    r = h.analyze(inp)
    assert r.trial.result == "D50/ye out of range"
    assert r.trial.hs_envelope > 0
    assert r.trial_gives == h.GIVES_CHANGE
    assert r.LB == 4 * 14
    assert r.basin_applies == "No"


# ------------------------------------------------------------- Circular


def test_segment_geometry():
    D = 4.0
    assert h._segment_area(D, 0) == 0
    assert math.isclose(h._segment_area(D, 2), math.pi * D ** 2 / 8)
    assert math.isclose(h._segment_area(D, 4), math.pi * D ** 2 / 4)
    assert math.isclose(h._chord(D, 2), 4)
    assert h._chord(D, 4) == 0


def test_circular_half_full():
    """48 in RCP, one barrel, flowing half full at the brink."""
    D = 4.0
    A = math.pi * D ** 2 / 8  # 6.283 ft2
    Q = 60.0
    inp = h.Inputs(shape="circular", barrels=1, Q=Q, rise=D, embedment=0,
                   yo=2.0, Vo=Q / A, TW=1.0, V_channel=2.0,
                   V_LB=[6, 4, 3, 2])
    r = h.analyze(inp)
    assert inp.Wo == D  # filled in by validate
    assert math.isclose(r.A, A)
    assert math.isclose(r.ye, math.sqrt(A / 2))
    assert r.Vo_check_result == "OK"
    assert math.isclose(r.Fr, inp.Vo / math.sqrt(32.2 * r.ye))
    # Critical depth satisfies Q^2 T / (g A^3) = 1
    yc = r.yc
    Ac, Tc = h.flow_area(inp, yc), h.top_width(inp, yc)
    assert math.isclose(Q ** 2 * Tc / (32.2 * Ac ** 3), 1.0, rel_tol=1e-6)
    assert 0 < yc < D


def test_circular_embedded_and_full():
    # Embedded 1 ft: flow area excludes the segment below the bed line.
    inp = h.Inputs(shape="circular", Q=50, rise=4, embedment=1, yo=1.5,
                   Vo=5, TW=1, V_channel=1, V_LB=[4, 3, 2, 1])
    r = h.analyze(inp)
    expect = h._segment_area(4, 2.5) - h._segment_area(4, 1)
    assert math.isclose(r.A, expect)
    assert r.D == 3
    # Brink depth at the crown: full barrel, area is the net section.
    full = h.Inputs(shape="circular", Q=50, rise=4, embedment=0, yo=4.0,
                    Vo=50 / (math.pi * 4), TW=1, V_channel=1,
                    V_LB=[4, 3, 2, 1])
    rf = h.analyze(full)
    assert rf.regime == "Barrel full at outlet"
    assert math.isclose(rf.A, math.pi * 4)
    assert rf.Vo_check_result == "OK"


def test_circular_yc_capped_at_crown():
    # Absurd discharge for a 2 ft pipe: critical depth reported as D.
    inp = h.Inputs(shape="circular", Q=500, rise=2, yo=2, Vo=159.2, TW=1,
                   V_channel=1, V_LB=[1, 1, 1, 1])
    assert h.critical_depth(inp) == 2


def test_validation():
    with pytest.raises(ValueError):
        h.analyze(h.Inputs(shape="oval", Q=1, Wo=1, rise=1, yo=1, Vo=1))
    with pytest.raises(ValueError):
        h.analyze(h.Inputs(Q=1, Wo=1, rise=1, embedment=1, yo=1, Vo=1))
    with pytest.raises(ValueError):
        h.analyze(h.Inputs(Q=0, Wo=1, rise=1, yo=1, Vo=1))
    with pytest.raises(ValueError):
        h.Inputs.from_dict({"Q": 1, "bogus": 2})


def test_report_and_cli(tmp_path, capsys):
    rc = h.main(["--example", "culv1"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Trial stone gives: Riprap basin (Sec 10.1)" in out
    js = tmp_path / "r.json"
    h.main(["--example", "culv2", "--json-out", str(js), "--out",
            str(tmp_path / "r.txt")])
    assert js.exists()
