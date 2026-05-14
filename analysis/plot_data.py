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
from matplotlib.gridspec import GridSpec

DATA_DIR      = os.path.join(os.path.dirname(__file__), "..", "data")
SMV_STILL     = 0.92   # g    — from baseline (still = 0.88g)
VAR_THRESHOLD = 0.0005 # g²   — from baseline (still variance ≈ 0)
WINDOW        = 150    # samples — 3s rolling window at 50Hz
SUSTAIN       = 1500   # samples — 30s sustained before classifying as sleep


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

    # Both conditions must be true simultaneously
    df["both_still"] = (df["smv"] < SMV_STILL) & (df["smv_var"] < VAR_THRESHOLD)

    # Sleep = both_still sustained for at least SUSTAIN consecutive samples.
    # rolling(SUSTAIN).min() == 1.0 only when every sample in the window is True.
    df["asleep"] = (
        df["both_still"].astype(float)
                        .rolling(SUSTAIN, min_periods=SUSTAIN)
                        .min()
                        .fillna(0)
                        .astype(bool)
    )
    return df


def plot(df: pd.DataFrame, title: str, path: str):
    dark   = "#0b0b0e"
    surf   = "#111115"
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

    fig = plt.figure(figsize=(14, 13), facecolor=dark)
    fig.suptitle(title, color=text, fontsize=11, fontweight="bold", y=0.99)

    gs = GridSpec(6, 1, figure=fig, hspace=0.55,
                  left=0.07, right=0.97, top=0.95, bottom=0.05)

    t = df["t"]

    # ── Accelerometer ──────────────────────────────────────────
    ax0 = fig.add_subplot(gs[0])
    ax0.plot(t, df["ax"], color=red,   lw=0.8, label="X")
    ax0.plot(t, df["ay"], color=green, lw=0.8, label="Y")
    ax0.plot(t, df["az"], color=blue,  lw=0.8, label="Z")
    ax0.set_title("Accelerometer  (g)")
    ax0.set_ylabel("g", color=muted)
    ax0.legend(loc="upper right", ncol=3)
    ax0.grid(True)
    ax0.tick_params(labelbottom=False)

    # ── Gyroscope ──────────────────────────────────────────────
    ax1 = fig.add_subplot(gs[1])
    ax1.plot(t, df["gx"], color=red,   lw=0.8, label="X")
    ax1.plot(t, df["gy"], color=green, lw=0.8, label="Y")
    ax1.plot(t, df["gz"], color=blue,  lw=0.8, label="Z")
    ax1.set_title("Gyroscope  (rad/s)")
    ax1.set_ylabel("rad/s", color=muted)
    ax1.legend(loc="upper right", ncol=3)
    ax1.grid(True)
    ax1.tick_params(labelbottom=False)

    # ── SMV ────────────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[2])
    ax2.plot(t, df["smv"], color=amber, lw=1.0, label="SMV")
    ax2.axhline(SMV_STILL, color=green, lw=0.8, ls="--",
                label=f"Still ref ({SMV_STILL} g)")
    ax2.fill_between(t, df["smv"].min(), df["smv"],
                     where=df["smv"] > SMV_STILL, alpha=0.12, color=amber)
    ax2.set_title("Signal Magnitude Vector  (g)")
    ax2.set_ylabel("g", color=muted)
    ax2.legend(loc="upper right", ncol=2)
    ax2.grid(True)
    ax2.tick_params(labelbottom=False)

    # ── SMV Rolling Variance ────────────────────────────────────
    ax3 = fig.add_subplot(gs[3])
    ax3.plot(t, df["smv_var"], color=purple, lw=1.0,
             label=f"Variance (w={WINDOW} samples)")
    ax3.axhline(VAR_THRESHOLD, color=green, lw=0.8, ls="--",
                label=f"Var threshold ({VAR_THRESHOLD})")
    ax3.fill_between(t, 0, df["smv_var"],
                     where=df["smv_var"] > VAR_THRESHOLD, alpha=0.15, color=purple)
    ax3.set_title(f"SMV Rolling Variance  ({WINDOW}-sample window = {WINDOW/50:.0f}s)")
    ax3.set_ylabel("var(g²)", color=muted)
    ax3.legend(loc="upper right", ncol=2)
    ax3.grid(True)
    ax3.tick_params(labelbottom=False)

    # ── Sleep State ────────────────────────────────────────────
    ax4 = fig.add_subplot(gs[4])
    sleep_float = df["asleep"].astype(float)
    ax4.fill_between(t, 0, sleep_float, color=green, alpha=0.4, label="ASLEEP")
    ax4.fill_between(t, 0, 1 - sleep_float, color=amber, alpha=0.15, label="AWAKE")
    ax4.plot(t, sleep_float, color=green, lw=0.6)
    ax4.set_title(f"Sleep State  (SMV < {SMV_STILL}g  AND  var < {VAR_THRESHOLD}  sustained {SUSTAIN/50:.0f}s)")
    ax4.set_ylabel("1=Sleep", color=muted)
    ax4.set_ylim(-0.05, 1.15)
    ax4.set_yticks([0, 1])
    ax4.set_yticklabels(["AWAKE", "SLEEP"])
    ax4.legend(loc="upper right", ncol=2)
    ax4.grid(True, axis="x")
    ax4.tick_params(labelbottom=False)

    # ── Temperature ────────────────────────────────────────────
    ax5 = fig.add_subplot(gs[5])
    ax5.plot(t, df["temp"], color="#f87171", lw=0.8, label="Temp")
    ax5.set_title("Temperature  (°C)")
    ax5.set_ylabel("°C", color=muted)
    ax5.set_xlabel("Time (s)", color=muted)
    ax5.legend(loc="upper right")
    ax5.grid(True)

    # stats
    duration   = t.iloc[-1]
    sleep_pct  = df["asleep"].mean() * 100
    still_pct  = (df["smv_var"] <= VAR_THRESHOLD).mean() * 100
    stats = (
        f"Duration: {duration:.0f}s   "
        f"Samples: {len(df)}   "
        f"Avg SMV: {df['smv'].mean():.4f} g   "
        f"Avg Variance: {df['smv_var'].mean():.5f}   "
        f"Still (var): {still_pct:.1f}%   "
        f"Sleep (sustained): {sleep_pct:.1f}%"
    )
    fig.text(0.5, 0.005, stats, ha="center", color=muted, fontsize=8)

    out_path = os.path.splitext(path)[0] + ".png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=dark)
    print(f"Saved plot → {out_path}")

    plt.show()


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else latest_csv()
    print(f"Plotting {os.path.basename(path)} ...")
    df = load(path)
    print(f"  {len(df)} rows  |  {df['t'].iloc[-1]:.1f}s  |  "
          f"avg SMV: {df['smv'].mean():.4f} g  |  "
          f"avg var: {df['smv_var'].mean():.5f}")
    plot(df, os.path.basename(path), path)


if __name__ == "__main__":
    main()
