"""Populate outlet protection inputs from HY-8 project and result files.

Two HY-8 files carry what block 1 needs:

``.hy8`` (project, inputs only)
    Culvert shape, span, rise, number of barrels, embedment, and the
    tailwater channel slope. Lengths are stored in ft and flows in cfs
    whatever the display units.

``.rst`` (results, written by HY-8 when a crossing is analyzed)
    Per culvert "Culvert Summary Table": Culvert Discharge, Outlet Depth,
    Outlet Velocity, Tailwater Depth, Tailwater Velocity, one column per
    flow. These are the design storm row values the workbook asks for.

Not in either file, so still typed: the HY-8 Energy Dissipation screen
values (jet velocity at 1 to 4 LB, Pool Depth HS), the trial D50, the
minimum class, and the SCDOT permissible velocity and shear.

Parsing is adapted from HY-8_Exporter (hy8_reader.py, hy8_results.py; MIT,
same author) and trimmed to the cards and tables this tool uses.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Union

from hec14_outlet_protection import Inputs

# HY-8 8.x ShapeDB order. Project files store a one-based index.
SHAPE_NAMES = (
    "Circular", "Concrete Box", "Elliptical", "Pipe Arch", "User Defined",
    "Arch, Open Bottom", "Low-Profile Arch", "High-Profile Arch", "Metal Box",
    "Concrete Open-Bottom Arch", "South Dakota Concrete Box Culvert",
)
# Shapes this tool can analyze and the Inputs.shape value each maps to.
SHAPE_TO_INPUT = {
    "Circular": "circular",
    "Concrete Box": "box",
    "Metal Box": "box",
    "South Dakota Concrete Box Culvert": "box",
}
TAILWATER_TYPES = {
    1: "Rectangular channel", 2: "Trapezoidal channel",
    3: "Triangular channel", 4: "Irregular channel",
    5: "Rating curve", 6: "Constant tailwater elevation",
}
# CHANNELGEOMETRY card for types 1 to 3: bottom width, side slope, slope,
# Manning n, channel invert. Confirmed on HY-8 8.0.1.2 demo projects.
CHANNEL_SLOPE_INDEX = 2
CHANNEL_TYPES_WITH_SLOPE = {1, 2, 3}

_VALUE = re.compile(
    r"^(?P<num>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?)(?P<q>\*+)?$")
_UNIT = re.compile(r"\(([^)]*)\)")


# --------------------------------------------------------------------------
# .hy8 project file
# --------------------------------------------------------------------------


@dataclass
class Hy8Culvert:
    name: str
    shape_code: int = 0
    span_ft: float = 0.0
    rise_ft: float = 0.0
    barrels: int = 1
    embed_depth_ft: float = 0.0
    outlet_invert_ft: Optional[float] = None

    @property
    def shape(self) -> str:
        if 1 <= self.shape_code <= len(SHAPE_NAMES):
            return SHAPE_NAMES[self.shape_code - 1]
        return f"Shape code {self.shape_code}"


@dataclass
class Hy8Crossing:
    name: str
    guid: str = ""
    discharge_method: Optional[int] = None
    design_list_cfs: List[float] = field(default_factory=list)
    user_list_cfs: List[float] = field(default_factory=list)
    user_names: List[str] = field(default_factory=list)
    discharge_range_cfs: List[float] = field(default_factory=list)
    tailwater_type: Optional[int] = None
    channel_geometry: List[float] = field(default_factory=list)
    culverts: List[Hy8Culvert] = field(default_factory=list)

    @property
    def flows_cfs(self) -> List[float]:
        """Active flow list, as HY-8 would run it."""
        if self.discharge_method == 1:
            return list(self.user_list_cfs)
        if self.discharge_method == 0:
            if self.design_list_cfs:
                return list(self.design_list_cfs)
            if len(self.discharge_range_cfs) == 3:
                return list(self.discharge_range_cfs)
        return []

    @property
    def flow_names(self) -> List[str]:
        names = list(self.user_names) if self.discharge_method == 1 else []
        return names + [""] * (len(self.flows_cfs) - len(names))

    @property
    def channel_slope(self) -> Optional[float]:
        """Tailwater channel slope, ft/ft, when the channel type carries one."""
        if self.tailwater_type in CHANNEL_TYPES_WITH_SLOPE \
                and len(self.channel_geometry) > CHANNEL_SLOPE_INDEX:
            return self.channel_geometry[CHANNEL_SLOPE_INDEX]
        return None


@dataclass
class Hy8Project:
    title: str = ""
    units_flag: Optional[int] = None
    crossings: List[Hy8Crossing] = field(default_factory=list)

    def crossing(self, name_or_index: Union[str, int]) -> Hy8Crossing:
        return _pick(self.crossings, name_or_index, "crossing")


def _string(value: str) -> str:
    match = re.search(r'"(.*)"', value)
    return match.group(1) if match else value.strip()


def _floats(value: str) -> List[float]:
    out = []
    for token in value.split():
        try:
            out.append(float(token))
        except ValueError:
            break
    return out


def _int(value: str, default: int = 0) -> int:
    numbers = _floats(value)
    return int(numbers[0]) if numbers else default


def _pick(items, key, what):
    """Select by exact name (case-insensitive), then by 0-based index."""
    if isinstance(key, int):
        if 0 <= key < len(items):
            return items[key]
        raise ValueError(f"{what} index {key} out of range (0 to {len(items) - 1})")
    for item in items:
        if item.name.lower() == str(key).lower():
            return item
    names = ", ".join(repr(i.name) for i in items)
    raise ValueError(f"No {what} named {key!r}. Available: {names}")


def read_hy8(path: Union[str, Path]) -> Hy8Project:
    """Parse the cards this tool needs from an HY-8 project file."""
    path = Path(path)
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines or not lines[0].strip().upper().startswith("HY8PROJECTFILE"):
        raise ValueError(f"{path.name} is not an HY-8 project file")
    project = Hy8Project()
    crossing: Optional[Hy8Crossing] = None
    culvert: Optional[Hy8Culvert] = None
    in_notes: Optional[str] = None

    for raw in lines[1:]:
        stripped = raw.strip()
        if not stripped:
            continue
        parts = stripped.split(None, 1)
        key = parts[0].upper()
        value = parts[1] if len(parts) > 1 else ""

        if in_notes:  # Skip free text until its END card.
            if key == in_notes:
                in_notes = None
            continue
        if key == "STARTPROJNOTES":
            in_notes = "ENDPROJNOTES"
        elif key == "STARTCULVNOTES":
            in_notes = "ENDCULVNOTES"
        elif key == "UNITS":
            project.units_flag = _int(value)
        elif key == "PROJTITLE":
            project.title = _string(value)
        elif key == "STARTCROSSING":
            crossing = Hy8Crossing(_string(value))
            project.crossings.append(crossing)
        elif key == "ENDCROSSING":
            crossing = None
        elif crossing is None:
            continue
        elif key == "STARTCULVERT":
            culvert = Hy8Culvert(_string(value))
            crossing.culverts.append(culvert)
        elif key == "ENDCULVERT":
            culvert = None
        elif culvert is not None:
            if key == "CULVERTSHAPE":
                culvert.shape_code = _int(value)
            elif key == "BARRELDATA":
                data = _floats(value) + [0.0, 0.0]
                culvert.span_ft, culvert.rise_ft = data[0], data[1]
            elif key == "NUMBEROFBARRELS":
                culvert.barrels = _int(value, 1)
            elif key == "EMBEDDEPTH":
                culvert.embed_depth_ft = (_floats(value) or [0.0])[0]
            elif key == "INVERTDATA":
                inv = _floats(value)
                culvert.outlet_invert_ft = inv[3] if len(inv) >= 4 else None
        else:
            if key == "CROSSGUID":
                crossing.guid = value.strip()
            elif key == "DISCHARGERANGE":
                crossing.discharge_range_cfs = _floats(value)
            elif key == "DISCHARGEMETHOD":
                crossing.discharge_method = _int(value)
            elif key == "DISCHARGEXYDESIGN_Y":
                crossing.design_list_cfs.append((_floats(value) or [0.0])[0])
            elif key == "DISCHARGEXYUSER_Y":
                crossing.user_list_cfs.append((_floats(value) or [0.0])[0])
            elif key == "DISCHARGEXYUSER_NAME":
                crossing.user_names.append(_string(value))
            elif key == "TAILWATERTYPE":
                crossing.tailwater_type = _int(value)
            elif key == "CHANNELGEOMETRY":
                crossing.channel_geometry = _floats(value)

    if not project.crossings:
        raise ValueError(f"{path.name} contains no crossings")
    return project


# --------------------------------------------------------------------------
# .rst results file
# --------------------------------------------------------------------------


@dataclass
class RstTable:
    title: str
    culvert_index: Optional[int]
    rows: Dict[str, List[Optional[float]]] = field(default_factory=dict)
    units: Dict[str, str] = field(default_factory=dict)

    def row(self, prefix: str) -> List[Optional[float]]:
        """Values of the first row whose name starts with ``prefix``."""
        want = prefix.lower().replace(" ", "")
        for name, values in self.rows.items():
            if name.lower().replace(" ", "").startswith(want):
                return values
        raise KeyError(f"No row starting with {prefix!r} in {self.title!r}")

    def unit(self, prefix: str) -> str:
        want = prefix.lower().replace(" ", "")
        for name, unit in self.units.items():
            if name.lower().replace(" ", "").startswith(want):
                return unit
        return ""


@dataclass
class RstCrossing:
    guid: str = ""
    name: str = ""
    tables: List[RstTable] = field(default_factory=list)

    def culvert_summary(self, key: Union[str, int]) -> RstTable:
        """'Culvert Summary Table' for a culvert by name or 0-based index."""
        summaries = [t for t in self.tables
                     if t.title.startswith("Culvert Summary Table")]
        if isinstance(key, int):
            for t in summaries:
                if t.culvert_index == key:
                    return t
            raise ValueError(f"No Culvert Summary Table for culvert index {key}")
        for t in summaries:
            name = t.title.split(" - ", 1)[1].strip() if " - " in t.title else ""
            if name.lower() == str(key).lower():
                return t
        names = ", ".join(repr(t.title.split(" - ", 1)[-1]) for t in summaries)
        raise ValueError(f"No Culvert Summary Table named {key!r}. "
                         f"Available: {names}")


def _cell(text: str) -> Optional[float]:
    match = _VALUE.match(text.strip())
    return float(match.group("num")) if match else None


def read_rst(path: Union[str, Path]) -> List[RstCrossing]:
    """Parse an HY-8 .rst file into crossings with their Dialog tables."""
    crossings: List[RstCrossing] = []
    current: Optional[RstCrossing] = None
    table: Optional[RstTable] = None
    pending: Dict[str, str] = {}
    for raw in Path(path).read_text(encoding="utf-8",
                                    errors="replace").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("CrossingGUID:"):
            current = RstCrossing(guid=line.split(":", 1)[1].strip())
            crossings.append(current)
            table, pending = None, {}
            continue
        if line == "EndCrossing":
            current, table = None, None
            continue
        if current is None:
            current = RstCrossing()
            crossings.append(current)
        head = line.split(":", 1)
        if len(head) == 2 and head[0] in ("Table", "Culvert", "BrokenBack") \
                and "," not in line:
            pending[head[0]] = head[1].strip()
            continue
        if line.startswith("Dialog:"):
            title = line.split(":", 1)[1].strip()
            idx = pending.get("Culvert", "")
            table = RstTable(title, int(idx) if idx.isdigit() else None)
            current.tables.append(table)
            pending = {}
            if title.startswith("Summary of Flows at Crossing - "):
                current.name = title.split(" - ", 1)[1].strip()
            continue
        if table is not None and "," in line:
            label, *cells = line.split(",")
            match = _UNIT.search(label)
            name = _UNIT.sub("", label).strip()
            table.rows[name] = [_cell(c) for c in cells]
            table.units[name] = match.group(1).strip() if match else ""
    return crossings


def _pick_rst_crossing(results: Sequence[RstCrossing],
                       crossing: Hy8Crossing) -> RstCrossing:
    for r in results:
        if crossing.guid and r.guid == crossing.guid:
            return r
    for r in results:
        if r.name.lower() == crossing.name.lower():
            return r
    names = ", ".join(repr(r.name) for r in results)
    raise ValueError(f"No results for crossing {crossing.name!r} in the .rst "
                     f"file. Available: {names}")


# --------------------------------------------------------------------------
# Build Inputs
# --------------------------------------------------------------------------


def _flow_index(crossing: Hy8Crossing, table: RstTable,
                flow: Union[str, int, float]) -> int:
    """Resolve a flow by name ('50-yr'), 0-based index, or discharge."""
    names = crossing.flow_names
    totals = table.row("Total Discharge")
    if isinstance(flow, int) and not isinstance(flow, bool):
        if -len(totals) <= flow < len(totals):
            return flow % len(totals)  # negative counts from the end
        raise ValueError(f"flow index {flow} out of range (0 to {len(totals) - 1})")
    if isinstance(flow, float):
        for i, q in enumerate(totals):
            if q is not None and abs(q - flow) <= 0.5:
                return i
        raise ValueError(f"No flow column within 0.5 cfs of {flow} cfs. "
                         f"Columns: {totals}")
    key = str(flow).lower()
    for i, n in enumerate(names):
        if n.lower() == key:
            return i
    avail = ", ".join(repr(n) for n in names if n) or "(unnamed)"
    raise ValueError(f"No flow named {flow!r}. Available: {avail}. You can "
                     "also give a 0-based column index or a discharge in cfs.")


def inputs_from_hy8(hy8_path: Union[str, Path],
                    crossing: Union[str, int],
                    culvert: Union[str, int],
                    flow: Union[str, int, float],
                    rst_path: Optional[Union[str, Path]] = None,
                    **overrides) -> Inputs:
    """Build block 1 ``Inputs`` from an HY-8 project and its results.

    Parameters
        hy8_path   .hy8 project file.
        crossing   crossing name or 0-based index in the project.
        culvert    culvert name or 0-based index within the crossing.
        flow       flow name ('50-yr'), 0-based column index, or total
                   crossing discharge in cfs (float).
        rst_path   .rst results file; defaults to hy8_path with .rst.
        overrides  any Inputs field, typed values: V_LB, HS_hy8, D50_trial,
                   min_class, V_perm, tau_perm, slope, design_storm, ...

    Q is the culvert's own discharge (all its barrels), not the crossing
    total, so Vo = Q / (Wo yo) ties to the HY-8 Outlet Velocity.
    """
    hy8_path = Path(hy8_path)
    rst_path = Path(rst_path) if rst_path else hy8_path.with_suffix(".rst")
    if not rst_path.exists():
        raise FileNotFoundError(
            f"{rst_path.name} not found. Analyze the crossing in HY-8 so it "
            "writes the results file, or pass rst_path.")

    project = read_hy8(hy8_path)
    xing = project.crossing(crossing)
    culv = _pick(xing.culverts, culvert, "culvert")
    shape = SHAPE_TO_INPUT.get(culv.shape)
    if shape is None:
        raise ValueError(f"Culvert {culv.name!r} is {culv.shape}; this tool "
                         "handles box and circular outlets only.")

    results = read_rst(rst_path)
    rst_xing = _pick_rst_crossing(results, xing)
    table = rst_xing.culvert_summary(culv.name if isinstance(culvert, str)
                                     else culvert)
    for prefix, want in (("Outlet Depth", "ft"), ("Outlet Velocity", "ft/s")):
        unit = table.unit(prefix)
        if unit and unit != want:
            raise ValueError(f"{prefix} is in {unit}; expected {want}. Run "
                             "HY-8 in English units.")

    i = _flow_index(xing, table, flow)
    names = xing.flow_names

    def val(prefix: str) -> float:
        v = table.row(prefix)[i]
        if v is None:
            raise ValueError(f"{prefix} is blank for flow column {i}")
        return v

    span = culv.span_ft
    data = dict(
        project=project.title,
        culvert=f"{xing.name}: {culv.name}",
        description=(f"{culv.barrels} x {span:g} ft x {culv.rise_ft:g} ft "
                     f"{culv.shape}, {culv.barrels * span:g} ft total width"),
        design_storm=names[i] if i < len(names) and names[i]
        else f"{val('Total Discharge'):g} cfs total",
        hy8_file=hy8_path.name,
        shape=shape,
        barrels=culv.barrels,
        Q=val("Culvert Discharge"),
        yo=val("Outlet Depth"),
        Vo=val("Outlet Velocity"),
        TW=val("Tailwater Depth"),
        V_channel=val("Tailwater Velocity"),
        Wo=culv.barrels * span,
        rise=culv.rise_ft,
        embedment=culv.embed_depth_ft,
        slope=xing.channel_slope,
    )
    data.update(overrides)
    return Inputs.from_dict(data)
