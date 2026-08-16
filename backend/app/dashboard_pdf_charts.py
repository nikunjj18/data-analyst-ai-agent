import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import os
import tempfile
import uuid

sns.set_theme(style="whitegrid", font_scale=0.9)
COLORS = ["#00A896", "#F5A623", "#FF6B9D", "#4ADE80", "#818CF8", "#FB923C", "#38BDF8", "#F2545B"]


def _fmt(v):
    if abs(v) >= 1_000_000:
        return f"{v/1_000_000:.2f}M"
    if abs(v) >= 1_000:
        return f"{v/1_000:.1f}K"
    if v == int(v):
        return f"{int(v):,}"
    return f"{v:,.1f}"


def render_widget_to_image(widget: dict, out_dir: str) -> str | None:
    """Renders one dashboard widget as a static PNG with visible data labels on every
    element, since a downloaded image has no hover tooltips."""
    wtype = widget.get("type")
    title = widget.get("title", "")
    path = os.path.join(out_dir, f"widget_{uuid.uuid4().hex}.png")

    try:
        if wtype in ("bar", "histogram") and widget.get("data"):
            fig, ax = plt.subplots(figsize=(6.2, 3.4), dpi=140)
            names = [d["name"] for d in widget["data"]]
            values = [d["value"] for d in widget["data"]]
            bars = ax.bar(names, values, color=COLORS[: len(values)])
            for bar, v in zip(bars, values):
                ax.annotate(_fmt(v), (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                            ha="center", va="bottom", fontsize=8, fontweight="bold")
            ax.set_title(title, fontsize=11, fontweight="bold")
            plt.xticks(rotation=30, ha="right", fontsize=8)
            ax.spines[["top", "right"]].set_visible(False)
            ax.margins(y=0.15)
            plt.tight_layout()
            fig.savefig(path, facecolor="white")
            plt.close(fig)
            return path

        if wtype == "table" and widget.get("data"):
            fig, ax = plt.subplots(figsize=(6.2, 3.6), dpi=140)
            data_sorted = sorted(widget["data"], key=lambda d: d["value"], reverse=True)
            names = [d["name"] for d in data_sorted][::-1]
            values = [d["value"] for d in data_sorted][::-1]
            bars = ax.barh(names, values, color=COLORS[: len(values)])
            for bar, v in zip(bars, values):
                ax.annotate(_fmt(v), (bar.get_width(), bar.get_y() + bar.get_height() / 2),
                            ha="left", va="center", fontsize=8, fontweight="bold", xytext=(4, 0), textcoords="offset points")
            ax.set_title(title, fontsize=11, fontweight="bold")
            ax.spines[["top", "right"]].set_visible(False)
            ax.margins(x=0.15)
            plt.tight_layout()
            fig.savefig(path, facecolor="white")
            plt.close(fig)
            return path

        if wtype == "pie" and widget.get("data"):
            fig, ax = plt.subplots(figsize=(5.2, 4.2), dpi=140)
            names = [d["name"] for d in widget["data"]]
            values = [d["value"] for d in widget["data"]]
            labels = [f"{n}\n{_fmt(v)}" for n, v in zip(names, values)]
            ax.pie(values, labels=labels, autopct="%1.0f%%", colors=COLORS[: len(values)],
                   textprops={"fontsize": 7.5}, wedgeprops={"edgecolor": "white"}, pctdistance=0.75)
            ax.set_title(title, fontsize=11, fontweight="bold")
            plt.tight_layout()
            fig.savefig(path, facecolor="white")
            plt.close(fig)
            return path

        if wtype == "line" and widget.get("data"):
            fig, ax = plt.subplots(figsize=(6.5, 3.4), dpi=140)
            periods = [d["period"] for d in widget["data"]]
            values = [d["value"] for d in widget["data"]]
            ax.plot(periods, values, marker="o", color=COLORS[0], linewidth=2, markersize=5)
            for x, y in zip(periods, values):
                ax.annotate(_fmt(y), (x, y), textcoords="offset points", xytext=(0, 8),
                            ha="center", fontsize=7.5, fontweight="bold")
            ax.set_title(title, fontsize=11, fontweight="bold")
            plt.xticks(rotation=30, ha="right", fontsize=8)
            ax.spines[["top", "right"]].set_visible(False)
            ax.margins(y=0.2)
            plt.tight_layout()
            fig.savefig(path, facecolor="white")
            plt.close(fig)
            return path

        if wtype == "scatter" and widget.get("data"):
            fig, ax = plt.subplots(figsize=(5.5, 3.5), dpi=140)
            xs = [d["x"] for d in widget["data"]]
            ys = [d["y"] for d in widget["data"]]
            ax.scatter(xs, ys, color=COLORS[2], alpha=0.6, s=25)
            ax.set_title(title, fontsize=11, fontweight="bold")
            ax.spines[["top", "right"]].set_visible(False)
            plt.tight_layout()
            fig.savefig(path, facecolor="white")
            plt.close(fig)
            return path

        if wtype == "correlation" and widget.get("matrix"):
            fig, ax = plt.subplots(figsize=(5, 4.2), dpi=140)
            sns.heatmap(widget["matrix"], annot=True, fmt=".2f", cmap="YlGnBu",
                        xticklabels=widget["columns"], yticklabels=widget["columns"], ax=ax, cbar=False, annot_kws={"size": 7})
            ax.set_title(title, fontsize=11, fontweight="bold")
            plt.xticks(rotation=30, ha="right", fontsize=7)
            plt.yticks(fontsize=7)
            plt.tight_layout()
            fig.savefig(path, facecolor="white")
            plt.close(fig)
            return path

    except Exception:
        return None

    return None


def render_all_dashboard_charts(dashboard_data: dict) -> list:
    out_dir = os.path.join(tempfile.gettempdir(), "dashboard_pdf_charts")
    os.makedirs(out_dir, exist_ok=True)

    results = []
    for widget in dashboard_data.get("widgets", []):
        if widget.get("type") == "kpi":
            continue
        path = render_widget_to_image(widget, out_dir)
        if path:
            results.append((widget.get("title", ""), path))
    return results