/*
  Logitech G25 Shifter (NO SPAM VERSION)

  - Reads 16-bit shift register
  - Gear detection via X/Y
  - Reverse = 6th gear + button bit
  - LED flicker on change
  - ONLY sends serial on state change (IMPORTANT FIX)
*/

#define POWER_LED 4

#define LATCH_PIN 5
#define CLOCK_PIN 6
#define DATA_PIN 7

#define X_AXIS A0
#define Y_AXIS A2

#define DEADZONE 80
#define REVERSE_BUTTON (1 << 14)

// ---------------- STATE ----------------

int OFFSET_X = 0;
int OFFSET_Y = 0;

String lastGear = "N";
uint16_t lastButtons = 0;

unsigned long flashTime = 0;

String lastSentGear = "";
uint16_t lastSentButtons = 0;
int lastSentX = 0;
int lastSentY = 0;

// ---------------- READ 16 BITS ----------------

uint16_t readButtonsRaw16() {

  uint16_t data = 0;

  digitalWrite(LATCH_PIN, LOW);
  delayMicroseconds(5);
  digitalWrite(LATCH_PIN, HIGH);
  delayMicroseconds(5);

  for (int i = 0; i < 16; i++) {

    data <<= 1;

    digitalWrite(CLOCK_PIN, LOW);
    delayMicroseconds(5);

    data |= digitalRead(DATA_PIN);

    digitalWrite(CLOCK_PIN, HIGH);
    delayMicroseconds(5);
  }

  return data;
}

// ---------------- ANALOG ----------------

int readCentered(int pin) {
  return analogRead(pin) - 512;
}

// ---------------- GEAR LOGIC ----------------

String getGear(int x, int y, uint16_t buttons) {

  x += OFFSET_X;
  y = -y + OFFSET_Y;

  bool reversePressed = (buttons & REVERSE_BUTTON);

  if (abs(x) < DEADZONE && abs(y) < DEADZONE) return "N";

  if (x < -DEADZONE) {
    if (y < -DEADZONE) return "1";
    if (y > DEADZONE) return "2";
    return "N";
  }

  if (abs(x) <= DEADZONE) {
    if (y < -DEADZONE) return "3";
    if (y > DEADZONE) return "4";
    return "N";
  }

  if (x > DEADZONE) {
    if (y < -DEADZONE) return "5";

    if (y > DEADZONE) {
      if (reversePressed) return "R";
      return "6";
    }

    return "N";
  }

  return "N";
}

// ---------------- SETUP ----------------

void setup() {

  Serial.begin(250000);

  pinMode(LATCH_PIN, OUTPUT);
  pinMode(CLOCK_PIN, OUTPUT);
  pinMode(DATA_PIN, INPUT);

  pinMode(POWER_LED, OUTPUT);

  digitalWrite(LATCH_PIN, HIGH);
  digitalWrite(CLOCK_PIN, HIGH);

  digitalWrite(POWER_LED, LOW);

  Serial.println("G25 NO-SPAM READY");
}

// ---------------- LOOP ----------------

void loop() {

  int x = readCentered(X_AXIS);
  int y = readCentered(Y_AXIS);
  uint16_t buttons = readButtonsRaw16();

  String gear = getGear(x, y, buttons);

  // ---------------- CHANGE DETECTION ----------------

  bool changed = (gear != lastGear) || (buttons != lastButtons);

  // LED flicker logic still works
  if (changed) {
    flashTime = millis();
    lastGear = gear;
    lastButtons = buttons;
  }

  if (millis() - flashTime < 80) {
    digitalWrite(POWER_LED, HIGH);
  } else {
    digitalWrite(POWER_LED, LOW);
  }

  // ---------------- ONLY SEND SERIAL ON CHANGE ----------------

  if (changed) {

    Serial.print("G,");
    Serial.print(gear);
    Serial.print(",");
    Serial.print(x);
    Serial.print(",");
    Serial.print(y);
    Serial.print(",");

    for (int i = 15; i >= 0; i--) {
      Serial.print(bitRead(buttons, i));
    }

    Serial.println();

    // OPTIONAL DEBUG PRINT (ONLY WHEN SENDING)
    // Serial.println("SENT");
  }

  delay(50);
}

