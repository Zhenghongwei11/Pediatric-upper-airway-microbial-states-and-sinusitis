#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from scipy.stats import gaussian_kde


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
PLOTS = ROOT / "plots" / "publication"
PDF_DIR = PLOTS / "pdf"
PNG_DIR = PLOTS / "png"

COLORS = {
    "blue": "#0072B2",
    "sky": "#56B4E9",
    "orange": "#E69F00",
    "vermillion": "#D55E00",
    "green": "#009E73",
    "purple": "#CC79A7",
    "gray": "#7A7A7A",
    "light_gray": "#E8E8E8",
    "black": "#1F1F1F",
}


def configure_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 8,
            "axes.labelsize": 8,
            "axes.titlesize": 9,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "legend.fontsize": 7,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def save_figure(fig: plt.Figure, name: str) -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(PDF_DIR / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(PNG_DIR / f"{name}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def panel_label(ax: plt.Axes, label: str, x: float = -0.08, y: float = 1.06) -> None:
    ax.text(x, y, label, transform=ax.transAxes, fontsize=11, fontweight="bold", va="top", ha="left")


def percent(values: pd.Series | np.ndarray | list[float]) -> np.ndarray:
    return np.asarray(values, dtype=float) * 100


def wilson_interval(events: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total == 0:
        return 0.0, 0.0
    p = events / total
    denominator = 1 + z**2 / total
    center = p + z**2 / (2 * total)
    margin = z * math.sqrt((p * (1 - p) + z**2 / (4 * total)) / total)
    return (center - margin) / denominator, (center + margin) / denominator


def draw_card(
    ax: plt.Axes,
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    body: str,
    color: str,
    title_size: float = 8.2,
    body_size: float = 7.2,
) -> None:
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.015,rounding_size=0.025",
        linewidth=1.0,
        edgecolor=color,
        facecolor=color,
        alpha=0.10,
    )
    ax.add_patch(patch)
    ax.text(x + 0.03, y + height - 0.055, title, ha="left", va="top", fontsize=title_size, fontweight="bold")
    ax.text(x + 0.03, y + height - 0.135, body, ha="left", va="top", fontsize=body_size, linespacing=1.25)


# ── CONSORT & LAYOUT HELPERS ─────────────────────────────────────────────────

def _flow_box(
    ax: plt.Axes,
    cx: float, cy: float, w: float, h: float,
    lines: list[str],
    fc: str = "white", ec: str = "#4A4A4A",
    lw: float = 0.85, fontsize: float = 7.2,
    bold_first: bool = False,
    alpha: float = 1.0,
) -> None:
    """Draw a CONSORT-style flowchart box centered at (cx, cy)."""
    patch = FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle="round,pad=0.012,rounding_size=0.018",
        linewidth=lw, edgecolor=ec, facecolor=fc, alpha=alpha,
        zorder=3,
    )
    ax.add_patch(patch)
    n = len(lines)
    spacing = h / (n + 0.8)
    for i, line in enumerate(lines):
        y = cy + h / 2 - spacing * (i + 0.65)
        fw = "bold" if (bold_first and i == 0) else "normal"
        ax.text(cx, y, line, ha="center", va="center",
                fontsize=fontsize, fontweight=fw, zorder=4)


def _flow_arrow(
    ax: plt.Axes,
    x1: float, y1: float, x2: float, y2: float,
    color: str = "#4A4A4A",
) -> None:
    """Draw a vertical or horizontal CONSORT arrow."""
    ax.annotate(
        "", xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(
            arrowstyle="-|>", color=color, lw=0.85, mutation_scale=8
        ),
        zorder=5,
    )


def _half_violin(
    ax: plt.Axes,
    x: float, values: np.ndarray,
    color: str, side: str = "right",
    width: float = 0.32, alpha: float = 0.60,
) -> None:
    """Draw a half kernel-density violin on one side of x."""
    values = values[np.isfinite(values)]
    if len(values) < 3:
        return
    kde = gaussian_kde(values, bw_method=0.35)
    span = values.max() - values.min()
    ymin = max(values.min() - span * 0.08, -2)
    ymax = min(values.max() + span * 0.08, 102)
    ygrid = np.linspace(ymin, ymax, 300)
    density = kde(ygrid)
    density = density / density.max() * width
    if side == "right":
        ax.fill_betweenx(ygrid, x, x + density, color=color,
                         alpha=alpha, linewidth=0, zorder=1)
        ax.plot(x + density, ygrid, color=color, linewidth=0.7, alpha=0.9, zorder=2)
    else:
        ax.fill_betweenx(ygrid, x - density, x, color=color,
                         alpha=alpha, linewidth=0, zorder=1)
        ax.plot(x - density, ygrid, color=color, linewidth=0.7, alpha=0.9, zorder=2)


def make_figure1() -> None:
    """Redesigned Figure 1: CONSORT data flow + ecological state concept + analysis framework."""
    primary = pd.read_csv(RESULTS / "primary" / "prjeb35160_cohort_profile.tsv", sep="\t").iloc[0]
    assignments = pd.read_csv(RESULTS / "replication" / "harmonized_state_assignments.tsv", sep="\t")
    transport = pd.read_csv(RESULTS / "replication" / "state_transportability.tsv", sep="\t")

    prjeb = assignments[assignments["dataset_id"] == "PRJEB35160"].copy()
    endpoint_counts = prjeb["clinical_group"].value_counts()
    shared_states = int(((transport["present_in_prjeb35160"] == "yes") & (transport["present_in_prjna422760"] == "yes")).sum())
    total_states = len(transport)
    n_children = int(primary["independent_children"])
    n_profiles = int(primary["uri_or_sinusitis_profiles"])
    n_sinusitis = int(endpoint_counts.get("Sinusitis", 0))
    n_uri = int(endpoint_counts.get("URI", 0))

    pd.DataFrame(
        [
            {"panel": "A", "message": "public dataset eligibility flow"},
            {"panel": "B", "message": f"{n_children} children; {n_profiles} endpoint profiles"},
            {"panel": "C", "message": "ecological state concept and analysis framework"},
            {"panel": "D", "message": f"{shared_states}/{total_states} dominant-genus categories observed in both cohorts"},
        ]
    ).to_csv(RESULTS / "figures" / "figure1_design.tsv", sep="\t", index=False)

    fig = plt.figure(figsize=(9.4, 5.8))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.16, 1.12, 0.96], wspace=0.12)

    # ── PANEL A: CONSORT-style dataset screening flowchart ───────────────────
    ax_a = fig.add_subplot(gs[0, 0])
    ax_a.set_axis_off()
    ax_a.set_xlim(0, 1)
    ax_a.set_ylim(0, 1)
    panel_label(ax_a, "A", x=-0.04)
    ax_a.set_title("Dataset screening", pad=8, fontsize=9, fontweight="bold", loc="left", x=0.06)

    _flow_box(ax_a, 0.40, 0.855, 0.66, 0.115,
              ["11 public pediatric airway/ENT", "datasets identified and screened"],
              fc="#EFF3FB", ec=COLORS["blue"], fontsize=7.2)
    _flow_arrow(ax_a, 0.40, 0.797, 0.40, 0.728)

    _flow_box(ax_a, 0.34, 0.680, 0.56, 0.095,
              ["Assessed for endpoint and label", "completeness (n = 11)"],
              fc="white", ec="#4A4A4A", fontsize=6.7)

    ax_a.plot([0.62, 0.67], [0.680, 0.680], color="#4A4A4A", lw=0.85, zorder=5)
    _flow_arrow(ax_a, 0.67, 0.680, 0.69, 0.680)
    _flow_box(ax_a, 0.83, 0.680, 0.30, 0.105,
              ["9 excluded after review", "insufficient labels/scope", "or non-pediatric"],
              fc="#F7F7F7", ec="#9E9E9E", fontsize=5.8)

    _flow_arrow(ax_a, 0.34, 0.633, 0.40, 0.558)
    _flow_box(ax_a, 0.40, 0.512, 0.66, 0.090,
              ["2 datasets retained for analysis"],
              fc="#EFF3FB", ec=COLORS["blue"], bold_first=True, fontsize=7.5)

    ax_a.plot([0.40, 0.40], [0.467, 0.440], color="#4A4A4A", lw=0.85, zorder=5)
    ax_a.plot([0.22, 0.72], [0.440, 0.440], color="#4A4A4A", lw=0.85, zorder=5)
    _flow_arrow(ax_a, 0.24, 0.440, 0.24, 0.360)
    _flow_arrow(ax_a, 0.72, 0.440, 0.72, 0.360)

    _flow_box(ax_a, 0.24, 0.290, 0.42, 0.130,
              ["PRJEB35160", f"{n_children} children · {n_profiles} profiles",
               "URI / sinusitis endpoints"],
              fc="#E8F4FD", ec=COLORS["blue"], bold_first=True, fontsize=6.4)
    _flow_box(ax_a, 0.72, 0.290, 0.42, 0.130,
              ["PRJNA422760", "28 children · 56 samples",
               "ENT anatomical context"],
              fc="#FFF3E0", ec=COLORS["orange"], bold_first=True, fontsize=6.4)

    _flow_arrow(ax_a, 0.24, 0.225, 0.24, 0.145)
    _flow_box(ax_a, 0.24, 0.095, 0.42, 0.095,
              ["Primary association", "& robustness analysis"],
              fc="#E8F5E9", ec=COLORS["green"], fontsize=7.0)

    _flow_arrow(ax_a, 0.72, 0.225, 0.72, 0.145)
    _flow_box(ax_a, 0.72, 0.095, 0.42, 0.095,
              ["State transportability", "descriptive analysis"],
              fc="#FFF8E1", ec=COLORS["orange"], fontsize=7.0)

    # ── PANEL B: Ecological state concept diagram ────────────────────────────
    ax_b = fig.add_subplot(gs[0, 1])
    ax_b.set_axis_off()
    ax_b.set_xlim(0, 1)
    ax_b.set_ylim(0, 1)
    panel_label(ax_b, "B", x=-0.04)
    ax_b.set_title("Ecological state classification", pad=8, fontsize=9, fontweight="bold", loc="left", x=0.06)

    genus_colors_list = [COLORS["orange"], COLORS["blue"], COLORS["green"], COLORS["gray"], COLORS["purple"]]
    genus_labels = ["Moraxella", "Haemophilus", "Streptococcus", "Other", "Mixed"]
    states_data = [
        ("Moraxella-dominant",    [0.82, 0.06, 0.05, 0.04, 0.03], COLORS["orange"]),
        ("Haemophilus-dominant",  [0.07, 0.74, 0.08, 0.06, 0.05], COLORS["blue"]),
        ("Streptococcus-dominant",[0.05, 0.08, 0.76, 0.06, 0.05], COLORS["green"]),
        ("Other-dominant",        [0.08, 0.09, 0.09, 0.68, 0.06], COLORS["gray"]),
        ("Mixed community",       [0.18, 0.17, 0.20, 0.22, 0.23], COLORS["purple"]),
    ]

    bar_h = 0.090
    bar_gap = 0.038
    bar_x0 = 0.06
    bar_w = 0.53
    y_start = 0.875

    ax_b.text(bar_x0 + bar_w / 2, y_start + 0.045, "Relative abundance",
              ha="center", va="center", fontsize=7.0, color="#555555")
    ax_b.text(0.75, y_start + 0.045, "State label",
              ha="center", va="center", fontsize=7.0, color="#555555")
    ax_b.axhline(y_start + 0.018, xmin=0.04, xmax=0.96, color="#CCCCCC", lw=0.6)

    for i, (state_name, fracs, state_color) in enumerate(states_data):
        y_bar = y_start - (i + 0.5) * (bar_h + bar_gap) - 0.025
        left = bar_x0
        for frac, gc in zip(fracs, genus_colors_list):
            ax_b.add_patch(Rectangle(
                (left, y_bar - bar_h / 2), frac * bar_w, bar_h,
                facecolor=gc, edgecolor="white", linewidth=0.4, zorder=2
            ))
            left += frac * bar_w
        label_x = bar_x0 + bar_w + 0.065
        lbox = FancyBboxPatch(
            (label_x, y_bar - bar_h * 0.52), 0.34, bar_h * 1.04,
            boxstyle="round,pad=0.008,rounding_size=0.010",
            linewidth=0.8, edgecolor=state_color, facecolor=state_color, alpha=0.12, zorder=2
        )
        ax_b.add_patch(lbox)
        label_color = state_color if state_color != COLORS["gray"] else "#444444"
        ax_b.text(label_x + 0.030, y_bar, state_name,
                  ha="left", va="center", fontsize=5.8, fontweight="bold",
                  color=label_color, zorder=3)
        ax_b.annotate("", xy=(label_x - 0.01, y_bar),
                      xytext=(bar_x0 + bar_w + 0.005, y_bar),
                      arrowprops=dict(arrowstyle="-|>", color="#888888",
                                      lw=0.7, mutation_scale=7), zorder=4)

    total_block = len(states_data) * (bar_h + bar_gap)
    legend_y = y_start - total_block - 0.13
    ax_b.text(0.5, legend_y + 0.055, "Genus colour key",
              ha="center", va="center", fontsize=6.5, color="#666666")
    legend_positions = [(0.08, 0.00), (0.38, 0.00), (0.70, 0.00),
                        (0.22, -0.060), (0.53, -0.060)]
    for (lbl, gc), (lx, dy) in zip(zip(genus_labels, genus_colors_list), legend_positions):
        ax_b.add_patch(Rectangle((lx, legend_y - 0.022 + dy), 0.025, 0.028,
                                  facecolor=gc, edgecolor="none"))
        ax_b.text(lx + 0.034, legend_y - 0.008 + dy, lbl,
                  ha="left", va="center", fontsize=6.3, color="#333333")


    # ── PANEL C: Analysis framework (3 claims) ───────────────────────────────
    ax_c = fig.add_subplot(gs[0, 2])
    ax_c.set_axis_off()
    ax_c.set_xlim(0, 1)
    ax_c.set_ylim(0, 1)
    panel_label(ax_c, "C", x=-0.04)
    ax_c.set_title("Analysis framework", pad=8, fontsize=9, fontweight="bold", loc="left", x=0.06)

    claims = [
        (
            "C1 · Primary association",
            ["Moraxella-dominant state",
             "→ sinusitis-associated profile?",
             "Risk ratio · adjusted OR · 95% CI"],
            COLORS["orange"], 0.750,
        ),
        (
            "C2 · State transportability",
            [f"{shared_states}/{total_states} categories shared",
             "across nasopharyngeal and",
             "adenoid/tonsil compartments"],
            COLORS["blue"], 0.440,
        ),
        (
            "C3 · Child-level robustness",
            ["Child-cluster bootstrap · LOO",
             "Moraxella burden per child",
             "vs sinusitis history"],
            COLORS["green"], 0.130,
        ),
    ]

    for title, lines, color, cy in claims:
        ax_c.add_patch(Rectangle((0.06, cy - 0.09), 0.025, 0.200,
                                  facecolor=color, edgecolor="none", alpha=0.85))
        ax_c.text(0.11, cy + 0.095, title,
                  ha="left", va="top", fontsize=7.6, fontweight="bold", color=color)
        for k, line in enumerate(lines):
            ax_c.text(0.11, cy + 0.040 - k * 0.055, line,
                      ha="left", va="top", fontsize=7.0, color="#333333")
        if cy > 0.14:
            ax_c.axhline(cy - 0.115, xmin=0.06, xmax=0.94, color="#E0E0E0", lw=0.6)

    save_figure(fig, "Figure1_study_design")


def moraxella_contingency() -> pd.DataFrame:
    assignments = pd.read_csv(RESULTS / "replication" / "harmonized_state_assignments.tsv", sep="\t")
    prjeb = assignments[assignments["dataset_id"] == "PRJEB35160"].copy()
    prjeb["moraxella_group"] = np.where(prjeb["state_key"] == "moraxella_dominant", "Moraxella-dominant", "Other profiles")
    return pd.crosstab(prjeb["moraxella_group"], prjeb["clinical_group"]).reindex(["Other profiles", "Moraxella-dominant"]).fillna(0).astype(int)


def threshold_30() -> pd.Series:
    table = pd.read_csv(RESULTS / "tables" / "moraxella_threshold_sensitivity.tsv", sep="\t")
    return table[table["threshold_percent"] == 30].iloc[0]


def parse_ci(ci: str) -> tuple[float, float]:
    left, right = str(ci).split("-")
    return float(left), float(right)


def make_figure2() -> None:
    contingency = moraxella_contingency()
    threshold = threshold_30()
    other_total = int(contingency.loc["Other profiles"].sum())
    mor_total = int(contingency.loc["Moraxella-dominant"].sum())
    other_events = int(contingency.loc["Other profiles", "Sinusitis"])
    mor_events = int(contingency.loc["Moraxella-dominant", "Sinusitis"])
    other_risk = other_events / other_total
    mor_risk = mor_events / mor_total
    risk_diff = mor_risk - other_risk
    rr_low, rr_high = parse_ci(threshold["risk_ratio_ci"])
    or_low, or_high = parse_ci(threshold["adjusted_or_ci"])

    pd.DataFrame(
        [
            {"panel": "A", "group": "Other profiles", "uri": int(contingency.loc["Other profiles", "URI"]), "sinusitis": other_events},
            {"panel": "A", "group": "Moraxella-dominant", "uri": int(contingency.loc["Moraxella-dominant", "URI"]), "sinusitis": mor_events},
            {"panel": "B", "measure": "absolute risk difference", "effect": risk_diff},
            {"panel": "C", "measure": "risk ratio", "effect": threshold["risk_ratio"], "ci": threshold["risk_ratio_ci"]},
            {"panel": "C", "measure": "adjusted odds ratio", "effect": threshold["adjusted_or"], "ci": threshold["adjusted_or_ci"]},
        ]
    ).to_csv(RESULTS / "figures" / "figure2_endpoint_story.tsv", sep="\t", index=False)

    fig = plt.figure(figsize=(7.4, 4.0))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.15, 0.82, 1.05], wspace=0.58)

    # ── Panel A: Proportional endpoint distribution (Marimekko-style) ────────
    ax = fig.add_subplot(gs[0, 0])
    panel_label(ax, "A")
    ax.set_title("Endpoint distribution", fontsize=9)
    x_positions = [0, 1]
    group_names = ["Other profiles", "Moraxella-\ndominant"]
    max_total = max(other_total, mor_total)
    for x, group, xtick_lbl in zip(
        x_positions,
        ["Other profiles", "Moraxella-dominant"],
        group_names,
    ):
        uri = int(contingency.loc[group, "URI"])
        sinusitis = int(contingency.loc[group, "Sinusitis"])
        total = uri + sinusitis
        uri_p = uri / total
        sin_p = sinusitis / total
        width = total / max_total * 0.65
        ax.add_patch(Rectangle((x - width / 2, 0), width, uri_p,
                                color=COLORS["sky"], alpha=0.90, linewidth=0))
        ax.add_patch(Rectangle((x - width / 2, uri_p), width, sin_p,
                                color=COLORS["orange"], alpha=0.90, linewidth=0))
        ax.text(x, uri_p / 2, f"URI\n{uri}",
                ha="center", va="center", fontsize=7, color="white", fontweight="bold")
        ax.text(x, uri_p + sin_p / 2, f"Sinusitis\n{sinusitis}",
                ha="center", va="center", fontsize=7, color="white", fontweight="bold")
        ax.text(x, 1.04, f"n = {total}", ha="center", fontsize=6.8, color="#444444")

    ax.set_xlim(-0.65, 1.65)
    ax.set_ylim(0, 1.13)
    ax.set_xticks(x_positions)
    ax.set_xticklabels(["Other\nprofiles", "Moraxella-\ndominant"])
    ax.set_ylabel("Within-group proportion")
    ax.set_yticks([0, 0.25, 0.50, 0.75, 1.0])
    ax.set_yticklabels(["0", "25%", "50%", "75%", "100%"])
    ax.tick_params(axis="y", length=3)
    # Legend
    ax.add_patch(Rectangle((0.04, 0.92), 0.08, 0.06, transform=ax.transAxes,
                            color=COLORS["sky"], linewidth=0))
    ax.text(0.14, 0.95, "URI", transform=ax.transAxes, fontsize=6.8, va="center")
    ax.add_patch(Rectangle((0.34, 0.92), 0.08, 0.06, transform=ax.transAxes,
                            color=COLORS["orange"], linewidth=0))
    ax.text(0.44, 0.95, "Sinusitis-associated", transform=ax.transAxes, fontsize=6.8, va="center")

    # ── Panel B: Sinusitis risk per group with Wilson CI ─────────────────────
    ax = fig.add_subplot(gs[0, 1])
    panel_label(ax, "B", x=-0.24, y=1.12)
    ax.set_title("Sinusitis-associated risk", fontsize=9, pad=10)
    bar_colors = [COLORS["sky"], COLORS["orange"]]
    risks_pct = [other_risk * 100, mor_risk * 100]
    ax.bar([0, 1], risks_pct, color=bar_colors, width=0.55, zorder=2,
           edgecolor="none")
    for x, risk, events, total, bc in zip(
        [0, 1], [other_risk, mor_risk],
        [other_events, mor_events],
        [other_total, mor_total],
        bar_colors,
    ):
        low, high = wilson_interval(events, total)
        ax.errorbar(x, risk * 100,
                    yerr=[[risk * 100 - low * 100], [high * 100 - risk * 100]],
                    fmt="none", color="#333333",
                    elinewidth=1.1, capsize=3.5, capthick=1.1, zorder=3)
        ax.text(x, high * 100 + 1.6, f"{events}/{total}",
                ha="center", fontsize=6.8, color="#444444")

    # Significance bracket
    ymax_bracket = max(mor_risk, other_risk) * 100 + 13
    ax.plot([0, 0, 1, 1],
            [ymax_bracket - 3, ymax_bracket, ymax_bracket, ymax_bracket - 3],
            color="#444444", lw=0.9)
    ax.text(0.5, ymax_bracket + 1.0,
            f"\u0394 = +{risk_diff * 100:.1f} pp",
            ha="center", fontsize=8, fontweight="bold", color="#222222")

    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Other", "Moraxella-\ndominant"], fontsize=7)
    ax.set_ylabel("Sinusitis-associated profiles (%)")
    ax.set_ylim(0, ymax_bracket + 8)
    ax.yaxis.grid(color=COLORS["light_gray"], linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)

    # ── Panel C: Forest plot (log scale) ─────────────────────────────────────
    ax = fig.add_subplot(gs[0, 2])
    panel_label(ax, "C")
    ax.set_title("Association estimates", fontsize=9)
    effects = pd.DataFrame(
        [
            {"label": "Risk ratio", "effect": float(threshold["risk_ratio"]),
             "low": rr_low, "high": rr_high, "color": COLORS["sky"]},
            {"label": "Adjusted OR", "effect": float(threshold["adjusted_or"]),
             "low": or_low, "high": or_high, "color": COLORS["orange"]},
        ]
    )
    y = np.arange(len(effects))
    for yi, row in effects.iterrows():
        ax.plot([row["low"], row["high"]], [yi, yi],
                color=row["color"], linewidth=2.0, solid_capstyle="round", zorder=2)
        ax.plot([row["low"], row["low"]], [yi - 0.08, yi + 0.08],
                color=row["color"], linewidth=1.3, zorder=2)
        ax.plot([row["high"], row["high"]], [yi - 0.08, yi + 0.08],
                color=row["color"], linewidth=1.3, zorder=2)
        ax.scatter(row["effect"], yi, color=row["color"],
                   s=36, zorder=3, edgecolors="white", linewidths=0.8)
        ax.text(row["high"] * 1.06, yi,
                f"{row['effect']:.2f} ({row['low']:.2f}\u2013{row['high']:.2f})",
                va="center", fontsize=6.6, color="#333333")

    ax.axvline(1, color=COLORS["gray"], linestyle="--", linewidth=0.85, zorder=1)
    ax.set_xscale("log")
    # Tight x-axis: just enough to show CIs + annotation
    x_max = effects["high"].max() * 2.4
    ax.set_xlim(0.88, x_max)
    nice_ticks = [t for t in [1.0, 1.5, 2.0, 2.5] if t <= x_max * 0.7]
    ax.set_xticks(nice_ticks)
    ax.set_xticklabels([f"{t:g}" for t in nice_ticks])
    ax.xaxis.get_offset_text().set_visible(False)
    ax.tick_params(axis="x", which="minor", bottom=False, labelbottom=False)
    ax.set_yticks(y)
    ax.set_yticklabels(effects["label"])
    ax.invert_yaxis()
    ax.set_xlabel("Effect estimate (95% CI, log scale)")
    ax.xaxis.grid(color=COLORS["light_gray"], linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.set_ylim(len(effects) - 0.6, -0.6)

    save_figure(fig, "Figure2_state_outcome")


def make_figure3() -> None:
    """Redesigned Figure 3: half-violin+jitter for A, improved forest for B, lollipop for C."""
    sample_path = RESULTS / "primary" / "sample_genus_abundance.tsv"
    sample = pd.read_csv(sample_path, sep="\t")
    genus_summary = pd.read_csv(RESULTS / "primary" / "genus_abundance_outcome.tsv", sep="\t")
    beta = pd.read_csv(RESULTS / "primary" / "beta_diversity_tests.tsv", sep="\t")
    alpha = pd.read_csv(RESULTS / "primary" / "alpha_diversity_outcome.tsv", sep="\t")

    focus = ["Moraxella", "Haemophilus", "Streptococcus", "Alloiococcus"]
    plot_df = sample[sample["genus"].isin(focus)].copy()
    plot_df["relative_abundance_percent"] = plot_df["relative_abundance"].astype(float) * 100
    summary = genus_summary.set_index("genus").loc[focus].reset_index()

    specificity = pd.DataFrame(
        [
            {"readout": "Moraxella-dominant\ncommunity", "pvalue": float(beta.loc[beta["term"] == "moraxella_dominant", "pvalue"].iloc[0])},
            {"readout": "Endpoint\ncommunity", "pvalue": float(beta.loc[beta["term"] == "clinical_endpoint", "pvalue"].iloc[0])},
            {"readout": "Shannon\nentropy (endpoint)", "pvalue": float(alpha["pvalue"].iloc[0])},
        ]
    )
    plot_df.to_csv(RESULTS / "figures" / "figure3_specificity_story.tsv", sep="\t", index=False)

    fig = plt.figure(figsize=(8.2, 4.5))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.46, 0.92, 0.88], wspace=0.72)

    # ── Panel A: Half-violin + jitter ─────────────────────────────────────────
    ax = fig.add_subplot(gs[0, 0])
    panel_label(ax, "A", x=-0.10, y=1.10)
    ax.set_title("Genus abundance by endpoint", pad=10, fontsize=9)
    rng = np.random.default_rng(20260524)
    outcome_groups = ["URI", "Sinusitis"]
    outcome_colors = {"URI": COLORS["sky"], "Sinusitis": COLORS["orange"]}
    violin_sides = {"URI": "left", "Sinusitis": "right"}
    jitter_offsets = {"URI": -0.06, "Sinusitis": 0.06}

    for idx, genus in enumerate(focus):
        for outcome in outcome_groups:
            vals = plot_df[
                (plot_df["genus"] == genus) & (plot_df["outcome_group"] == outcome)
            ]["relative_abundance_percent"].to_numpy()
            color = outcome_colors[outcome]
            side = violin_sides[outcome]

            violin_width = 0.36 if genus == "Moraxella" else 0.28
            _half_violin(ax, idx, vals, color=color, side=side, width=violin_width, alpha=0.42)

            jitter = rng.normal(0, 0.028, len(vals))
            jx = np.full(len(vals), idx + jitter_offsets[outcome]) + jitter
            ax.scatter(jx, vals, s=4, alpha=0.34, color=color, linewidths=0, zorder=3)

            if len(vals) >= 1:
                med = np.median(vals)
                ax.plot(
                    [idx + jitter_offsets[outcome] - 0.12,
                     idx + jitter_offsets[outcome] + 0.12],
                    [med, med],
                    color="#222222", linewidth=1.4, zorder=4,
                )

    ax.set_xticks(range(len(focus)))
    ax.set_xticklabels(focus, rotation=18, ha="right")
    ax.set_ylabel("Relative abundance (%)")
    ax.set_ylim(-2, 105)
    ax.yaxis.grid(color=COLORS["light_gray"], linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    # Legend
    ax.fill_between([], [], color=COLORS["sky"], alpha=0.55, label="URI")
    ax.fill_between([], [], color=COLORS["orange"], alpha=0.55, label="Sinusitis-associated")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.56, 1.03),
              ncol=2, fontsize=6.8, handlelength=1.1, columnspacing=0.9)

    # ── Panel B: Adjusted taxon forest plot ───────────────────────────────────
    ax = fig.add_subplot(gs[0, 1])
    panel_label(ax, "B", x=-0.12, y=1.10)
    ax.set_title("Adjusted taxon effects", pad=10, fontsize=9)
    summary = summary.sort_values("adjusted_odds_ratio_per_10pct")
    y_pos = np.arange(len(summary))
    for yi, (_, row) in enumerate(summary.iterrows()):
        lo = row["adjusted_ci_lower"]
        hi = row["adjusted_ci_upper"]
        est = row["adjusted_odds_ratio_per_10pct"]
        point_color = COLORS["orange"] if est > 1 else COLORS["blue"]
        ax.plot([lo, hi], [yi, yi], color=point_color, linewidth=2.0,
                solid_capstyle="round", zorder=2)
        ax.plot([lo, lo], [yi - 0.07, yi + 0.07], color=point_color, lw=1.2, zorder=2)
        ax.plot([hi, hi], [yi - 0.07, yi + 0.07], color=point_color, lw=1.2, zorder=2)
        ax.scatter(est, yi, color=point_color, s=32, zorder=3,
                   edgecolors="white", linewidths=0.8)
        ax.text(hi * 1.06, yi, f"{est:.2f}", va="center", fontsize=6.8)

    ax.axvline(1, color=COLORS["gray"], linestyle="--", linewidth=0.85, zorder=1)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(summary["genus"])
    ax.set_xlabel("Adjusted OR per 10 pp\n(relative abundance)")
    ax.xaxis.grid(color=COLORS["light_gray"], linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.set_ylim(-0.6, len(summary) - 0.4)

    # ── Panel C: Specificity lollipop chart ───────────────────────────────────
    ax = fig.add_subplot(gs[0, 2])
    panel_label(ax, "C", x=-0.12, y=1.10)
    ax.set_title("Specificity checks", pad=10, fontsize=9)
    specificity["score"] = -np.log10(np.maximum(specificity["pvalue"].astype(float), 1e-4))
    alpha_line = -math.log10(0.05)
    y_pos_c = np.arange(len(specificity))
    lollipop_colors = [COLORS["orange"], COLORS["sky"], COLORS["sky"]]

    for yi, (_, row) in enumerate(specificity.iterrows()):
        score = row["score"]
        col = lollipop_colors[yi]
        ax.plot([0, score], [yi, yi], color="#CCCCCC", linewidth=1.2, zorder=1)
        ax.scatter(score, yi, color=col, s=48, zorder=3, edgecolors="white", linewidths=0.8)
        p_val = row["pvalue"]
        p_label = "< 0.001" if p_val < 0.001 else (f"{p_val:.3f}" if p_val < 0.995 else "1.00")
        ax.text(score + 0.08, yi, f"P = {p_label}", va="center", fontsize=7.0, color="#333333")

    ax.axvline(alpha_line, color=COLORS["gray"], linestyle="--", linewidth=0.85, zorder=2)
    ax.set_yticks(y_pos_c)
    ax.set_yticklabels(specificity["readout"])
    ax.invert_yaxis()
    ax.set_xlabel("-log10(P value)")
    ax.xaxis.grid(color=COLORS["light_gray"], linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    x_max_c = max(specificity["score"].max() * 1.5, alpha_line * 1.8)
    ax.set_xlim(0, x_max_c)
    ax.text(alpha_line + 0.04, 0.05, "α = 0.05",
            transform=ax.get_xaxis_transform(), fontsize=6.5,
            color=COLORS["gray"], va="bottom")

    save_figure(fig, "Figure3_genus_effects")


def make_figure4() -> None:
    """Redesigned Figure 4: unified colormap, colorbar, and fixed x-axis overflow."""
    transport = pd.read_csv(RESULTS / "replication" / "state_transportability.tsv", sep="\t")
    paired = pd.read_csv(RESULTS / "replication" / "prjna422760_paired_tissue_effects.tsv", sep="\t")
    paired_all = paired[paired["comparison"] == "tonsil_minus_adenoid_all"].copy()
    paired_focus = paired_all[paired_all["genus"].isin(
        ["Moraxella", "Haemophilus", "Streptococcus", "Prevotella", "Porphyromonas", "Fusobacterium"]
    )].copy()
    paired_focus["order"] = paired_focus["genus"].map(
        {"Moraxella": 0, "Haemophilus": 1, "Streptococcus": 2,
         "Fusobacterium": 3, "Prevotella": 4, "Porphyromonas": 5}
    )
    paired_focus = paired_focus.sort_values("order")

    fig = plt.figure(figsize=(7.6, 4.5))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.10, 1.05], wspace=0.48)

    # ── Panel A: Unified heatmap with shared colormap & colorbar ─────────────
    ax = fig.add_subplot(gs[0, 0])
    panel_label(ax, "A")
    ax.set_title("Ecological state profile fractions", fontsize=9)
    states = transport["state_label"].str.replace(" state", "", regex=False).tolist()
    matrix = transport[
        ["prjeb35160_profile_fraction", "prjna422760_profile_fraction"]
    ].astype(float).to_numpy() * 100

    cmap = plt.cm.YlGnBu
    vmin, vmax = 0, 55
    im = ax.imshow(matrix, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)

    ax.set_yticks(range(len(states)))
    ax.set_yticklabels(states, fontsize=7)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["PRJEB35160\n(nasopharynx)", "PRJNA422760\n(adenoid/tonsil)"],
                       fontsize=7.5)

    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            frac = matrix[i, j]
            text_color = "white" if frac > 28 else "#333333"
            ax.text(j, i, f"{frac:.1f}%", ha="center", va="center",
                    fontsize=7, color=text_color)

    # Cell borders
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks(np.arange(-0.5, 2, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(states), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.8)
    ax.tick_params(which="minor", bottom=False, left=False)

    # Colorbar
    from mpl_toolkits.axes_grid1 import make_axes_locatable
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="4%", pad=0.06)
    cb = fig.colorbar(im, cax=cax)
    cb.set_label("% of profiles", fontsize=6.5)
    cb.ax.tick_params(labelsize=6)

    # ── Panel B: Paired adenoid-to-tonsil connected dot plot ─────────────────
    ax = fig.add_subplot(gs[0, 1])
    panel_label(ax, "B")
    ax.set_title("Paired adenoid-to-tonsil shift", fontsize=9)
    y = np.arange(len(paired_focus))

    # Compute x-axis range with proper padding
    all_x = np.concatenate([
        paired_focus["median_adenoid"].to_numpy(),
        paired_focus["median_tonsil"].to_numpy(),
    ])
    x_max = all_x.max() * 1.35

    for yi, (_, row) in enumerate(paired_focus.iterrows()):
        x_a = float(row["median_adenoid"])
        x_t = float(row["median_tonsil"])
        ax.plot([x_a, x_t], [yi, yi], color="#BDBDBD", linewidth=1.1, zorder=1)
        ax.scatter(x_a, yi, color=COLORS["blue"], s=28, zorder=2,
                   edgecolors="white", linewidths=0.6)
        ax.scatter(x_t, yi, color=COLORS["orange"], s=28, zorder=3,
                   edgecolors="white", linewidths=0.6)
        if float(row["fdr"]) < 0.05:
            ax.text(max(x_a, x_t) + x_max * 0.04, yi, "*",
                    va="center", fontsize=10, color="#333333")

    ax.set_yticks(y)
    ax.set_yticklabels(paired_focus["genus"])
    ax.invert_yaxis()
    ax.set_xlabel("Median relative abundance (%)")
    ax.set_xlim(-0.5, x_max)
    ax.xaxis.grid(color=COLORS["light_gray"], linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.scatter([], [], color=COLORS["blue"], label="Adenoid", s=28)
    ax.scatter([], [], color=COLORS["orange"], label="Tonsil", s=28)
    ax.legend(frameon=False, loc="upper right", fontsize=7)
    ax.text(0.98, 0.02, "* FDR < 0.05", transform=ax.transAxes,
            ha="right", va="bottom", fontsize=6.5, color="#666666")

    save_figure(fig, "Figure4_state_transportability")


def make_figure5() -> None:
    """Redesigned Figure 5: beeswarm+violin for A, tighter forest plot for B."""
    child = pd.read_csv(RESULTS / "effect_sizes" / "prjeb35160_child_state_burden.tsv", sep="\t")
    bootstrap = pd.read_csv(RESULTS / "effect_sizes" / "bootstrap_stability.tsv", sep="\t")
    loo = pd.read_csv(RESULTS / "effect_sizes" / "leave_one_child_out_summary.tsv", sep="\t")
    child_sensitivity = pd.read_csv(RESULTS / "effect_sizes" / "child_level_sensitivity.tsv", sep="\t")
    thresholds = pd.read_csv(RESULTS / "tables" / "moraxella_threshold_sensitivity.tsv", sep="\t")

    fig = plt.figure(figsize=(7.4, 4.2))
    gs = fig.add_gridspec(1, 2, width_ratios=[0.92, 1.18], wspace=0.52)

    # ── Panel A: Half-violin + beeswarm-style jitter ──────────────────────────
    ax = fig.add_subplot(gs[0, 0])
    panel_label(ax, "A")
    ax.set_title("Child-level Moraxella burden", fontsize=9)
    rng = np.random.default_rng(20260524)
    group_params = [
        ("no",  "No sinusitis-\nassociated profile", COLORS["sky"],    "right"),
        ("yes", "Any sinusitis-\nassociated profile", COLORS["orange"], "left"),
    ]
    for x, (value, label, color, side) in enumerate(group_params):
        vals = child[child["ever_sinusitis"] == value][
            "moraxella_dominant_profile_fraction"
        ].astype(float).to_numpy() * 100

        _half_violin(ax, x, vals, color=color, side=side, width=0.38, alpha=0.55)

        jitter = rng.normal(0, 0.038, len(vals))
        jx = np.full(len(vals), x) + jitter
        ax.scatter(jx, vals, s=20, alpha=0.72, color=color,
                   edgecolors="white", linewidths=0.5, zorder=3)

        med = np.median(vals)
        q1, q3 = np.percentile(vals, [25, 75])
        ax.plot([x - 0.22, x + 0.22], [med, med],
                color="#1A1A1A", linewidth=1.6, zorder=4, solid_capstyle="round")
        ax.plot([x - 0.10, x + 0.10], [q1, q1],
                color="#555555", linewidth=0.9, zorder=4)
        ax.plot([x - 0.10, x + 0.10], [q3, q3],
                color="#555555", linewidth=0.9, zorder=4)
        ax.text(x, 106, f"n = {len(vals)}", ha="center", fontsize=7, color="#444444")

    ax.set_xticks([0, 1])
    ax.set_xticklabels(["No sinusitis-\nassociated\nprofile",
                         "Any sinusitis-\nassociated\nprofile"], fontsize=7)
    ax.set_ylim(-3, 114)
    ax.set_ylabel("Moraxella-dominant profiles\nper child (%)")
    ax.yaxis.grid(color=COLORS["light_gray"], linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)

    # ── Panel B: Robustness forest plot (tighter x-axis) ─────────────────────
    ax = fig.add_subplot(gs[0, 1])
    panel_label(ax, "B")
    ax.set_title("Sensitivity and robustness checks", fontsize=9)

    rows: list[dict[str, object]] = []
    for _, row in thresholds.iterrows():
        low, high = parse_ci(row["adjusted_or_ci"])
        rows.append({
            "check": f"{int(row['threshold_percent'])}% dominance\nthreshold",
            "effect": row["adjusted_or"], "low": low, "high": high,
            "type": "Adjusted OR",
        })
    boot = bootstrap[bootstrap["exposure"] == "moraxella_dominant"].iloc[0]
    rows.append({
        "check": "Child-cluster\nbootstrap",
        "effect": boot["effect"], "low": boot["ci_lower"], "high": boot["ci_upper"],
        "type": "Risk ratio",
    })
    loo_row = loo[loo["exposure"] == "Moraxella-dominant state"].iloc[0]
    rows.append({
        "check": "Leave-one-\nchild-out",
        "effect": loo_row["median_odds_ratio"],
        "low": loo_row["min_odds_ratio"], "high": loo_row["max_odds_ratio"],
        "type": "Adjusted OR",
    })
    child_row = child_sensitivity[
        child_sensitivity["model"].str.contains("25 percentage-point Moraxella", regex=False)
    ].iloc[0]
    rows.append({
        "check": "Child-level\nburden",
        "effect": child_row["effect"],
        "low": child_row["ci_lower"], "high": child_row["ci_upper"],
        "type": "Odds ratio",
    })
    matrix = pd.DataFrame(rows)
    matrix.to_csv(RESULTS / "figures" / "figure5_robustness_matrix.tsv", sep="\t", index=False)

    y = np.arange(len(matrix))
    type_colors = {"Adjusted OR": COLORS["blue"], "Risk ratio": COLORS["orange"], "Odds ratio": COLORS["green"]}

    for yi, row in matrix.iterrows():
        eff = float(row["effect"])
        lo = float(row["low"])
        hi = float(row["high"])
        col = type_colors.get(str(row["type"]), COLORS["blue"])
        ax.plot([lo, hi], [yi, yi], color=col, linewidth=2.0,
                solid_capstyle="round", zorder=2)
        ax.plot([lo, lo], [yi - 0.08, yi + 0.08], color=col, lw=1.2, zorder=2)
        ax.plot([hi, hi], [yi - 0.08, yi + 0.08], color=col, lw=1.2, zorder=2)
        ax.scatter(eff, yi, color=col, s=32, zorder=3,
                   edgecolors="white", linewidths=0.8)
        ax.text(hi * 1.04, yi, f"{eff:.2f}", va="center", fontsize=6.8, color="#333333")

    ax.axvline(1, color=COLORS["gray"], linestyle="--", linewidth=0.85, zorder=1)
    ax.set_xscale("log")

    # Tight x-axis
    all_hi = matrix["high"].astype(float)
    all_lo = matrix["low"].astype(float)
    x_right = all_hi.max() * 2.0
    x_left = min(all_lo.min() * 0.85, 0.88)
    ax.set_xlim(x_left, x_right)
    tick_candidates = [0.75, 1.0, 1.5, 2.0, 2.5, 3.0]
    nice_ticks = [t for t in tick_candidates if x_left * 0.9 <= t <= x_right * 0.7]
    ax.set_xticks(nice_ticks)
    ax.set_xticklabels([f"{t:g}" for t in nice_ticks])
    ax.xaxis.get_offset_text().set_visible(False)
    ax.tick_params(axis="x", which="minor", bottom=False, labelbottom=False)

    ax.set_yticks(y)
    ax.set_yticklabels(matrix["check"], fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("Effect estimate (log scale)")
    ax.xaxis.grid(color=COLORS["light_gray"], linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.set_ylim(len(matrix) - 0.5, -0.6)

    # Legend for effect type
    for etype, col in type_colors.items():
        if etype in matrix["type"].values:
            ax.plot([], [], color=col, linewidth=2, label=etype)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.58, -0.12),
              ncol=3, fontsize=6.5, handlelength=1.8, columnspacing=1.0)

    save_figure(fig, "Figure5_child_level_robustness")


def main() -> int:
    configure_style()
    make_figure1()
    make_figure2()
    make_figure3()
    make_figure4()
    make_figure5()
    print("Wrote redesigned publication Figure1 through Figure5 outputs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
