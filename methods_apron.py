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
    if supercritical and d != diameter and (tailwater < 0.4 * diameter or d < tailwater <= diameter):
        raise ValueError("Supercritical tailwater bound depends on D versus D'; review required")
    if tailwater > d:
        raise ValueError("High tailwater: evaluate HEC-14 section 10.3")
    tw = max(0.4 * d, tailwater or 0)
    return {"d50_ft": 0.2*d*(q/math.sqrt(32.2*d**5))**(4/3)*d/tw,
            "effective_diameter_ft": d, "tailwater_used_ft": tw,
            "reference": "HEC-14 (2006) equations 10.4–10.5",
            "scope": "Stone size only; apron geometry not evaluated",
            "status": "Restricted calculation; integration verification pending"}


# HEC-14 (2006) Table 10.1 example classes, distinct from SCDOT gradations.
# Nominal D50 (in), length / diameter, thickness / nominal D50.
EXAMPLE_CLASSES = ((5, 4, 3.5), (6, 4, 3.3), (10, 5, 2.4),
                   (14, 6, 2.2), (20, 7, 2.0), (22, 8, 2.0))


def apron_screen(q, diameter, tailwater, specific_gravity, **options):
    result = apron_d50(q, diameter, tailwater, **options)
    if not math.isfinite(specific_gravity) or specific_gravity <= 1:
        raise ValueError("Specific gravity must exceed 1")
    required = result["d50_ft"] * 2.65 / specific_gravity
    result.update(d50_ft=required, scope="FHWA example gradation and apron geometry")
    for number, (size, length_factor, thickness_factor) in enumerate(EXAMPLE_CLASSES, 1):
        if size / 12 >= required:
            length = diameter * length_factor
            result.update(example_class=number, length_ft=length,
                          thickness_ft=size / 12 * thickness_factor,
                          end_width_ft=3 * diameter + 2 * length / 3)
            return result
    raise ValueError("Required D50 exceeds FHWA Table 10.1 example classes")
