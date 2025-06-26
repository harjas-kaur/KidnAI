#include <math.h>

volatile unsigned long voltageTime = 0;
volatile unsigned long currentTime = 0;

float voltageRMS = 0;
float currentRMS = 0;
float realPower = 0;
float powerFactor = 0;

float voltageOffset = 2.5;
float currentOffset = 2.5;

const int voltageAnalogPin = A0;
const int currentAnalogPin = A1;

const float voltageSensitivity = 0.288;
const float currentSensitivity = 0.0312;  // ✅ Calibrated using actual current
const float voltageACScale = 228.0 / 2.65; // ≈ 86.04

float pfSmoothed = 1.0;
const float pfAlpha = 0.05;

void setup() {
  Serial.begin(9600);
  calibrateVoltageSensor();
  calibrateCurrentSensor();

  attachInterrupt(digitalPinToInterrupt(2), voltageISR, RISING);
  attachInterrupt(digitalPinToInterrupt(3), currentISR, RISING);
}

void loop() {
  voltageRMS = readVoltageRMS(voltageAnalogPin, voltageOffset, voltageSensitivity);
  currentRMS = readCurrentRMS(currentAnalogPin, currentOffset, currentSensitivity);

  if (voltageRMS < 0.5) voltageRMS = 0;
  if (currentRMS < 0.1) currentRMS = 0;

  float actualVoltage = voltageRMS * voltageACScale;

  // Phase + PF
  noInterrupts();
  long deltaT = (long)voltageTime - (long)currentTime;
  interrupts();

  float period_us = 1000000.0 / 50.0;
  float phaseAngle = (2.0 * PI * deltaT) / period_us;
  phaseAngle = fmod(fabs(phaseAngle), 2.0 * PI);
  if (phaseAngle > PI) phaseAngle = 2.0 * PI - phaseAngle;

  float pf = fabs(cos(phaseAngle));
  if (pf > 1.0) pf = 1.0;
  if (pf < 0.95) pf = 0.95;

  pfSmoothed = (1.0 - pfAlpha) * pfSmoothed + pfAlpha * pf;

  realPower = fabs(actualVoltage * currentRMS * pfSmoothed);

  // Output
  Serial.print("ZMPT RMS: ");
  Serial.print(voltageRMS, 3);
  Serial.print(" V, Scaled Voltage: ");
  Serial.print(actualVoltage, 2);
  Serial.print(" V, Current RMS: ");
  Serial.print(currentRMS, 2);
  Serial.print(" A, PF: ");
  Serial.print(pfSmoothed, 3);
  Serial.print(", Real Power: ");
  Serial.print(realPower, 2);
  Serial.println(" W");

  delay(500);
}

// === RMS Functions ===
float readCurrentRMS(int pin, float offset, float sensitivity) {
  float sumSq = 0;
  for (int i = 0; i < 1000; i++) {
    float voltage = (analogRead(pin) / 1023.0) * 5.0;
    float current = (voltage - offset) / sensitivity;
    sumSq += current * current;
    delayMicroseconds(100);
  }
  return sqrt(sumSq / 1000);
}

float readVoltageRMS(int pin, float offset, float sensitivity) {
  float sumSq = 0;
  for (int i = 0; i < 1000; i++) {
    float voltage = ((analogRead(pin) / 1023.0) * 5.0 - offset) / sensitivity;
    sumSq += voltage * voltage;
    delayMicroseconds(100);
  }
  return sqrt(sumSq / 1000);
}

// === Offset Calibration ===
void calibrateCurrentSensor() {
  long sum = 0;
  for (int i = 0; i < 1000; i++) {
    sum += analogRead(currentAnalogPin);
    delay(1);
  }
  currentOffset = (sum / 1000) * (5.0 / 1023.0);
  Serial.print("Current Offset: ");
  Serial.println(currentOffset, 3);
}

void calibrateVoltageSensor() {
  long sum = 0;
  for (int i = 0; i < 1000; i++) {
    sum += analogRead(voltageAnalogPin);
    delay(1);
  }
  voltageOffset = (sum / 1000) * (5.0 / 1023.0);
  Serial.print("Voltage Offset: ");
  Serial.println(voltageOffset, 3);
}

// === Interrupts ===
void voltageISR() {
  voltageTime = micros();
}

void currentISR() {
  currentTime = micros();
}