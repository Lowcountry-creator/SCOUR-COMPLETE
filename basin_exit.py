"""HEC-14 (2006), section 10.1.5, Step 4. US customary units."""
import math


def basin_exit(q, width, side_slope, g, allowable):
    """Critical flow at a trapezoidal basin exit. Side slope is H:V."""
    if type(side_slope) not in (float, int) or not math.isfinite(side_slope) or side_slope < 0:
        raise ValueError("basin_side_slope must be a finite nonnegative H:V ratio")
    # Rectangular critical depth brackets the root for outward-sloping banks.
    low, high = 0.0, ((q / width) ** 2 / g) ** (1 / 3)
    for _ in range(64):
        depth = (low + high) / 2
        area = depth * (width + side_slope * depth)
        top = width + 2 * side_slope * depth
        if g * area**3 < q**2 * top:
            low = depth
        else:
            high = depth
    velocity = q / area
    return {"depth_ft": depth, "velocity_fps": velocity, "allowable_fps": allowable,
            "passes": velocity <= allowable}
