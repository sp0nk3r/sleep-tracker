#include "sensor.h"
#include <Wire.h>
#include <math.h>

#define MPU_ADDR     0x68
#define ACCEL_XOUT_H 0x3B   // first of 14 consecutive data registers

// ±2g range  → 16384 LSB/g  (MPU-6050 register map, section 6.2)
#define ACCEL_LSB_PER_G    16384.0f

// ±500°/s range → 65.5 LSB/(°/s) → convert to LSB/(rad/s)
#define GYRO_LSB_PER_RADS  (65.5f * (180.0f / M_PI))

// MPU-6050 datasheet temperature formula (section 4.6.1)
// TEMP_degC = raw / 340.0 + 36.53
#define TEMP_SCALE  340.0f
#define TEMP_OFFSET 36.53f

void readSensor(SensorData& out) {
  // Burst-read all 14 data bytes in one I2C transaction:
  // ACCEL_X[H,L]  ACCEL_Y[H,L]  ACCEL_Z[H,L]
  // TEMP[H,L]
  // GYRO_X[H,L]   GYRO_Y[H,L]   GYRO_Z[H,L]
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(ACCEL_XOUT_H);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, (uint8_t)14);

  int16_t raw_ax = (int16_t)((Wire.read() << 8) | Wire.read());
  int16_t raw_ay = (int16_t)((Wire.read() << 8) | Wire.read());
  int16_t raw_az = (int16_t)((Wire.read() << 8) | Wire.read());
  int16_t raw_t  = (int16_t)((Wire.read() << 8) | Wire.read());
  int16_t raw_gx = (int16_t)((Wire.read() << 8) | Wire.read());
  int16_t raw_gy = (int16_t)((Wire.read() << 8) | Wire.read());
  int16_t raw_gz = (int16_t)((Wire.read() << 8) | Wire.read());

  out.ax   = raw_ax / ACCEL_LSB_PER_G;
  out.ay   = raw_ay / ACCEL_LSB_PER_G;
  out.az   = raw_az / ACCEL_LSB_PER_G;
  out.gx   = raw_gx / GYRO_LSB_PER_RADS;
  out.gy   = raw_gy / GYRO_LSB_PER_RADS;
  out.gz   = raw_gz / GYRO_LSB_PER_RADS;
  out.temp = raw_t  / TEMP_SCALE + TEMP_OFFSET;
}
