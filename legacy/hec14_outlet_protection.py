"""Culvert outlet protection per FHWA HEC-14 (3rd ed.) Chapter 10 with HY-8.

Python port of the "Outlet Protection Calcs" workbook. One ``Inputs`` record
corresponds to block 1 of a culvert tab; ``analyze`` reproduces blocks 2 to
10 with the same formulas, limits and wording, so a result can be checked
line by line against the spreadsheet or an HY-8 Riprap Basin printout.

Basis
    HEC-14 3rd ed. (FHWA-NHI-06-086) Table 1.1, Sec 10.1, 10.1.3, 10.3.
    HEC-15 3rd ed. (channel shear check).
    HY-8 Energy Dissipation report (Riprap Basin, Envelope Curve).
    SCDOT Stormwater Quality Design Manual App. E, Tables E.2 and E.3.
    SCDOT Std Spec Sec 804 (riprap classes).

Units
    ft, cfs, fps, psf, pcf. US customary throughout.

Usage
    python hec14_outlet_protection.py --example culv1
    python hec14_outlet_protection.py inputs.json [--json-out results.json]
    python hec14_outlet_protection.py --template > inputs.json
    python hec14_outlet_protection.py --hy8 proj.hy8 --crossing "Oak Creek Road" \
        --culvert "Twin 6x4 Box" --flow 50-yr --v-lb 11.7 6.2 4.1 3.1 --hs 1.8

Outlet shapes
    box       ye = yo (rectangular). Wo is the total clear width.
    circular  ye = (A/2)^0.5 with A the flow area at the brink, HEC-14
              Sec 10.1. rise is the diameter; Wo defaults to barrels x D.

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass, field, fields
from typing import Dict, List, Optional, Union

Number = Union[int, float]

# --------------------------------------------------------------------------
# Reference tables
# --------------------------------------------------------------------------

# SCDOT riprap classes, d50 and dmax in ft (block 8 of the workbook).
# Order matters: class selection walks this list from smallest to largest.
SCDOT_CLASSES: List[Dict[str, Number]] = [
    {"name": "A", "d50": 0.50, "dmax": 0.75},
    {"name": "B", "d50": 0.75, "dmax": 1.30},
    {"name": "C", "d50": 1.30, "dmax": 1.80},
    {"name": "D", "d50": 1.80, "dmax": 2.25},
]
CLASS_NAMES = [c["name"] for c in SCDOT_CLASSES]
CLASS_D50 = {c["name"]: c["d50"] for c in SCDOT_CLASSES}
LARGER_THAN_D = "Larger than D"
NONE_OF_A_TO_D = "None of A to D"

# Riprap basin equation limits, HEC-14 Sec 10.1.5 Step 2.
D50_YE_MIN = 0.1
D50_YE_MAX = 0.7
HS_D50_MIN = 2.0

# Tailwater threshold for the high tailwater procedure, HEC-14 Sec 10.1.3.
HIGH_TW_RATIO = 0.75

# Riprap apron (Sec 10.2) applicability, Table 1.1 footnote 8: rise <= 60 in.
APRON_MAX_RISE_IN = 60

SHAPES = {"box", "circular"}

# Result strings. Kept identical to the workbook so outputs tie exactly.
GIVES_BASIN = "Riprap basin (Sec 10.1)"
GIVES_LINED = "Lined channel, no pool"
GIVES_CHANGE = "Change trial D50"


# --------------------------------------------------------------------------
# Inputs (block 1)
# --------------------------------------------------------------------------


@dataclass
class Inputs:
    """Block 1 of a culvert tab. Everything typed is here."""

    # Project heading (rows 2 to 5).
    project: str = ""
    culvert: str = ""
    description: str = ""
    design_storm: str = ""
    hy8_file: str = ""

    # HY-8 Culvert Summary Table, design storm row.
    Q: float = 0.0  # Design discharge, cfs
    yo: float = 0.0  # Brink (outlet) depth, ft
    Vo: float = 0.0  # Brink velocity, fps
    TW: float = 0.0  # Tailwater depth above embedded bed, ft
    V_channel: float = 0.0  # Tailwater (channel) velocity, fps

    # Plans.
    shape: str = "box"  # "box" (rectangular) or "circular"
    barrels: int = 1  # Barrel count; sets Wo for circular when Wo is 0
    Wo: float = 0.0  # Total clear width at the outlet, all barrels, ft
    rise: float = 0.0  # Culvert rise (diameter for circular), ft
    embedment: float = 0.0  # Embedment, ft

    # HY-8 Tailwater Data. Optional; used only in the block 9 shear check.
    slope: Optional[float] = None  # Channel slope, ft/ft

    # SCDOT App. E, Tables E.2 and E.3.
    V_perm: float = 4.0  # Permissible velocity, vegetated channel, fps
    tau_perm: float = 2.1  # Permissible shear, vegetated channel, psf

    # Riprap and constants.
    Ss: float = 2.65  # Riprap specific gravity
    g: float = 32.2  # ft/s2
    gamma_w: float = 62.4  # Unit weight of water, pcf

    # Trial stone and minimum class to specify.
    D50_trial: float = 0.75  # d50 of the SCDOT class run in HY-8, ft
    min_class: str = "B"  # Smallest class the Engineer will call out

    # HY-8 Riprap Basin screen, Downstream Riprap for High TW, jet velocities
    # at 1, 2, 3 and 4 basin lengths (LB), fps.
    V_LB: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])

    # HY-8 Pool Depth (HS) at the trial D50, Envelope Curve. Optional.
    HS_hy8: Optional[float] = None

    def validate(self) -> None:
        """Raise ValueError on inputs the formulas cannot take."""
        if self.shape not in SHAPES:
            raise ValueError(f"shape must be one of {sorted(SHAPES)}")
        if self.barrels < 1:
            raise ValueError("barrels must be >= 1")
        if self.shape == "circular" and self.Wo <= 0:
            self.Wo = self.barrels * self.rise  # total width = n x diameter
        positives = ("Q", "yo", "Vo", "Wo", "rise", "D50_trial", "Ss", "g",
                     "gamma_w")
        for name in positives:
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be > 0")
        if self.TW < 0 or self.embedment < 0:
            raise ValueError("TW and embedment must be >= 0")
        if self.embedment >= self.rise:
            raise ValueError("embedment must be less than rise")
        if self.Ss <= 1:
            raise ValueError("Ss must be > 1")
        if self.min_class not in CLASS_NAMES:
            raise ValueError(f"min_class must be one of {CLASS_NAMES}")
        if len(self.V_LB) != 4:
            raise ValueError("V_LB needs four velocities (1 to 4 LB)")
        if self.slope is not None and self.slope < 0:
            raise ValueError("slope must be >= 0 or None")

    @classmethod
    def from_dict(cls, data: Dict) -> "Inputs":
        known = {f.name for f in fields(cls)}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"Unknown input keys: {sorted(unknown)}")
        return cls(**data)


# --------------------------------------------------------------------------
# Results (blocks 2 to 10)
# --------------------------------------------------------------------------


@dataclass
class StoneCheck:
    """One row of the block 4 table (trial stone or an SCDOT class)."""

    label: str
    D50: float
    D50_ye: float
    hs_envelope: float
    hs_D50: float  # 0 when hs <= 0, as in the workbook
    result: str
    hs_best_fit: float


@dataclass
class Reach:
    """One row of the block 8 riprap sizing table."""

    label: str
    from_ft: float
    to_ft: float
    V: float
    D50_required: float
    scdot_class: str  # e.g. "D (1.80)" or "Larger than D"
    within_protection: str  # "Yes", "No" or "See block 7"


@dataclass
class Results:
    """Everything the workbook computes, grouped by block."""

    # Block 2. Outlet hydraulics.
    D: float = 0.0  # Hydraulic rise = rise - embedment
    A: float = 0.0  # Flow area at the brink, all barrels, ft2
    yc: float = 0.0  # Critical depth in the barrel
    regime: str = ""
    Vo_check: float = 0.0  # Q / A  (= Q / (Wo yo) for a box)
    Vo_check_result: str = ""
    ye: float = 0.0  # Equivalent depth: yo for a box, (A/2)^0.5 otherwise
    Fr: float = 0.0
    TW_ye: float = 0.0
    tailwater_case: str = ""

    # Block 3. Applicability screen, HEC-14 Table 1.1.
    apron_applicable: str = ""
    basin_applicable: str = ""
    jump_basin: str = ""

    # Block 4. Riprap basin check, Eq. 10.1 to 10.3.
    C0_envelope: float = 0.0
    C0_best_fit: float = 0.0
    trial: Optional[StoneCheck] = None
    classes: List[StoneCheck] = field(default_factory=list)
    trial_result: str = ""
    largest_valid_class: str = ""
    smallest_no_pool_class: str = ""
    tie_to_hy8: str = ""
    trial_gives: str = ""

    # Block 1 derived. Basin length LB used as the HY-8 reporting interval.
    LB: float = 0.0

    # Block 5. Riprap basin geometry. None when no basin.
    basin_applies: str = ""
    hs: Optional[float] = None
    Ls: Optional[float] = None
    La: Optional[float] = None
    Lb: Optional[float] = None
    Wb: Optional[float] = None
    t_approach: Optional[float] = None  # 3 D50
    t_pool: Optional[float] = None  # 2 D50

    # Block 6. Downstream velocity decay.
    high_tw_procedure: str = ""
    decay_L: List[float] = field(default_factory=list)
    decay_V: List[float] = field(default_factory=list)
    decay_ratio: List[float] = field(default_factory=list)

    # Block 7. Protection length.
    channel_vs_perm: str = ""
    V_target: float = 0.0
    L_target: Union[float, str] = 0.0
    L_min: float = 0.0
    L_adopted: Union[float, str] = 0.0
    L_perm: Union[float, str] = 0.0

    # Block 8. Riprap sizing, Eq. 10.6.
    reaches: List[Reach] = field(default_factory=list)
    headwall_class_lined: str = ""

    # Block 9. Receiving channel check.
    tau: Union[float, str] = ""
    shear_result: str = ""
    D50_channel: Union[float, str] = ""
    channel_class: Union[float, str] = ""
    channel_finding: str = ""

    # Block 10. Design summary.
    option_1: str = ""
    option_2: str = ""
    vertical_limits: str = ""
    banks: str = ""
    basis: str = ""


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _class_index_for_d50(required: float) -> int:
    """1-based index of the smallest class whose d50 >= required.

    Mirrors Excel COUNTIF(d50_range, "<" & required) + 1. Returns 5 when
    every class is too small.
    """
    return sum(1 for c in SCDOT_CLASSES if c["d50"] < required) + 1


def _class_index(name: str) -> int:
    """1-based index of a class name, 5 when 'None of A to D'."""
    if name == NONE_OF_A_TO_D:
        return len(SCDOT_CLASSES) + 1
    return CLASS_NAMES.index(name) + 1


def _class_label(index: int) -> str:
    """'D (1.80)' style label, or 'Larger than D'."""
    if index > len(SCDOT_CLASSES):
        return LARGER_THAN_D
    c = SCDOT_CLASSES[index - 1]
    return f"{c['name']} ({c['d50']:.2f})"


def _class_name(index: int) -> str:
    if index > len(SCDOT_CLASSES):
        return LARGER_THAN_D
    return CLASS_NAMES[index - 1]


def _ceiling(x: float, step: float) -> float:
    """Excel CEILING(x, step): round up to the next multiple of step."""
    n = x / step
    # Guard against 56.000000001 rounding up a whole extra step.
    if abs(n - round(n)) < 1e-9:
        return round(n) * step
    return math.ceil(n) * step


def _fmt0(x: float) -> str:
    """Excel TEXT(x, "0")."""
    return f"{x:.0f}"


def _fmt1(x: float) -> str:
    """Excel TEXT(x, "0.0")."""
    return f"{x:.1f}"


# --------------------------------------------------------------------------
# Outlet section geometry
# --------------------------------------------------------------------------


def _segment_area(diameter: float, depth: float) -> float:
    """Area of a circular segment of height ``depth`` from the invert."""
    if depth <= 0:
        return 0.0
    if depth >= diameter:
        return math.pi * diameter ** 2 / 4.0
    r = diameter / 2.0
    theta = 2.0 * math.acos((r - depth) / r)  # central angle, rad
    return r ** 2 * (theta - math.sin(theta)) / 2.0


def _chord(diameter: float, depth: float) -> float:
    """Water surface width in a circle at ``depth`` from the invert."""
    if depth <= 0 or depth >= diameter:
        return 0.0
    r = diameter / 2.0
    return 2.0 * math.sqrt(max(r ** 2 - (r - depth) ** 2, 0.0))


def flow_area(inp: Inputs, depth: float) -> float:
    """Flow area for all barrels at ``depth`` above the embedded bed, ft2."""
    if inp.shape == "box":
        return inp.Wo * depth
    # Circular: segment above the embedment line, per barrel.
    e = inp.embedment
    per_barrel = (_segment_area(inp.rise, e + depth) - _segment_area(inp.rise, e))
    return inp.barrels * per_barrel


def top_width(inp: Inputs, depth: float) -> float:
    """Water surface width for all barrels at ``depth``, ft."""
    if inp.shape == "box":
        return inp.Wo
    return inp.barrels * _chord(inp.rise, inp.embedment + depth)


def critical_depth(inp: Inputs) -> float:
    """Critical depth above the embedded bed, ft.

    Box: closed form yc = ((Q/Wo)^2 / g)^(1/3). Circular: bisection on
    Q^2 T / (g A^3) = 1 between the invert and 0.94 D. Above that the top
    width collapses toward the crown and the equation always has a root
    just below D that means nothing physically, so if the flow is still
    supercritical at 0.94 D the critical depth is reported as D, the same
    cap HDS-5 charts and HY-8 use.
    """
    if inp.shape == "box":
        return ((inp.Q / inp.Wo) ** 2 / inp.g) ** (1.0 / 3.0)
    D = inp.rise - inp.embedment

    def f(y: float) -> float:
        A, T = flow_area(inp, y), top_width(inp, y)
        if A <= 0 or T <= 0:
            return -1.0
        return inp.Q ** 2 * T / (inp.g * A ** 3) - 1.0

    lo, hi = 1e-6 * D, 0.94 * D
    if f(hi) > 0:  # Still supercritical at 0.94 D: report the crown.
        return D
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-10:
            break
    return 0.5 * (lo + hi)


def equivalent_depth(inp: Inputs, A: float) -> float:
    """HEC-14 Sec 10.1: ye = yo for rectangular, (A/2)^0.5 otherwise."""
    if inp.shape == "box":
        return inp.yo
    return math.sqrt(A / 2.0)


# --------------------------------------------------------------------------
# Core equations
# --------------------------------------------------------------------------


def c0_envelope(tw_ye: float) -> float:
    """HEC-14 Eq. 10.2, Envelope Curve coefficient."""
    if tw_ye < 0.75:
        return 1.4
    if tw_ye <= 1.0:
        return 4.0 * tw_ye - 1.6
    return 2.4


def c0_best_fit(tw_ye: float) -> float:
    """HEC-14 Eq. 10.3, Best Fit Curve coefficient (comparison only)."""
    if tw_ye < 0.75:
        return 2.0
    if tw_ye <= 1.0:
        return 4.0 * tw_ye - 1.0
    return 3.0


def pool_depth(D50: float, ye: float, Fr: float, C0: float) -> float:
    """HEC-14 Eq. 10.1: hs = (0.86 (D50/ye)^-0.55 Fr - C0) ye.

    Negative values mean no pool forms. The caller applies the D50/ye
    limits; this function does not.
    """
    return (0.86 * (D50 / ye) ** -0.55 * Fr - C0) * ye


def riprap_d50_velocity(V: float, g: float, Ss: float) -> float:
    """HEC-14 Eq. 10.6 (Sec 10.3): D50 = 0.692 V^2 / (2 g (Ss - 1))."""
    return 0.692 * V ** 2 / (2.0 * g * (Ss - 1.0))


def _stone_check(label: str, D50: float, ye: float, Fr: float,
                 C0_env: float, C0_bf: float) -> StoneCheck:
    """One block 4 row."""
    ratio = D50 / ye
    hs_env = pool_depth(D50, ye, Fr, C0_env)
    hs_bf = pool_depth(D50, ye, Fr, C0_bf)
    hs_d50 = hs_env / D50 if hs_env > 0 else 0.0
    if ratio < D50_YE_MIN or ratio > D50_YE_MAX:
        result = "D50/ye out of range"
    elif hs_env <= 0:
        result = "No pool"
    elif hs_d50 < HS_D50_MIN:
        result = "hs/D50 below 2"
    else:
        result = "Valid basin"
    return StoneCheck(label, D50, ratio, hs_env, hs_d50, result, hs_bf)


def _interp_length(target: float, Vo: float, V_LB: List[float],
                   LB: float) -> Union[float, str]:
    """Distance where the jet velocity decays to ``target``.

    Linear interpolation between the HY-8 points at 0, 1, 2, 3 and 4 LB
    (block 7, row 87). Returns "beyond 4 LB" when the jet is still faster
    than the target at 4 LB.
    """
    if target >= Vo:
        return 0.0
    stations = [Vo] + list(V_LB)
    for i in range(1, len(stations)):
        upstream, downstream = stations[i - 1], stations[i]
        if target >= downstream:
            return (i - 1) * LB + (upstream - target) / (upstream - downstream) * LB
    return "beyond 4 LB"


# --------------------------------------------------------------------------
# Main analysis
# --------------------------------------------------------------------------


def analyze(inp: Inputs) -> Results:
    """Run blocks 2 to 10 of the workbook for one culvert."""
    inp.validate()
    r = Results()
    g = inp.g

    # ---- Block 2. Outlet hydraulics -------------------------------------
    r.D = inp.rise - inp.embedment
    # Brink depth cannot exceed the hydraulic rise.
    yo_eff = min(inp.yo, r.D)
    r.A = flow_area(inp, yo_eff)
    r.yc = critical_depth(inp)
    if inp.yo >= r.D:
        r.regime = "Barrel full at outlet"
    elif inp.yo < r.yc:
        r.regime = "Supercritical at brink; tailwater submerges jet"
    else:
        r.regime = "Subcritical at brink"
    r.Vo_check = inp.Q / r.A
    r.Vo_check_result = (
        "OK" if abs(r.Vo_check - inp.Vo) <= 0.1
        else "Does not match: check Q, width and outlet depth")
    r.ye = equivalent_depth(inp, r.A)
    r.Fr = inp.Vo / math.sqrt(g * r.ye)
    r.TW_ye = inp.TW / r.ye
    r.tailwater_case = ("High tailwater" if r.TW_ye > HIGH_TW_RATIO
                        else "Low tailwater")

    # ---- Block 3. Applicability screen, Table 1.1 ------------------------
    r.apron_applicable = (
        "Applicable" if inp.rise * 12 <= APRON_MAX_RISE_IN
        else "Not applicable, rise > 60 in (footnote 8)")
    r.basin_applicable = ("Applicable, Fr < 3" if r.Fr < 3
                          else "Not applicable, Fr >= 3")
    r.jump_basin = ("Possible, Fr >= 1.7" if r.Fr >= 1.7
                    else "Not needed, Fr < 1.7")

    # ---- Block 4. Riprap basin check, Eq. 10.1 ---------------------------
    r.C0_envelope = c0_envelope(r.TW_ye)
    r.C0_best_fit = c0_best_fit(r.TW_ye)
    r.trial = _stone_check("Trial D50", inp.D50_trial, r.ye, r.Fr,
                           r.C0_envelope, r.C0_best_fit)
    r.classes = [
        _stone_check(f"Class {c['name']}", c["d50"], r.ye, r.Fr,
                     r.C0_envelope, r.C0_best_fit)
        for c in SCDOT_CLASSES
    ]
    by_name = dict(zip(CLASS_NAMES, r.classes))

    t = r.trial
    if t.result == "Valid basin":
        r.trial_result = ("Valid riprap basin for the trial stone "
                          "(hs/D50 of 2 or more).")
    elif t.result == "No pool":
        r.trial_result = ("No scour pool forms (hs <= 0). No basin. HY-8 "
                          "shows HS = 0.000 and a red HS/D50.")
    elif t.result == "hs/D50 below 2":
        r.trial_result = ("Shallow pool, hs/D50 below 2. Use a smaller class "
                          "for a basin or a larger class for no pool.")
    else:
        r.trial_result = ("D50/ye is outside 0.1 to 0.7. Eq. 10.1 does not "
                          "apply to this stone. Change the trial D50.")

    # Largest class with a valid basin: walk D, C, B, A.
    r.largest_valid_class = NONE_OF_A_TO_D
    for name in reversed(CLASS_NAMES):
        if by_name[name].result == "Valid basin":
            r.largest_valid_class = name
            break
    # Smallest class with no pool: walk A, B, C, D.
    r.smallest_no_pool_class = NONE_OF_A_TO_D
    for name in CLASS_NAMES:
        if by_name[name].result == "No pool":
            r.smallest_no_pool_class = name
            break

    if inp.HS_hy8 is None:
        r.tie_to_hy8 = "Enter HY-8 Pool Depth (HS) in block 1 to check"
    elif abs(max(t.hs_envelope, 0.0) - inp.HS_hy8) <= 0.05:
        r.tie_to_hy8 = "Ties to HY-8"
    else:
        r.tie_to_hy8 = "Does not tie: check inputs and curve"

    if t.result == "Valid basin":
        r.trial_gives = GIVES_BASIN
    elif t.result == "No pool":
        r.trial_gives = GIVES_LINED
    else:
        r.trial_gives = GIVES_CHANGE

    # ---- Block 1 derived. Basin length LB (row 24) -----------------------
    # Ls + La when the trial stone gives a valid basin, else 4 Wo. This is
    # stricter than the workbook, which used Ls + La for any hs > 0 even
    # when D50/ye was outside the Eq. 10.1 range or hs/D50 < 2.
    hs_t = t.hs_envelope
    if r.trial_gives == GIVES_BASIN:
        r.LB = max(10 * hs_t, 3 * inp.Wo) + max(5 * hs_t, inp.Wo)
    else:
        r.LB = 4 * inp.Wo

    # ---- Block 5. Riprap basin geometry ----------------------------------
    if r.trial_gives == GIVES_BASIN:
        r.basin_applies = "Yes"
        r.hs = hs_t
        r.Ls = max(10 * hs_t, 3 * inp.Wo)
        r.La = max(5 * hs_t, inp.Wo)
        r.Lb = r.Ls + r.La
        r.Wb = inp.Wo + 2.0 / 3.0 * r.Lb  # 1:3 flare each side
        r.t_approach = 3 * inp.D50_trial
        r.t_pool = 2 * inp.D50_trial
    else:
        r.basin_applies = "No"

    # ---- Block 6. Downstream velocity decay ------------------------------
    high_tw = r.TW_ye > HIGH_TW_RATIO
    r.high_tw_procedure = (
        "Yes, TW/ye > 0.75" if high_tw
        else "No, low tailwater: use the Sec 10.1 basin exit check")
    r.decay_L = [r.LB * i for i in (1, 2, 3, 4)]
    r.decay_V = list(inp.V_LB)
    r.decay_ratio = [v / inp.Vo for v in inp.V_LB]

    # ---- Block 7. Protection length --------------------------------------
    channel_faster = inp.V_channel > inp.V_perm
    r.channel_vs_perm = ("Channel velocity exceeds permissible"
                         if channel_faster
                         else "Channel velocity is at or below permissible")
    r.V_target = inp.V_channel if channel_faster else inp.V_perm
    if high_tw:
        r.L_target = _interp_length(r.V_target, inp.Vo, inp.V_LB, r.LB)
        r.L_perm = _interp_length(inp.V_perm, inp.Vo, inp.V_LB, r.LB)
    else:
        r.L_target = "n/a, low tailwater"
        r.L_perm = "n/a, low tailwater"
    r.L_min = r.LB
    if isinstance(r.L_target, (int, float)):
        r.L_adopted = _ceiling(max(r.L_target, r.L_min), 6)
    else:
        r.L_adopted = r.L_target

    # ---- Block 8. Riprap sizing, Eq. 10.6 --------------------------------
    min_idx = _class_index(inp.min_class)
    reach_V = [inp.Vo] + list(inp.V_LB[:3])  # velocity at upstream end
    labels = ["Headwall to 1 LB", "1 LB to 2 LB", "2 LB to 3 LB",
              "3 LB to 4 LB"]
    r.reaches = []
    for i, (label, V) in enumerate(zip(labels, reach_V)):
        req = riprap_d50_velocity(V, g, inp.Ss)
        idx = max(_class_index_for_d50(req), min_idx)
        start = r.LB * i
        if isinstance(r.L_adopted, (int, float)):
            within = "Yes" if start < r.L_adopted else "No"
        else:
            within = "See block 7"
        r.reaches.append(Reach(label, start, r.LB * (i + 1), V, req,
                               _class_label(idx), within))
    hw_idx = max(_class_index_for_d50(r.reaches[0].D50_required), min_idx,
                 _class_index(r.smallest_no_pool_class))
    r.headwall_class_lined = _class_name(hw_idx)

    # ---- Block 9. Receiving channel check, HEC-15 shear basis -----------
    if inp.slope is None:
        r.tau = "Enter channel slope in block 1"
        r.shear_result = "n/a"
        r.D50_channel = "n/a"
        r.channel_class = "n/a"
    else:
        # Depth in place of hydraulic radius; conservative.
        r.tau = inp.gamma_w * inp.TW * inp.slope
        if r.tau <= inp.tau_perm:
            r.shear_result = "OK for vegetated lining"
            r.D50_channel = "n/a"
            r.channel_class = "n/a"
        else:
            r.shear_result = "Exceeds vegetated lining"
            # HEC-15 Shields form, bed only: D50 = tau / (0.047 (Ss-1) gamma)
            r.D50_channel = r.tau / (0.047 * (inp.Ss - 1.0) * inp.gamma_w)
            r.channel_class = _class_name(_class_index_for_d50(r.D50_channel))

    if channel_faster:
        r.channel_finding = (
            "Channel is faster than permissible under its own flow. Outlet "
            "protection ends where the jet equals channel velocity. Beyond "
            "that: HEC-15 channel lining, or documented field evidence that "
            "the existing channel is stable.")
    elif r.shear_result == "Exceeds vegetated lining":
        r.channel_finding = (
            "Channel velocity is acceptable but bed shear exceeds the "
            "vegetated lining. Check the cover assumption or line the "
            "channel.")
    elif isinstance(r.tau, (int, float)):
        r.channel_finding = (
            "Channel velocity and bed shear are within the vegetated lining "
            "limits at the design storm. Permanent seeding beyond the end of "
            "rock; turf reinforcement mat on the banks is optional through "
            "establishment.")
    else:
        r.channel_finding = (
            "Channel velocity is at or below permissible. Bed shear not "
            "checked: enter the channel slope in block 1.")

    # ---- Block 10. Design summary ----------------------------------------
    r.option_1 = _option_1(r)
    r.option_2 = _option_2(r)
    r.vertical_limits = (
        "Line bottom and both banks to the design storm WSE plus 0.5 ft and "
        "key 1 ft into the bank or bench. Toe key at headwall 1.5 ft below "
        "outlet invert; 2 ft key trench at the downstream end. Top of rock "
        "flush with existing bed.")
    r.banks = ("Lay back to 2H:1V or flatter within the lined reach. "
               "Geotextile under all riprap.")
    r.basis = (
        "HEC-14 3rd ed. (FHWA-NHI-06-086) Table 1.1, Sec 10.1, 10.1.3, 10.3; "
        "HEC-15 3rd ed.; HY-8 Energy Dissipation report (Riprap Basin, "
        "Envelope Curve); SCDOT Stormwater Quality Design Manual App. E "
        "Tables E.2 and E.3; SCDOT Requirements for Hydraulic Design Studies "
        "(design storm).")
    return r


def _short_class(label: str) -> str:
    """'D (1.80)' -> 'D'; 'Larger than D' -> 'larger than D'."""
    if label.startswith("Larger"):
        return "larger than D"
    return label[0]


def _option_1(r: Results) -> str:
    """Block 10, Option 1: lined channel at bed grade (no pool)."""
    if not isinstance(r.L_adopted, (int, float)):
        return "See block 7."
    L = r.L_adopted
    first = r.reaches[0]
    text = (f"Class {_short_class(r.headwall_class_lined)} 0 to "
            f"{_fmt0(min(first.to_ft, L))} ft. ")
    for reach in r.reaches[1:]:
        if reach.from_ft < L:
            text += (f"Class {_short_class(reach.scdot_class)} "
                     f"{_fmt0(reach.from_ft)} to "
                     f"{_fmt0(min(reach.to_ft, L))} ft. ")
    return text + "Bottom and both banks."


def _option_2(r: Results) -> str:
    """Block 10, Option 2: riprap basin (Sec 10.1)."""
    if r.largest_valid_class == NONE_OF_A_TO_D:
        return ("Not available. No scour pool forms with Classes A to D, so "
                "there is no basin to build.")
    if r.trial_gives == GIVES_BASIN:
        return (f"Class {r.largest_valid_class} basin: pool {_fmt1(r.hs)} ft "
                f"deep, {_fmt0(r.Ls)} ft pool + {_fmt0(r.La)} ft apron, "
                f"{_fmt0(r.Wb)} ft wide at the downstream end. Sec 10.3 "
                "classes from block 8 beyond the basin to the protection "
                "length.")
    return (f"Available with Class {r.largest_valid_class}. Set the trial "
            "D50 to that class to fill block 5.")


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------


def _num(x: Union[float, str, None], nd: int = 2) -> str:
    if x is None:
        return "n/a"
    if isinstance(x, str):
        return x
    return f"{x:.{nd}f}"


def format_report(inp: Inputs, r: Results) -> str:
    """Plain-text report laid out like the workbook's ten blocks."""
    L: List[str] = []
    w = L.append
    w("Culvert Outlet Protection Calculation")
    w("FHWA HEC-14 (3rd ed.) Chapter 10 with HY-8")
    w(f"Project: {inp.project}    Culvert: {inp.culvert}")
    w(f"Description: {inp.description}")
    w(f"Design storm: {inp.design_storm}    HY-8 file: {inp.hy8_file}")
    w("Units: ft, cfs, fps, psf.")
    w("")
    w("1. Inputs")
    w(f"  Shape = {inp.shape}   barrels = {inp.barrels}   Q = {inp.Q} cfs   "
      f"Wo = {inp.Wo} ft   rise = {inp.rise} ft   embedment = {inp.embedment} ft")
    w(f"  yo = {inp.yo} ft   Vo = {inp.Vo} fps   TW = {inp.TW} ft   "
      f"V channel = {inp.V_channel} fps   S = {inp.slope}")
    w(f"  V perm = {inp.V_perm} fps   tau perm = {inp.tau_perm} psf   "
      f"Ss = {inp.Ss}")
    w(f"  Trial D50 = {inp.D50_trial} ft   Min class = {inp.min_class}   "
      f"HY-8 HS = {inp.HS_hy8}")
    w(f"  HY-8 jet V at 1..4 LB = {inp.V_LB} fps   LB = {_num(r.LB)} ft")
    w("")
    w("2. Outlet hydraulics")
    w(f"  D = rise - embedment = {_num(r.D)} ft   Flow area at brink A = "
      f"{_num(r.A)} ft2")
    yc_note = ("((Q/Wo)^2/g)^(1/3)" if inp.shape == "box"
               else "Q^2 T/(g A^3) = 1")
    w(f"  yc = {yc_note} = {_num(r.yc, 3)} ft")
    w(f"  Outlet regime: {r.regime}")
    w(f"  Vo check = Q/A = {_num(r.Vo_check)} fps  ({r.Vo_check_result})")
    ye_note = "yo" if inp.shape == "box" else "(A/2)^0.5"
    w(f"  ye = {ye_note} = {_num(r.ye)} ft   Fr = {_num(r.Fr, 3)}   "
      f"TW/ye = {_num(r.TW_ye, 3)}   {r.tailwater_case}")
    w("")
    w("3. Applicability screen, HEC-14 Table 1.1")
    w(f"  Riprap apron, Sec 10.2: {r.apron_applicable}")
    w(f"  Riprap basin, Sec 10.1: {r.basin_applicable}")
    w(f"  Hydraulic jump basins, Ch. 8: {r.jump_basin}")
    w("")
    w("4. Riprap basin check, HEC-14 Eq. 10.1")
    w("  hs/ye = 0.86 (D50/ye)^-0.55 Fr - C0")
    w(f"  C0 envelope (Eq. 10.2) = {_num(r.C0_envelope)}   "
      f"C0 best fit (Eq. 10.3) = {_num(r.C0_best_fit)}")
    w(f"  {'Stone':10s} {'D50':>6s} {'D50/ye':>7s} {'hs env':>8s} "
      f"{'hs/D50':>7s} {'hs bf':>8s}  Result")
    for s in [r.trial] + r.classes:
        w(f"  {s.label:10s} {s.D50:6.2f} {s.D50_ye:7.3f} {s.hs_envelope:8.3f} "
          f"{s.hs_D50:7.2f} {s.hs_best_fit:8.3f}  {s.result}")
    w(f"  Result for trial D50: {r.trial_result}")
    w(f"  Largest class giving a valid basin: {r.largest_valid_class}")
    w(f"  Smallest class with no scour pool: {r.smallest_no_pool_class}")
    w(f"  Tie to HY-8 Pool Depth: {r.tie_to_hy8}")
    w(f"  Trial stone gives: {r.trial_gives}")
    w("")
    w("5. Riprap basin geometry, HEC-14 Sec 10.1")
    w(f"  Basin applies? {r.basin_applies}")
    w(f"  hs = {_num(r.hs)} ft   Ls = max(10 hs, 3 Wo) = {_num(r.Ls)} ft   "
      f"La = max(5 hs, Wo) = {_num(r.La)} ft")
    w(f"  Ls + La = {_num(r.Lb)} ft   Width downstream = Wo + 2/3 (Ls+La) = "
      f"{_num(r.Wb)} ft")
    w(f"  Thickness: approach 3 D50 = {_num(r.t_approach)} ft; pool and "
      f"apron 2 D50 = {_num(r.t_pool)} ft")
    w("")
    w("6. Downstream velocity decay, HEC-14 Sec 10.1.3 / Fig. 10.3")
    w(f"  High tailwater procedure applies? {r.high_tw_procedure}")
    for i, (Lx, V, ratio) in enumerate(zip(r.decay_L, r.decay_V,
                                           r.decay_ratio), 1):
        w(f"  {i} LB: L = {Lx:6.1f} ft   V = {V:6.3f} fps   VL/Vo = {ratio:.3f}")
    w("")
    w("7. Protection length")
    w(f"  {r.channel_vs_perm}. Target velocity = {_num(r.V_target)} fps")
    w(f"  Length where jet = target: {_num(r.L_target, 1)} ft")
    w(f"  Minimum length, 1 LB: {_num(r.L_min, 1)} ft")
    w(f"  Outlet protection length adopted (rounded up to 6 ft): "
      f"{_num(r.L_adopted, 0)} ft")
    w(f"  Reference, length where jet = permissible: {_num(r.L_perm, 1)} ft")
    w("")
    w("8. Riprap sizing, HEC-14 Eq. 10.6: D50 = 0.692 V^2 / (2 g (Ss - 1))")
    w(f"  {'Reach':18s} {'From':>6s} {'To':>6s} {'V':>7s} {'Req D50':>8s}  "
      f"{'Class':10s} Within L?")
    for x in r.reaches:
        w(f"  {x.label:18s} {x.from_ft:6.0f} {x.to_ft:6.0f} {x.V:7.3f} "
          f"{x.D50_required:8.3f}  {x.scdot_class:10s} {x.within_protection}")
    w(f"  Headwall class for a lined channel with no pool: "
      f"{r.headwall_class_lined}")
    w("")
    w("9. Receiving channel check, HEC-15 shear basis")
    w(f"  {r.channel_vs_perm}")
    w(f"  Bed shear tau = gamma TW S = {_num(r.tau, 3)} psf  ({r.shear_result})")
    w(f"  Required bed D50 = tau / (0.047 (Ss-1) gamma) = "
      f"{_num(r.D50_channel, 3)} ft   Class: {r.channel_class}")
    w(f"  Finding: {r.channel_finding}")
    w("")
    w("10. Design summary")
    w(f"  Option 1, lined channel (no pool): {r.option_1}")
    w(f"  Option 2, riprap basin: {r.option_2}")
    w(f"  Outlet protection length: {_num(r.L_adopted, 0)} ft")
    w(f"  Receiving channel: {r.channel_finding}")
    w(f"  Vertical limits: {r.vertical_limits}")
    w(f"  Banks: {r.banks}")
    w(f"  Basis: {r.basis}")
    return "\n".join(L)


# --------------------------------------------------------------------------
# Worked examples (US176 culverts from the source workbook)
# --------------------------------------------------------------------------

EXAMPLES: Dict[str, Inputs] = {
    "culv1": Inputs(
        project="US176", culvert="Culvert 1",
        description="Dual 7 ft x 7 ft RCB, run in HY-8 as one 14 ft wide outlet",
        design_storm="50-yr (SCDOT primary route)",
        Q=639.56, Wo=14, rise=7, embedment=1, yo=2.8, Vo=16.32, TW=5.14,
        V_channel=7.02, slope=0.0211, V_perm=4, tau_perm=2.1, Ss=2.65,
        D50_trial=0.75, min_class="B",
        V_LB=[11.741, 6.235, 4.145, 3.102], HS_hy8=1.819),
    "culv2": Inputs(
        project="US176", culvert="Culvert 2",
        description="Dual 6 ft x 6 ft RCB, run in HY-8 as one 12 ft wide outlet",
        design_storm="50-yr (SCDOT primary route)",
        Q=303.1, Wo=12, rise=6, embedment=1, yo=5, Vo=5.05, TW=5.27,
        V_channel=1.61, slope=None, V_perm=4, tau_perm=2.1, Ss=2.65,
        D50_trial=0.75, min_class="B",
        V_LB=[4.291, 2.794, 1.857, 1.39], HS_hy8=None),
    "culv4": Inputs(
        project="US176", culvert="Culvert 4",
        description="Dual 7 ft x 7 ft RCB, run in HY-8 as one 14 ft wide outlet",
        design_storm="50-yr (SCDOT primary route)",
        Q=453, Wo=14, rise=7, embedment=1, yo=3.96, Vo=8.17, TW=3.96,
        V_channel=1.89, slope=0.003, V_perm=4, tau_perm=2.1, Ss=2.65,
        D50_trial=0.75, min_class="B",
        V_LB=[6.46, 3.717, 2.471, 1.849], HS_hy8=None),
}


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _results_to_dict(r: Results) -> Dict:
    return asdict(r)


def _as_key(text: Union[str, int, None], allow_float: bool = False):
    """CLI selector: int string -> int, float string -> float, else str."""
    if text is None or isinstance(text, int):
        return text
    s = str(text).strip()
    if s.lstrip("-").isdigit():
        return int(s)
    if allow_float:
        try:
            return float(s)
        except ValueError:
            pass
    return s


def _inputs_from_hy8_args(a: argparse.Namespace) -> Inputs:
    """Assemble Inputs from --hy8 and friends."""
    import hy8_io  # local module, imported here to keep the core standalone

    overrides: Dict = {}
    if a.v_lb is not None:
        overrides["V_LB"] = list(a.v_lb)
    if a.hs is not None:
        overrides["HS_hy8"] = a.hs
    if a.d50 is not None:
        overrides["D50_trial"] = a.d50
    if a.min_class is not None:
        overrides["min_class"] = a.min_class
    if a.v_perm is not None:
        overrides["V_perm"] = a.v_perm
    if a.tau_perm is not None:
        overrides["tau_perm"] = a.tau_perm
    if a.slope is not None:
        overrides["slope"] = a.slope
    if a.design_storm is not None:
        overrides["design_storm"] = a.design_storm

    flow = _as_key(a.flow, allow_float=True)
    if flow is None:
        flow = -1  # resolved below to the last column
    inp = hy8_io.inputs_from_hy8(
        a.hy8, _as_key(a.crossing), _as_key(a.culvert), flow,
        rst_path=a.rst, **overrides)
    if a.v_lb is None:
        print("WARNING: no --v-lb given; jet velocities at 1 to 4 LB are 0. "
              "Blocks 6 to 8 and 10 are placeholders until you enter the "
              "HY-8 Energy Dissipation values.", file=sys.stderr)
    return inp


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="HEC-14 Ch. 10 culvert outlet protection (HY-8 workflow).")
    p.add_argument("inputs", nargs="?", help="JSON file with block 1 inputs")
    p.add_argument("--example", choices=sorted(EXAMPLES),
                   help="run a built-in worked example")
    p.add_argument("--template", action="store_true",
                   help="print a blank inputs JSON and exit")
    p.add_argument("--json-out", metavar="FILE",
                   help="also write full results as JSON")
    p.add_argument("--out", metavar="FILE", help="write the text report here")
    p.add_argument("--inputs-out", metavar="FILE",
                   help="write the assembled block 1 inputs as JSON "
                        "(useful after --hy8, to edit and rerun)")

    hy8 = p.add_argument_group(
        "HY-8 import",
        "Read Q, yo, Vo, TW, channel velocity and geometry from an HY-8 "
        "project (.hy8) and its results (.rst). Energy Dissipation values "
        "are not in those files: give --v-lb and --hs.")
    hy8.add_argument("--hy8", metavar="FILE", help="HY-8 project file")
    hy8.add_argument("--rst", metavar="FILE",
                     help="results file (default: same name as .hy8)")
    hy8.add_argument("--crossing", default=0,
                     help="crossing name or 0-based index (default 0)")
    hy8.add_argument("--culvert", default=0,
                     help="culvert name or 0-based index (default 0)")
    hy8.add_argument("--flow", default=None,
                     help="flow name (e.g. 50-yr), 0-based column index, or "
                          "total discharge in cfs (default: last column)")
    hy8.add_argument("--v-lb", nargs=4, type=float, metavar="V",
                     help="HY-8 jet velocity at 1, 2, 3, 4 LB, fps")
    hy8.add_argument("--hs", type=float, help="HY-8 Pool Depth HS, ft")
    hy8.add_argument("--d50", type=float, help="trial D50, ft (default 0.75)")
    hy8.add_argument("--min-class", choices=CLASS_NAMES,
                     help="minimum SCDOT class (default B)")
    hy8.add_argument("--v-perm", type=float,
                     help="permissible velocity, fps (default 4)")
    hy8.add_argument("--tau-perm", type=float,
                     help="permissible shear, psf (default 2.1)")
    hy8.add_argument("--slope", type=float,
                     help="channel slope override, ft/ft")
    hy8.add_argument("--design-storm", help="label for the report")
    a = p.parse_args(argv)

    if a.template:
        print(json.dumps(asdict(Inputs()), indent=2))
        return 0
    if a.example:
        inp = EXAMPLES[a.example]
    elif a.hy8:
        inp = _inputs_from_hy8_args(a)
    elif a.inputs:
        with open(a.inputs, encoding="utf-8") as fh:
            inp = Inputs.from_dict(json.load(fh))
    else:
        p.error("give an inputs JSON file, --hy8, --example or --template")

    if a.inputs_out:
        with open(a.inputs_out, "w", encoding="utf-8") as fh:
            json.dump(asdict(inp), fh, indent=2)

    r = analyze(inp)
    report = format_report(inp, r)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(report + "\n")
    else:
        print(report)
    if a.json_out:
        with open(a.json_out, "w", encoding="utf-8") as fh:
            json.dump({"inputs": asdict(inp), "results": _results_to_dict(r)},
                      fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
