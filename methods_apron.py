"""HEC-14 section 10.2 restricted circular apron benchmark implementation."""
import math

def apron_d50(q, diameter, tailwater, *, supercritical=False, normal_depth=None):
    """US customary, single circular nonembedded outlet, Ss=2.65 only.
    High tailwater is routed to section 10.3 rather than silently clamped.
    Returns stone size only, not a complete design.
    """
    if not all(math.isfinite(x) and x > 0 for x in (q, diameter)):
        raise ValueError("Positive finite discharge and diameter required")
    if diameter > 5:
        raise ValueError("Outside conservative 60-inch screening limit")
    d = diameter
    if supercritical:
        if normal_depth is None or not 0 < normal_depth <= diameter:
            raise ValueError("Valid supercritical normal depth required")
        d = (diameter + normal_depth) / 2
    if tailwater is not None and (not math.isfinite(tailwater) or tailwater < 0):
        raise ValueError("Invalid tailwater")
    if tailwater is None:
        raise ValueError("Explicit tailwater depth in ft required")
    # UNVERIFIED: whether the adjusted diameter governs the tailwater limits.
    if supercritical and (tailwater < 0.4 * diameter or d < tailwater <= diameter):
        raise ValueError("Supercritical tailwater bound depends on D versus D'; review required")
    if tailwater > d:
        raise ValueError("High tailwater: evaluate HEC-14 section 10.3")
    tw = max(0.4 * d, tailwater or 0)
    return {"d50_ft": 0.2*d*(q/math.sqrt(32.2*d**5))**(4/3)*d/tw,
            "effective_diameter_ft": d, "tailwater_used_ft": tw,
            "reference": "HEC-14 (2006) equations 10.4–10.5",
            "scope": "Stone size only; apron geometry not evaluated",
            "status": "Restricted calculation; integration verification pending"}
