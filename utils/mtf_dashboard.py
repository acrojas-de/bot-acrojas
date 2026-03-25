import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, Circle, FancyBboxPatch
import math


def _decision_color(mtf_decision):
    if mtf_decision == "ENTER LONG":
        return "#22c55e"
    if mtf_decision == "ENTER SHORT":
        return "#ef4444"
    if mtf_decision == "SCALP":
        return "#f59e0b"
    return "#94a3b8"


def _bias_color(bias):
    if str(bias).lower() == "bullish":
        return "#22c55e"
    if str(bias).lower() == "bearish":
        return "#ef4444"
    return "#94a3b8"


def generate_mtf_dashboard(price, entry_score, mtf_decision,
                           monthly_bias, weekly_bias, trigger):

    max_score = 8
    score = max(0, min(entry_score, max_score))
    decision_color = _decision_color(mtf_decision)

    fig = plt.figure(figsize=(7, 9), dpi=140)
    fig.patch.set_facecolor("#06122b")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 140)
    ax.axis("off")

    # Card principal
    card = FancyBboxPatch(
        (4, 4), 92, 132,
        boxstyle="round,pad=0.8,rounding_size=6",
        linewidth=1.6,
        edgecolor="#1e3a5f",
        facecolor="#08152f"
    )
    ax.add_patch(card)

    # Header
    ax.text(50, 130, "ACROJAS MTF PANEL",
            ha="center", va="center",
            color="white", fontsize=21, fontweight="bold")

    ax.text(50, 121.5, "BTC / USDT",
            ha="center", va="center",
            color="#8fb3d9", fontsize=11)

    ax.text(50, 115.5, f"${price:,.2f}",
            ha="center", va="center",
            color="white", fontsize=25, fontweight="bold")

    # Gauge semicircular
    center_x, center_y = 50, 78
    radius = 28
    width = 7

    zones = [
        (180, 135, "#ef4444"),
        (135, 90, "#f59e0b"),
        (90, 45, "#84cc16"),
        (45, 0, "#22c55e"),
    ]

    for theta1, theta2, color in zones:
        wedge = Wedge(
            (center_x, center_y), radius, theta2, theta1,
            width=width, facecolor=color, edgecolor="none", alpha=0.95
        )
        ax.add_patch(wedge)

    outline = Wedge(
        (center_x, center_y), radius, 0, 180,
        width=width, facecolor="none", edgecolor="#dbeafe", linewidth=2
    )
    ax.add_patch(outline)

    # Marcas principales
    for i in range(max_score + 1):
        frac = i / max_score
        angle = 180 - (180 * frac)
        rad = math.radians(angle)

        r1 = radius - width - 1.5
        r2 = radius + 1.2

        x1 = center_x + r1 * math.cos(rad)
        y1 = center_y + r1 * math.sin(rad)
        x2 = center_x + r2 * math.cos(rad)
        y2 = center_y + r2 * math.sin(rad)

        lw = 1.8 if i in [0, 2, 4, 6, 8] else 1.0
        alpha = 0.9 if i in [0, 2, 4, 6, 8] else 0.45

        ax.plot([x1, x2], [y1, y2], color="#dbeafe", linewidth=lw, alpha=alpha)

    # Números del dial
    for i in [0, 2, 4, 6, 8]:
        frac = i / max_score
        angle = 180 - (180 * frac)
        rad = math.radians(angle)

        label_r = radius + 6
        lx = center_x + label_r * math.cos(rad)
        ly = center_y + label_r * math.sin(rad)

        ax.text(lx, ly, str(i),
                ha="center", va="center",
                color="#dbeafe", fontsize=10, fontweight="bold")

    # Aguja más visible
    needle_angle = 180 - (180 * (score / max_score))
    needle_rad = math.radians(needle_angle)
    needle_len = radius - 3

    nx = center_x + needle_len * math.cos(needle_rad)
    ny = center_y + needle_len * math.sin(needle_rad)

    # Línea base de aguja
    ax.plot([center_x, nx], [center_y, ny],
            color="#38bdf8", linewidth=4.2, solid_capstyle="round")

    # Glow simple
    ax.plot([center_x, nx], [center_y, ny],
            color="#7dd3fc", linewidth=7, alpha=0.15, solid_capstyle="round")

    # Centro
    ax.add_patch(Circle((center_x, center_y), 2.2, color="#38bdf8"))
    ax.add_patch(Circle((center_x, center_y), 1.0, color="#e2e8f0"))

    # Score
    ax.text(50, 60, f"SCORE {score}/{max_score}",
            ha="center", va="center",
            color="white", fontsize=21, fontweight="bold")

    # Barra lineal
    bar_x, bar_y, bar_w, bar_h = 18, 52, 64, 5.8
    bar_bg = FancyBboxPatch(
        (bar_x, bar_y), bar_w, bar_h,
        boxstyle="round,pad=0.25,rounding_size=2.2",
        linewidth=0, facecolor="#13294b"
    )
    ax.add_patch(bar_bg)

    fill_w = bar_w * (score / max_score)
    bar_fill = FancyBboxPatch(
        (bar_x, bar_y), fill_w, bar_h,
        boxstyle="round,pad=0.25,rounding_size=2.2",
        linewidth=0, facecolor=decision_color
    )
    ax.add_patch(bar_fill)

    # Labels
    ax.text(22, 42, "MONTHLY BIAS",
            ha="left", va="center", color="#8fb3d9", fontsize=10, fontweight="bold")
    ax.text(22, 37, str(monthly_bias).upper(),
            ha="left", va="center", color=_bias_color(monthly_bias), fontsize=14, fontweight="bold")

    ax.text(50, 42, "WEEKLY BIAS",
            ha="center", va="center", color="#8fb3d9", fontsize=10, fontweight="bold")
    ax.text(50, 37, str(weekly_bias).upper(),
            ha="center", va="center", color=_bias_color(weekly_bias), fontsize=14, fontweight="bold")

    ax.text(78, 42, "TRIGGER",
            ha="right", va="center", color="#8fb3d9", fontsize=10, fontweight="bold")
    ax.text(78, 37, str(trigger).upper(),
            ha="right", va="center", color="white", fontsize=14, fontweight="bold")

    # Caja decisión
    decision_box = FancyBboxPatch(
        (16, 14), 68, 14,
        boxstyle="round,pad=0.5,rounding_size=4",
        linewidth=1.2, edgecolor=decision_color, facecolor="#0b1c3d"
    )
    ax.add_patch(decision_box)

    ax.text(50, 23, "MTF DECISION",
            ha="center", va="center",
            color="#8fb3d9", fontsize=10, fontweight="bold")
    ax.text(50, 18, mtf_decision,
            ha="center", va="center",
            color=decision_color, fontsize=18, fontweight="bold")

    ax.text(50, 8, "ACROJAS CORE · MTF ENGINE V2",
            ha="center", va="center",
            color="#5f7ea5", fontsize=8)

    path = "mtf_panel.png"
    plt.savefig(path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()

    print("PNG guardado en:", path)
    return path