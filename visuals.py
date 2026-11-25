"""Development graphics from legacy results; not construction drawings."""
from pathlib import Path

def export_velocity_plot(case, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    inp, result = case["inputs"], case["legacy"]
    fig, ax = plt.subplots(figsize=(8, 4))
    if result["TW_ye"] > 0.75 and any(result["decay_V"]):
        ax.plot([0] + result["decay_L"], [inp["Vo"]] + result["decay_V"],
                "o-", label="Supplied HY-8 velocities (not independent prediction)")
    else:
        ax.text(.5, .9, "Downstream jet series unavailable", transform=ax.transAxes,
                ha="center")
    ax.axhline(inp["V_channel"], linestyle="--", label="Ambient channel")
    ax.axhline(inp["V_perm"], linestyle=":", label="Permissible velocity")
    ax.set(xlabel="Distance downstream (ft)", ylabel="Velocity (fps)",
           title="Development only — unverified legacy results")
    ax.legend()
    ax.grid(True, alpha=.3)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)

def export_orbit(case, path, *, plotlyjs=True):
    """Conceptual basin surface, not predicted scour; no invented dimensions."""
    import plotly.graph_objects as go
    r, inp = case["legacy"], case["inputs"]
    if r["basin_applies"] != "Yes" or r["Fr"] >= 3:
        raise ValueError("No eligible legacy basin geometry to visualize")
    length, width, depth = r["Lb"], r["Wb"], r["hs"]
    if not all(isinstance(v, (int, float)) and v > 0 for v in (length, width, depth)):
        raise ValueError("Missing basin geometry")
    # I02: illustrative interpolation, not a calculated scour surface.
    xs, ys, zs = [], [], []
    for i in range(41):
        t = i / 40
        w = inp["Wo"] + (width - inp["Wo"]) * t
        xs.append([length*t]*21)
        ys.append([w*(j/20-.5) for j in range(21)])
        zs.append([-depth*4*t*(1-t)*4*(j/20)*(1-j/20) for j in range(21)])
    fig = go.Figure(go.Surface(x=xs, y=ys, z=zs, colorscale="Earth"))
    fig.update_layout(title="I02: Conceptual unverified basin — NOT FOR CONSTRUCTION",
                      scene=dict(aspectmode="data", xaxis_title="Distance (ft)",
                                 yaxis_title="Width (ft)", zaxis_title="Relative elevation (ft)"))
    fig.write_html(str(path), include_plotlyjs=plotlyjs)
