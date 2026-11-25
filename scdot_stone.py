"""SCDOT 2025 Standard Specifications §804.2.1, p. 800-11 (ft)."""
# Class, 50 percent finer, 100 percent finer.
GRADATIONS = (
    ("A", 0.50, 0.75), ("B", 0.75, 1.33), ("C", 1.30, 1.80),
    ("D", 1.80, 2.25), ("E", 2.25, 2.85), ("F", 2.85, 3.60),
)


def reach_class(required, minimum):
    floor = next(d50 for name, d50, _ in GRADATIONS if name == minimum)
    return next((name for name, d50, _ in GRADATIONS if d50 >= max(floor, required)),
                "Exceeds Class F")
