from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

from .models import DesignResult


def section_figure(result: DesignResult):
    data = result.inputs
    h = result.selected_height_cm
    hf = data.topping_cm
    pitch = data.rib_spacing_cm
    bw = data.rib_width_cm
    bays = 3
    width = bays * pitch
    critical_positive = max((item for item in result.flexure if item.kind == "Positivo"), key=lambda item: item.mu_tfm)
    bar_count = int(critical_positive.bar_label.split()[0])
    bar_radius = critical_positive.bar_diameter_mm / 20.0

    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.add_patch(Rectangle((0, h - hf), width, hf, facecolor="#aeb7c2", edgecolor="#27364a", linewidth=1.4))
    for index in range(bays):
        center = pitch * (index + 0.5)
        x_rib = center - bw / 2
        ax.add_patch(Rectangle((x_rib, 0), bw, h - hf, facecolor="#aeb7c2", edgecolor="#27364a", linewidth=1.2))
        if index < bays - 1:
            x_block = center + bw / 2
            block_width = pitch - bw
            ax.add_patch(Rectangle((x_block, 1.0), block_width, h - hf - 1.0, facecolor="#f3a33a", edgecolor="#8d5415", linewidth=1.0))
        offsets = [0.0] if bar_count == 1 else [-(bar_radius + 0.25), bar_radius + 0.25]
        for offset in offsets:
            ax.add_patch(Circle((center + offset, data.cover_cm + bar_radius), bar_radius, facecolor="#2878b5", edgecolor="white", linewidth=0.8))

    temp_step = max(result.temperature_spacing_cm, 5.0)
    x = temp_step / 2.0
    while x < width:
        ax.add_patch(Circle((x, h - data.cover_cm), 0.32, facecolor="#cc3b3b", edgecolor="white", linewidth=0.5))
        x += temp_step

    ax.annotate("", xy=(0, -3.0), xytext=(pitch, -3.0), arrowprops=dict(arrowstyle="<->", color="#27364a"))
    ax.text(pitch / 2, -4.5, f"s = {pitch:.0f} cm", ha="center", fontsize=9)
    ax.annotate("", xy=(-4.0, 0), xytext=(-4.0, h), arrowprops=dict(arrowstyle="<->", color="#27364a"))
    ax.text(-6.0, h / 2, f"h = {h:.0f} cm", rotation=90, va="center", fontsize=9)
    ax.text(width * 0.03, h + 2.2, f"Losa superior: {hf:.0f} cm", fontsize=9)
    ax.text(width * 0.55, h + 2.2, f"Acero de temperatura: {result.temperature_bar_label} @ {result.temperature_spacing_cm:.0f} cm", fontsize=9)
    ax.text(width * 0.03, -7.0, f"Acero principal mostrado: {critical_positive.bar_label}. Esquema parametrizado.", fontsize=8, color="#506070")
    ax.set_xlim(-9, width + 2)
    ax.set_ylim(-9, h + 5)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.tight_layout()
    return fig
