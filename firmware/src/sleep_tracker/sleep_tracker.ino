// Required libraries (install via Arduino Library Manager):
//   - "WebSockets" by Markus Sattler (Links2004/arduinoWebSockets)
//   - "ArduinoJson" by Benoit Blanchon
//   - "Adafruit MPU6050" + "Adafruit Unified Sensor" (already installed)
//   - ESPmDNS is part of the ESP32 Arduino core — no install needed

#include <WiFi.h>
#include <WebSocketsServer.h>
#include <ESPmDNS.h>
#include <ArduinoJson.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>

#include "credentials.h"
#include "sensor.h"

#define DEBUG     1   // 1 = serial output, 0 = silent
#define SAMPLE_HZ 50  // target sample rate
#define WS_PORT   81

#if DEBUG
  #define DPRINT(x)   Serial.print(x)
  #define DPRINTLN(x) Serial.println(x)
#else
  #define DPRINT(x)
  #define DPRINTLN(x)
#endif

Adafruit_MPU6050 mpu;
WebSocketsServer ws(WS_PORT);

void onWsEvent(uint8_t num, WStype_t type, uint8_t* payload, size_t len) {
  if (type == WStype_CONNECTED) {
    IPAddress ip = ws.remoteIP(num);
    DPRINT("[WS] Client connected from "); DPRINTLN(ip.toString());
  } else if (type == WStype_DISCONNECTED) {
    DPRINT("[WS] Client #"); DPRINT(num); DPRINTLN(" disconnected");
  }
}

void setup() {
  Serial.begin(115200);

  if (!mpu.begin()) {
    DPRINTLN("MPU6050 not found — check wiring.");
    while (1) delay(10);
  }
  DPRINTLN("MPU6050 found.");

  mpu.setAccelerometerRange(MPU6050_RANGE_2_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_5_HZ);

  WiFi.begin(WIFI_SSID, WIFI_PASS);
  DPRINT("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    DPRINT(".");
  }
  DPRINT("\nConnected. IP: ");
  DPRINTLN(WiFi.localIP().toString());
  DPRINT("Open: ws://");
  DPRINT(WiFi.localIP().toString());
  DPRINT(":"); DPRINTLN(WS_PORT);

  if (MDNS.begin("sleep-tracker")) {
    DPRINTLN("mDNS: ws://sleep-tracker.local:81");
  }

  ws.begin();
  ws.onEvent(onWsEvent);
  DPRINTLN("WebSocket server ready.");
}

unsigned long lastSample = 0;
const unsigned long interval = 1000 / SAMPLE_HZ;

void loop() {
  ws.loop();

  unsigned long now = millis();
  if (now - lastSample < interval) return;
  lastSample = now;

  SensorData s;
  readSensor(s);

  float smv = sqrt(s.ax*s.ax + s.ay*s.ay + s.az*s.az);

  StaticJsonDocument<192> doc;
  doc["ax"]   = s.ax;
  doc["ay"]   = s.ay;
  doc["az"]   = s.az;
  doc["gx"]   = s.gx;
  doc["gy"]   = s.gy;
  doc["gz"]   = s.gz;
  doc["smv"]  = smv;
  doc["temp"] = s.temp;
  doc["ts"]   = now;

  String json;
  serializeJson(doc, json);
  ws.broadcastTXT(json);

  DPRINTLN(json);
}
