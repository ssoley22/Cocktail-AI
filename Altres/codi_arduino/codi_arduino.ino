#include <Servo.h>
#include <SPI.h>
#include <MFRC522.h>
/*
  Ordres:
  HOME
  A1 [temps_ms]
  A2 [temps_ms]
  A3 [temps_ms]
  A4 [temps_ms]
  A5 [temps_ms]
  A6 [temps_ms]
  ICE [temps_ms]
  PAY

  Respostes:
  HOME OK
  OK
  ICE OK
  ERR
  PAY OK
*/

// ---------- PINS ----------
const byte DIR_PIN = 2;        // DIR del driver stepper
const byte STEP_PIN = 3;       // STEP del driver stepper
const byte LIMIT_PIN = 4;      // Final de carrera
const byte SERVO_PIN = 9;      // Senyal del servo
const byte RFID_RST_PIN = 5;   // Reset del lector RFID
const byte RFID_SS_PIN = 10;   // SDA/SS del lector RFID

// ---------- STEPPER ----------
const bool DIR_POSITIVE = HIGH;        // Direcció positiva; canviar a LOW si va al revés
const bool DIR_HOME = !DIR_POSITIVE;   // Direcció cap al final de carrera
const bool DIR_RELEASE = DIR_POSITIVE; // Direcció per sortir del final de carrera

const int STEP_DELAY_US = 700;   // Velocitat del stepper; menys valor = més ràpid
const int START_DELAY_US = 2200; // Velocitat inicial de la rampa
const int RAMP_STEPS = 200;      // Acceleració/frenada; augmentar per més suavitat

const long LIMIT_RELEASE_STEPS = 100; // Passos per sortir del final de carrera després del HOME
const long MAX_HOME_STEPS = 1000000;  // Màxim de passos buscant HOME abans de donar error

const bool LIMIT_PRESSED_STATE = HIGH; // Final de carrera NC + INPUT_PULLUP: premut = HIGH

// ---------- POSICIONS ----------
const long POS_A[7] = {
  0,      // No usat; permet que A1 sigui índex 1
  2000,   // Ampolla 1
  4200,   // Ampolla 2
  6400,   // Ampolla 3
  8500,   // Ampolla 4
  10600,  // Ampolla 5
  12700   // Ampolla 6
};

const long POS_ICE = 14900; // Dispensador de gel

// ---------- SERVO ----------
const int SERVO_REST = 30;      // Angle segur/repos abans de moure el carro
const int SERVO_PRESS = 80;     // Angle per prémer les ampolles
const int SERVO_HOME = 55;      // Angle després de fer HOME
const int SERVO_ICE = 50;       // Angle per accionar el gel

const int SERVO_UNJAM = 60;       // Angle intermedi per desencallar el dispensador
const int UNJAM_DOWN_MS = 180;    // Temps baixant una mica
const int UNJAM_UP_MS = 180;      // Temps tornant a pressionar curt

const int DEFAULT_PRESS_MS = 3300; // Temps per defecte de dispensació
const int DEFAULT_ICE_MS = 600;    // Temps per defecte de cada pulsació del gel
const int ICE_PAUSE_MS = 250;      // Pausa entre pulsacions del gel
const int MAX_PRESS_MS = 10000;    // Temps màxim permès per seguretat

// ---------- VARIABLES ----------
Servo servo;
long pos = 0;

char cmd[24];
byte idx = 0;

MFRC522 rfid(RFID_SS_PIN, RFID_RST_PIN);

byte UID_USUARI[4] = {0x4D, 0x18, 0xA2, 0x30}; // Targeta autoritzada

const unsigned long PAY_TIMEOUT_MS = 60000; // Temps màxim esperant targeta: 60s

// ---------- SETUP ----------
void setup() {
  pinMode(DIR_PIN, OUTPUT);
  pinMode(STEP_PIN, OUTPUT);
  pinMode(LIMIT_PIN, INPUT_PULLUP);

  digitalWrite(STEP_PIN, LOW);
  digitalWrite(DIR_PIN, DIR_POSITIVE);

  servo.attach(SERVO_PIN);
  servo.write(SERVO_REST);

  Serial.begin(115200);

  SPI.begin();
  rfid.PCD_Init();

  if (home()) {
    Serial.println(F("HOME OK")); // HOME automàtic en arrencar
  } else {
    Serial.println(F("ERR"));
  }
}

// ---------- LOOP ----------
void loop() {
  readSerial();
}

// ---------- SERIAL ----------
void readSerial() {
  while (Serial.available()) {
    char c = Serial.read();

    if (c == '\n' || c == '\r') {
      if (idx > 0) {
        cmd[idx] = '\0';
        processCommand();
        idx = 0;
      }
    } else if (idx < sizeof(cmd) - 1) {
      cmd[idx] = c;
      idx++;
    }
  }
}

// ---------- ORDRES ----------
void processCommand() {
  if (strcmp(cmd, "HOME") == 0) {
    if (home()) {
      Serial.println(F("HOME OK"));
    } else {
      Serial.println(F("ERR"));
    }
    return;
  }

    if (strcmp(cmd, "PAY") == 0) {
      if (waitPayment()) {
        Serial.println(F("PAY OK"));
    } else {
        Serial.println(F("ERR"));
    }
    return;
  }

  if (cmd[0] == 'A' && cmd[1] >= '1' && cmd[1] <= '6') {
    int bottle = cmd[1] - '0';
    int ms = getTime(cmd + 2, DEFAULT_PRESS_MS);

    if (!validTime(ms)) {
      Serial.println(F("ERR"));
      return;
    }

    if (goTo(POS_A[bottle])) {
      pressServo(SERVO_PRESS, ms);
      Serial.println(F("OK"));
    } else {
      Serial.println(F("ERR"));
    }

    return;
  }

  if (cmd[0] == 'I' && cmd[1] == 'C' && cmd[2] == 'E') {
    int ms = getTime(cmd + 3, DEFAULT_ICE_MS);

    if (!validTime(ms)) {
      Serial.println(F("ERR"));
      return;
    }

    if (goTo(POS_ICE)) {
      pressIce(ms);
      Serial.println(F("ICE OK"));
    } else {
      Serial.println(F("ERR"));
    }

    return;
  }

  Serial.println(F("ERR"));
}

// ---------- HOME ----------
bool home() {
  servo.write(SERVO_REST);
  delay(200);

  digitalWrite(DIR_PIN, DIR_HOME);
  delayMicroseconds(20);

  for (long i = 0; i < MAX_HOME_STEPS; i++) {
    if (limitPressed()) {
      releaseLimit();
      pos = 0; // Zero de treball després de sortir 100 passos del final de carrera

      servo.write(SERVO_HOME);
      delay(200);

      return true;
    }

    stepMotor(STEP_DELAY_US);
  }

  return false;
}

void releaseLimit() {
  digitalWrite(DIR_PIN, DIR_RELEASE);
  delayMicroseconds(20);

  for (long i = 0; i < LIMIT_RELEASE_STEPS; i++) {
    stepMotor(STEP_DELAY_US);
  }
}

// ---------- MOVIMENT ----------
bool goTo(long target) {
  long steps = target - pos;
  return moveSteps(steps);
}

bool moveSteps(long steps) {
  if (steps == 0) {
    return true;
  }

  servo.write(SERVO_REST); // Sempre baixa el servo abans de moure el carro
  delay(150);

  bool dir;

  if (steps > 0) {
    dir = DIR_POSITIVE;
  } else {
    dir = !DIR_POSITIVE;
  }

  long total = labs(steps);

  digitalWrite(DIR_PIN, dir);
  delayMicroseconds(20);

  for (long i = 0; i < total; i++) {
    if (dir == DIR_HOME && limitPressed()) {
      releaseLimit();
      pos = 0;
      return false;
    }

    int d = rampDelay(i, total);
    stepMotor(d);

    if (dir == DIR_POSITIVE) {
      pos++;
    } else {
      pos--;
    }
  }

  return true;
}

void stepMotor(int delayUs) {
  digitalWrite(STEP_PIN, HIGH);
  delayMicroseconds(4);
  digitalWrite(STEP_PIN, LOW);
  delayMicroseconds(delayUs);
}

int rampDelay(long i, long total) {
  long r = min(i, total - 1 - i);

  if (r < RAMP_STEPS) {
    return map(r, 0, RAMP_STEPS, START_DELAY_US, STEP_DELAY_US);
  }

  return STEP_DELAY_US;
}

// ---------- SERVO ----------
void pressServo(int angle, int ms) {
  servo.write(angle);
  delay(ms);

  servo.write(SERVO_UNJAM); // Baixa una mica per alliberar tensió
  delay(UNJAM_DOWN_MS);

  servo.write(angle);       // Torna a pressionar curt per desencallar
  delay(UNJAM_UP_MS);

  servo.write(SERVO_REST);  // Baixa del tot
  delay(300);
}

void pressIce(int ms) {
  servo.write(SERVO_ICE);
  delay(ms);

  servo.write(SERVO_REST);
  delay(ICE_PAUSE_MS);

  servo.write(SERVO_ICE);
  delay(ms);

  servo.write(SERVO_REST);
  delay(300);
}

// ---------- RFID / PAGAMENT ----------
bool waitPayment() {
  unsigned long startTime = millis();

  while (millis() - startTime < PAY_TIMEOUT_MS) {
    if (!rfid.PICC_IsNewCardPresent()) {
      delay(50);
      continue;
    }

    if (!rfid.PICC_ReadCardSerial()) {
      delay(50);
      continue;
    }

    bool uidCorrecte = true;

    if (rfid.uid.size != 4) {
      uidCorrecte = false;
    } else {
      for (byte i = 0; i < 4; i++) {
        if (rfid.uid.uidByte[i] != UID_USUARI[i]) {
          uidCorrecte = false;
          break;
        }
      }
    }

    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();

    if (uidCorrecte) {
      return true;
    }

    delay(500); // Evita lectures repetides molt ràpides d'una targeta incorrecta
  }

  return false;
}

// ---------- UTILITATS ----------
bool limitPressed() {
  return digitalRead(LIMIT_PIN) == LIMIT_PRESSED_STATE;
}

int getTime(char *text, int defaultMs) {
  while (*text == ' ') {
    text++;
  }

  if (*text == '\0') {
    return defaultMs;
  }

  return atoi(text);
}

bool validTime(int ms) {
  if (ms > 0 && ms <= MAX_PRESS_MS) {
    return true;
  } else {
    return false;
  }
}
