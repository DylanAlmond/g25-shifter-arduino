/*
  Logitech G25 Shifter

  - Reads 16-bit shift register
  - Sends raw X/Y and 16-bit button state on change
*/

#define POWER_LED 4

#define LATCH_PIN 5
#define CLOCK_PIN 6
#define DATA_PIN 7

#define X_AXIS A0
#define Y_AXIS A2

// ---------------- STATE ----------------

unsigned long flashTime = 0;

uint16_t lastSentButtons = 0;
int lastSentX = 0;
int lastSentY = 0;

// ---------------- READ 16 BITS ----------------

uint16_t readButtonsRaw16()
{

  uint16_t data = 0;

  digitalWrite(LATCH_PIN, LOW);
  delayMicroseconds(5);
  digitalWrite(LATCH_PIN, HIGH);
  delayMicroseconds(5);

  for (int i = 0; i < 16; i++)
  {

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

int readCentered(int pin)
{
  return analogRead(pin) - 512;
}

// Arduino no longer computes gear; driver handles gear detection/calibration.

// ---------------- SETUP ----------------

void setup()
{

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

void loop()
{

  int x = readCentered(X_AXIS);
  int y = readCentered(Y_AXIS);
  uint16_t buttons = readButtonsRaw16();

  // Send raw data whenever X, Y, or buttons change. Python driver handles gear logic.
  bool changed = (x != lastSentX) || (y != lastSentY) || (buttons != lastSentButtons);

  if (changed)
  {
    flashTime = millis();
    lastSentX = x;
    lastSentY = y;
    lastSentButtons = buttons;

    // Header 'R' for raw
    Serial.print("R,");
    Serial.print(x);
    Serial.print(",");
    Serial.print(y);
    Serial.print(",");

    for (int i = 15; i >= 0; i--)
    {
      Serial.print(bitRead(buttons, i));
    }

    Serial.println();
  }

  delay(50);
}
