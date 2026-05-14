"""
Plots a recorded session CSV.
Run:  python plot_data.py                    # plots most recent session
      python plot_data.py data/session_X.csv # plots specific file

Install deps: pip install pandas matplotlib
"""

import os
import sys

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

DATA_DIR      = os.path.join(os.path.dirname(__file__), "..", "data")
SMV_STILL     = 0.92   # g    — from baseline (still = 0.88g)
VAR_THRESHOLD = 0.0005 # g²   — from baseline (still variance ≈ 0)
WINDOW        = 150    # samples — 3s rolling window at 50Hz
SUSTAIN       = 1500   # samples — 30s sustained before classifying as sleep
SAMPLE_HZ     = 50


def latest_csv():
    files = sorted(
        [f for f in os.listdir(DATA_DIR) if f.endswith(".csv")],
        reverse=True
    )
    if not files:
        sys.exit(f"No CSV files found in {DATA_DIR}")
    return os.path.join(DATA_DIR, files[0])


def load(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["t"]       = (df["ts_ms"] - df["ts_ms"].iloc[0]) / 1000.0
    df["smv_var"] = df["smv"].rolling(WINDOW, min_periods=1).var()

    df["both_still"] = (df["smv"] < SMV_STILL) & (df["smv_var"] < VAR_THRESHOLD)

    df["asleep"] = (
        df["both_still"].astype(float)
                        .rolling(SUSTAIN, min_periods=SUSTAIN)
                        .min()
                        .fillna(0)
                        .astype(bool)
    )
    return df


def summarize(df: pd.DataFrame) -> dict:
    total_samples  = len(df)
    session_dur_s  = df["t"].iloc[-1]
    sample_dur_s   = 1.0 / SAMPLE_HZ

    # Total sleep time
    sleep_samples  = df["asleep"].sum()
    total_sleep_s  = sleep_samples * sample_dur_s

    # Sleep efficiency = sleep time / total session time
    efficiency_pct = (total_sleep_s / session_dur_s) * 100 if session_dur_s > 0 else 0

    # Wake events = transitions from asleep → awake
    transitions    = df["asleep"].astype(int).diff()
    wake_events    = int((transitions == -1).sum())

    # Longest continuous sleep period
    df["run_id"]   = (df["asleep"] != df["asleep"].shift()).cumsum()
    sleep_runs     = df[df["asleep"]].groupby("run_id").size()
    longest_s      = (sleep_runs.max() * sample_dur_s) if len(sleep_runs) > 0 else 0

    return {
        "session_dur_s":  session_dur_s,
        "total_sleep_s":  total_sleep_s,
        "wake_events":    wake_events,
        "longest_sleep_s": longest_s,
        "efficiency_pct": efficiency_pct,
    }


def fmt_duration(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}h {m:02d}m"
    return f"{m}m {s:02d}s"


def print_summary(stats: dict):
    print()
    print("  ┌─────────────────────────────────────┐")
    print("  │         SLEEP SESSION SUMMARY        │")
    print("  ├─────────────────────────────────────┤")
    print(f"  │  Session duration   {fmt_duration(stats['session_dur_s']):>16s}  │")
    print(f"  │  Total sleep time   {fmt_duration(stats['total_sleep_s']):>16s}  │")
    print(f"  │  Wake events        {stats['wake_events']:>16d}  │")
    print(f"  │  Longest sleep run  {fmt_duration(stats['longest_sleep_s']):>16s}  │")
    print(f"  │  Sleep efficiency   {stats['efficiency_pct']:>15.1f}%  │")
    print("  └─────────────────────────────────────┘")
    print()


def plot(df: pd.DataFrame, title: str, path: str, stats: dict):
    dark   = "#0b0b0e"
    surf   = "#111115"
    surf2  = "#17171d"
    border = "#1f1f28"
    amber  = "#f59e0b"
    green  = "#22c55e"
    muted  = "#6b6b82"
    text   = "#e8e8f0"
    red    = "#ef4444"
    blue   = "#60a5fa"
    purple = "#a78bfa"

    plt.rcParams.update({
        "figure.facecolor":  dark,
        "axes.facecolor":    surf,
        "axes.edgecolor":    border,
        "axes.labelcolor":   muted,
        "xtick.color":       muted,
        "ytick.color":       muted,
        "text.color":        text,
        "grid.color":        border,
        "grid.linewidth":    0.6,
        "font.family":       "monospace",
        "font.size":         9,
        "axes.titlesize":    10,
        "axes.titlecolor":   text,
        "axes.titleweight":  "bold",
        "legend.facecolor":  surf,
        "legend.edgecolor":  border,
        "legend.fontsize":   8,
    })

    # Extra height for the summary block at top
    fig = plt.figure(figsize=(14, 15), facecolor=dark)
    fig.suptitle(title, color=text, fontsize=11, fontweight="bold", y=0.995)

    # Summary block occupies top row; 6 data panels below
    gs = GridSpec(7, 1, figure=fig, hspace=0.55,
                  left=0.07, right=0.97, top=0.97, bottom=0.04,
                  height_ratios=[0.7, 1, 1, 1, 1, 1, 1])

    # ── Summary Stats Panel ────────────────────────────────────
    ax_s = fig.add_subplot(gs[0])
    ax_s.set_facecolor(surf2)
    ax_s.set_xlim(0, 1)
    ax_s.set_ylim(0, 1)
    ax_s.axis("off")

    cells = [
        ("SESSION",              fmt_duration(stats["session_dur_s"])),
        ("SLEEP TIME",           fmt_duration(stats["total_sleep_s"])),
        ("WAKE EVENTS",          str(stats["wake_events"])),
        ("LONGEST SLEEP",        fmt_duration(stats["longest_sleep_s"])),
        ("SLEEP EFFICIENCY",     f"{stats['efficiency_pct']:.1f}%"),
    ]

    n = len(cells)
    for i, (label, value) in enumerate(cells):
        x = (i + 0.5) / n
        # vertical dividers
        if i > 0:
            ax_s.axvline(i / n, color=border, lw=1)
        ax_s.text(x, 0.72, label, ha="center", va="center",
                  color=muted, fontsize=8, fontweight="bold",
                  fontfamily="monospace")

        # colour-code efficiency
        val_color = text
        if label == "SLEEP EFFICIENCY":
            pct = stats["efficiency_pct"]
            val_color = green if pct >= 85 else amber if pct >= 70 else red
        elif label == "WAKE EVENTS":
            val_color = green if stats["wake_events"] <= 3 else amber

        ax_s.text(x, 0.28, value, ha="center", va="center",
                  color=val_color, fontsize=16, fontweight="bold",
                  fontfamily="monospace")

    t = df["t"]

    # ── Accelerometer ──────────────────────────────────────────
    ax0 = fig.add_subplot(gs[1])
    ax0.plot(t, df["ax"], color=red,   lw=0.6, label="X")
    ax0.plot(t, df["ay"], color=green, lw=0.6, label="Y")
    ax0.plot(t, df["az"], color=blue,  lw=0.6, label="Z")
    ax0.set_title("Accelerometer  (g)")
    ax0.set_ylabel("g", color=muted)
    ax0.legend(loc="upper right", ncol=3)
    ax0.grid(True)
    ax0.tick_params(labelbottom=False)

    # ── Gyroscope ──────────────────────────────────────────────
    ax1 = fig.add_subplot(gs[2])
    ax1.plot(t, df["gx"], color=red,   lw=0.6, label="X")
    ax1.plot(t, df["gy"], color=green, lw=0.6, label="Y")
    ax1.plot(t, df["gz"], color=blue,  lw=0.6, label="Z")
    ax1.set_title("Gyroscope  (rad/s)")
    ax1.set_ylabel("rad/s", color=muted)
    ax1.legend(loc="upper right", ncol=3)
    ax1.grid(True)
    ax1.tick_params(labelbottom=False)

    # ── SMV ────────────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[3])
    ax2.plot(t, df["smv"], color=amber, lw=0.8, label="SMV")
    ax2.axhline(SMV_STILL, color=green, lw=0.8, ls="--",
                label=f"Threshold ({SMV_STILL} g)")
    ax2.fill_between(t, df["smv"].min(), df["smv"],
                     where=df["smv"] > SMV_STILL, alpha=0.12, color=amber)
    ax2.set_title("Signal Magnitude Vector  (g)")
    ax2.set_ylabel("g", color=muted)
    ax2.legend(loc="upper right", ncol=2)
    ax2.grid(True)
    ax2.tick_params(labelbottom=False)

    # ── SMV Rolling Variance ────────────────────────────────────
    ax3 = fig.add_subplot(gs[4])
    ax3.plot(t, df["smv_var"], color=purple, lw=0.8,
             label=f"Variance (w={WINDOW} samples)")
    ax3.axhline(VAR_THRESHOLD, color=green, lw=0.8, ls="--",
                label=f"Threshold ({VAR_THRESHOLD})")
    ax3.fill_between(t, 0, df["smv_var"],
                     where=df["smv_var"] > VAR_THRESHOLD, alpha=0.15, color=purple)
    ax3.set_title(f"SMV Rolling Variance  ({WINDOW/SAMPLE_HZ:.0f}s window)")
    ax3.set_ylabel("var(g²)", color=muted)
    ax3.legend(loc="upper right", ncol=2)
    ax3.grid(True)
    ax3.tick_params(labelbottom=False)

    # ── Sleep State ────────────────────────────────────────────
    ax4 = fig.add_subplot(gs[5])
    sleep_float = df["asleep"].astype(float)
    ax4.fill_between(t, 0, sleep_float,       color=green, alpha=0.4, label="ASLEEP")
    ax4.fill_between(t, 0, 1 - sleep_float,   color=amber, alpha=0.15, label="AWAKE")
    ax4.plot(t, sleep_float, color=green, lw=0.6)
    ax4.set_title(
        f"Sleep State  (SMV < {SMV_STILL}g AND var < {VAR_THRESHOLD}, "
        f"sustained {SUSTAIN/SAMPLE_HZ:.0f}s)"
    )
    ax4.set_ylabel("State", color=muted)
    ax4.set_ylim(-0.05, 1.15)
    ax4.set_yticks([0, 1])
    ax4.set_yticklabels(["AWAKE", "SLEEP"])
    ax4.legend(loc="upper right", ncol=2)
    ax4.grid(True, axis="x")
    ax4.tick_params(labelbottom=False)

    # ── Temperature ────────────────────────────────────────────
    ax5 = fig.add_subplot(gs[6])
    ax5.plot(t, df["temp"], color="#f87171", lw=0.8, label="Temp")
    ax5.set_title("Temperature  (°C)")
    ax5.set_ylabel("°C", color=muted)
    ax5.set_xlabel("Time (s)", color=muted)
    ax5.legend(loc="upper right")
    ax5.grid(True)

    out_path = os.path.splitext(path)[0] + ".png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=dark)
    print(f"Saved plot → {out_path}")

    plt.show()


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else latest_csv()
    print(f"Plotting {os.path.basename(path)} ...")
    df = load(path)
    stats = summarize(df)
    print_summary(stats)
    plot(df, os.path.basename(path), path, stats)


if __name__ == "__main__":
    main()
