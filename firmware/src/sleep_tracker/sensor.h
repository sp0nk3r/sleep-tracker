#pragma once

struct SensorData {
  float ax, ay, az;   // g        (±2g range, 16384 LSB/g)
  float gx, gy, gz;   // rad/s   (±500°/s range, 65.5 LSB/°/s)
  float temp;          // °C
};

// Reads one full sample directly from MPU6050 registers.
// Call after mpu.begin() / mpu.setRange() have already run.
void readSensor(SensorData& out);
