"""
Connects to the ESP32 WebSocket, streams sensor data, and writes to CSV.
Run:  python log_data.py
Stop: Ctrl+C  — file is saved automatically on exit.

Install dep: pip install websockets
"""

import asyncio
import csv
import json
import os
from datetime import datetime

import websockets

WS_URL   = "ws://sleep-tracker.local:81"   # or swap to ws://192.168.x.x:81
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

COLUMNS = ["ts_ms", "datetime", "ax", "ay", "az", "gx", "gy", "gz", "smv", "temp"]

row_count = 0


def new_csv_path():
    os.makedirs(DATA_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return os.path.join(DATA_DIR, f"session_{stamp}.csv")


async def log(url: str, path: str):
    global row_count
    print(f"Connecting to {url} ...")

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()

        try:
            async with websockets.connect(url, ping_interval=None) as ws:
                print(f"Connected. Logging to {os.path.basename(path)}")
                print("Press Ctrl+C to stop.\n")

                async for raw in ws:
                    try:
                        d = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    writer.writerow({
                        "ts_ms":    d.get("ts", 0),
                        "datetime": datetime.now().isoformat(timespec="milliseconds"),
                        "ax":       round(d.get("ax",   0), 4),
                        "ay":       round(d.get("ay",   0), 4),
                        "az":       round(d.get("az",   0), 4),
                        "gx":       round(d.get("gx",   0), 5),
                        "gy":       round(d.get("gy",   0), 5),
                        "gz":       round(d.get("gz",   0), 5),
                        "smv":      round(d.get("smv",  0), 4),
                        "temp":     round(d.get("temp", 0), 2),
                    })
                    f.flush()
                    row_count += 1

                    if row_count % 50 == 0:
                        print(f"  {row_count} rows  |  SMV: {d.get('smv', 0):.3f}", end="\r")

        except asyncio.CancelledError:
            pass  # clean Ctrl+C shutdown
        except websockets.ConnectionClosed:
            print("\nConnection closed by device.")
        except OSError as e:
            print(f"\nCould not connect: {e}")
            print("Check WS_URL at the top of this script.")


def main():
    path = new_csv_path()

    try:
        asyncio.run(log(WS_URL, path))
    except KeyboardInterrupt:
        pass

    print(f"\nStopped.")

    if row_count > 0:
        size = os.path.getsize(path) / 1024
        print(f"Saved {row_count} rows ({size:.1f} KB) → {path}")
    else:
        try:
            os.remove(path)
        except OSError:
            pass
        print("No data recorded — file not saved.")


if __name__ == "__main__":
    main()
