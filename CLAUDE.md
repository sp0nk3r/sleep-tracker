# Sleep Tracker — CLAUDE.md

## Project Overview
Wrist-worn sleep tracker using an ESP32 DevKit V1 and MPU-6050 IMU. Detects sleep/wake states via motion analysis (Signal Magnitude Vector + rolling variance). Portfolio project demonstrating embedded systems, sensor integration, and signal processing.

## Hardware
- **MCU:** ESP32 DevKit V1
- **IMU:** MPU-6050 (I2C: SDA → GPIO 21, SCL → GPIO 22, address 0x68)
- **LCD address:** 0x3F (wired later)
- **Power:** USB during dev → LiPo + TP4056 later
- **Sensor config:** ±2g range, DLPF 5Hz bandwidth, gyro ±500°/s

## Sensor Units — All values are in g (not m/s²)
Raw int16 values are read directly from MPU-6050 registers in `sensor.cpp`.
The Adafruit library is used for init/config only — its `getEvent()` is NOT used for reads.

| Signal | Sensitivity constant | Unit |
|---|---|---|
| Accelerometer | 16384 LSB/g | g |
| Gyroscope | 65.5 LSB/°/s → converted to rad/s | rad/s |
| Temperature | raw/340.0 + 36.53 | °C |

SMV is computed in g: `sqrt(ax² + ay² + az²)` — still ≈ 1.0g (gravity only).

## Established Thresholds (from baseline recording — device flat on desk, 5 min)
- **Baseline SMV:** ~0.88g (still, no movement)
- **SMV threshold:** 0.92g — above this = movement candidate
- **Variance threshold:** 0.0005 g² — rolling 3s window (150 samples at 50Hz)
- **Sleep classification:** SMV < 0.92g AND variance < 0.0005 sustained for 30 seconds (1500 samples)

## Folder Structure
```
sleep-tracker/
├── firmware/
│   └── src/
│       └── sleep_tracker/
│           ├── sleep_tracker.ino   # main sketch — WiFi, WebSocket, sensor loop
│           ├── sensor.h            # SensorData struct + readSensor() declaration
│           ├── sensor.cpp          # raw I2C burst-read, applies 16384 LSB/g
│           └── credentials.h       # WiFi SSID/pass, API keys — git-ignored
├── data/                           # CSV session logs (session_YYYY-MM-DD_HH-MM-SS.csv)
├── analysis/
│   ├── log_data.py                 # WebSocket logger → CSV
│   └── plot_data.py                # 6-panel matplotlib plot incl. sleep state
├── docs/                           # Schematics, block diagrams, write-ups
├── index.html                      # Live 3D dashboard (Three.js, open in Chrome)
└── CLAUDE.md
```

## Firmware Architecture
- **Transport:** WiFi + WebSocket server on port 81
- **mDNS:** `sleep-tracker.local` (fallback: print IP to serial at 115200 baud)
- **Sample rate:** 50Hz (`delay(20)` in loop, non-blocking with `millis()`)
- **JSON payload:** `{ax, ay, az, gx, gy, gz, smv, temp, ts}`
- **DEBUG flag:** `#define DEBUG 1` — set to 0 to silence serial for power testing
- **Credentials:** `#define WIFI_SSID / WIFI_PASS` in `credentials.h` (never commit)

## Python Logging Setup
```
pip install websockets pandas matplotlib
```

| Script | Command | What it does |
|---|---|---|
| `log_data.py` | `python analysis/log_data.py` | Streams WebSocket → CSV in `data/`, Ctrl+C to save |
| `plot_data.py` | `python analysis/plot_data.py` | Plots most recent CSV; pass path for specific file |

CSV columns: `ts_ms, datetime, ax, ay, az, gx, gy, gz, smv, temp`

Plot panels (6): Accelerometer (g) · Gyroscope (rad/s) · SMV · Rolling Variance · Sleep State · Temperature

Key constants to tune in `plot_data.py`:
```python
SMV_STILL     = 0.92    # g
VAR_THRESHOLD = 0.0005  # g²
WINDOW        = 150     # samples (3s at 50Hz)
SUSTAIN       = 1500    # samples (30s at 50Hz)
```

## Live Dashboard (index.html)
Open directly in Chrome — no build step. Enter ESP32 IP in URL bar and hit Connect.
- 3D box rotates via complementary filter (pitch/roll corrected, yaw integrates gyro)
- State badge: MOVING → STILL → ASLEEP (after 30s sustained)
- SMV chart range: 0.8–1.4g

## Phase Progress
- [x] Wire MPU-6050 to ESP32
- [x] Confirm I2C address 0x68
- [x] Read raw sensor data
- [x] WiFi + WebSocket streaming at 50Hz
- [x] Live 3D dashboard
- [x] CSV logger
- [x] matplotlib plotter
- [x] Fix sensitivity bug (16384 LSB/g in sensor.cpp)
- [x] Establish baseline — SMV 0.88g, variance ≈ 0
- [x] Set sleep/wake thresholds from real data
- [ ] Wear overnight, log full session
- [ ] Validate against phone sleep app
- [ ] Tune thresholds from overnight data

## Phase 2 — Next
- Sleep/wake classifier on full overnight session
- Accuracy analysis vs. reference device
- Document current draw

## Development Notes
- Always power MPU-6050 from 3.3V, not 5V
- Add `credentials.h` to `.gitignore` before pushing to GitHub
- Document current draw measurements (good portfolio detail)
- IoT Bridge (192.168.0.147:5000) and DeskHub (192.168.0.150:8080) defined in credentials.h — not yet wired into firmware

## Key Resources
- MPU-6050 Register Map: https://cdn.sparkfun.com/datasheets/Sensors/Accelerometers/RM-MPU-6000A.pdf
- RandomNerdTutorials ESP32 + MPU-6050 guide
- DigiKey YouTube — Embedded Systems series
