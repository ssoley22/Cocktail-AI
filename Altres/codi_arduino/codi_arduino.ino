#include <Servo.h>

/*
  CRISTAL NOCTURNO - CODI BASE AMB FINAL DE CARRERA I POSICIONS REALS

  Connexions:
  - DIR driver stepper  -> Arduino pin 2
  - STEP driver stepper -> Arduino pin 3
  - Final de carrera    -> Arduino pin 4
  - Servo senyal        -> Arduino pin 9

  Final de carrera:
  - Connectat com a NC.
  - C  -> pin 4
  - NC -> GND
  - Amb INPUT_PULLUP:
      No premut = LOW
      Premut    = HIGH

  Ordres:
  - B0 = anar a inici / home
  - B1 = ampolla 1 + dispensar
  - B2 = ampolla 2 + dispensar
  - B3 = ampolla 3 + dispensar
  - B4 = ampolla 4 + dispensar
  - B5 = ampolla 5 + dispensar
  - B6 = ampolla 6 + dispensar
  - B7 = dispensador de gel, doble pulsacio fins a 50 graus
  - M 1000 = moure manualment 1000 passos
  - M -1000 = moure enrere 1000 passos
  - S 70 = moure servo manualment a 70 graus
  - P 2000 = dispensar manualment durant 2000 ms
  - Z = posar posicio actual a zero
  - Q = veure posicio
  - L = veure final de carrera
*/

// -------------------- PINS --------------------
const byte DIR_PIN = 2;
const byte STEP_PIN = 3;
const byte LIMIT_PIN = 4;
const byte SERVO_PIN = 9;

// -------------------- MOVIMENT --------------------
const int STEP_DELAY_US = 700;
const int RAMP_STEPS = 200;
const int START_DELAY_US = 2200;

// Si el motor va al revés, canvia HIGH per LOW.
const bool DIR_POSITIVE = HIGH;

// Direcció cap al final de carrera.
// Ara assumim que anar cap a l'inici és direcció negativa.
const bool DIR_HOME = !DIR_POSITIVE;

// Direcció per sortir del final de carrera.
const bool DIR_RELEASE = DIR_POSITIVE;

// Passos per sortir del final de carrera després de tocar-lo.
const long LIMIT_RELEASE_STEPS = 100;

// Estat del final de carrera quan està premut.
// Amb NC + INPUT_PULLUP: premut = HIGH.
const bool LIMIT_PRESSED_STATE = HIGH;

// -------------------- POSICIONS REALS --------------------
// Posicions absolutes respecte al zero després de fer B0.
const long POS_B1 = 2000;
const long POS_B2 = 4200;
const long POS_B3 = 6400;
const long POS_B4 = 8500;
const long POS_B5 = 10600;
const long POS_B6 = 12700;
const long POS_ICE = 14900;

// -------------------- SERVO --------------------
const int SERVO_REST_ANGLE = 30;       // posició segura per moure
const int SERVO_PRESS_ANGLE = 80;      // pressió ampolles
const int SERVO_HOME_ANGLE = 50;       // angle quan toca final de carrera a B0
const int SERVO_ICE_ANGLE = 50;        // gel només fins a 50

const int DEFAULT_PRESS_MS = 3300;

// Gel: menys temps i doble pulsació
const int ICE_PRESS_MS = 700;
const int ICE_PAUSE_MS = 300;

// -------------------- VARIABLES --------------------
Servo dispenserServo;

long currentPosition = 0;

char buffer[20];
byte bufferIndex = 0;

// -------------------- SETUP --------------------
void setup() {
  pinMode(DIR_PIN, OUTPUT);
  pinMode(STEP_PIN, OUTPUT);
  pinMode(LIMIT_PIN, INPUT_PULLUP);

  digitalWrite(DIR_PIN, DIR_POSITIVE);
  digitalWrite(STEP_PIN, LOW);

  dispenserServo.attach(SERVO_PIN);
  dispenserServo.write(SERVO_REST_ANGLE);

  Serial.begin(115200);

  Serial.println(F("CRISTAL NOCTURNO"));
  Serial.println(F("Ordres: B0-B7, M, S, P, Z, Q, L"));
}

// -------------------- LOOP --------------------
void loop() {
  readSerial();
}

// -------------------- LECTURA SERIAL --------------------
void readSerial() {
  while (Serial.available()) {
    char c = Serial.read();

    if (c == '\n' || c == '\r') {
      if (bufferIndex > 0) {
        buffer[bufferIndex] = '\0';
        processCommand(buffer);
        bufferIndex = 0;
      }
    }

    else if (bufferIndex < sizeof(buffer) - 1) {
      buffer[bufferIndex++] = c;
    }
  }
}

// -------------------- PROCESSAR ORDRES --------------------
void processCommand(char *cmd) {
  uppercase(cmd);

  // B0 = HOME
  if (cmd[0] == 'B' && cmd[1] == '0') {
    homeToLimit();
  }

  // B1-B7
  else if (cmd[0] == 'B' && cmd[1] >= '1' && cmd[1] <= '7') {
    int target = cmd[1] - '0';
    goToStationAndDispense(target);
  }

  // P 1500 = dispensar manualment amb servo normal
  else if (cmd[0] == 'P') {
    int ms = atoi(cmd + 2);
    if (ms <= 0) ms = DEFAULT_PRESS_MS;
    dispenseBottle(ms);
  }

  // S 70 = moure servo manualment a 70 graus
  else if (cmd[0] == 'S') {
    int angle = atoi(cmd + 2);

    if (angle >= 0 && angle <= 180) {
      dispenserServo.write(angle);
      Serial.print(F("SERVO "));
      Serial.println(angle);
    } else {
      Serial.println(F("ERR SERVO"));
    }
  }

  // M 2100 = moviment manual
  else if (cmd[0] == 'M') {
    long steps = atol(cmd + 2);
    moveSteps(steps);
    printPosition();
  }

  // Z = posar posició actual a zero
  else if (cmd[0] == 'Z') {
    currentPosition = 0;
    Serial.println(F("ZERO"));
    printPosition();
  }

  // Q = consultar posició
  else if (cmd[0] == 'Q') {
    printPosition();
  }

  // L = consultar final de carrera
  else if (cmd[0] == 'L') {
    printLimitState();
  }

  else {
    Serial.println(F("ERR"));
  }
}

// -------------------- ANAR A ESTACIÓ I DISPENSAR --------------------
void goToStationAndDispense(int station) {
  long targetPosition = getStationPosition(station);

  Serial.print(F("B"));
  Serial.print(station);
  Serial.print(F(" -> "));
  Serial.println(targetPosition);

  goToPosition(targetPosition);

  if (station == 7) {
    dispenseIce();
  } else {
    dispenseBottle(DEFAULT_PRESS_MS);
  }

  printPosition();
}

// -------------------- POSICIÓ DE CADA ESTACIÓ --------------------
long getStationPosition(int station) {
  if (station == 1) return POS_B1;
  if (station == 2) return POS_B2;
  if (station == 3) return POS_B3;
  if (station == 4) return POS_B4;
  if (station == 5) return POS_B5;
  if (station == 6) return POS_B6;
  if (station == 7) return POS_ICE;

  return 0;
}

// -------------------- ANAR A POSICIÓ ABSOLUTA --------------------
void goToPosition(long targetPosition) {
  long movement = targetPosition - currentPosition;
  moveSteps(movement);
}

// -------------------- DISPENSAR AMPOLLA --------------------
void dispenseBottle(int ms) {
  Serial.print(F("DISPENSE "));
  Serial.println(ms);

  dispenserServo.write(SERVO_PRESS_ANGLE);
  delay(ms);

  dispenserServo.write(SERVO_REST_ANGLE);
  delay(300);

  Serial.println(F("OK"));
}

// -------------------- DISPENSAR GEL --------------------
void dispenseIce() {
  Serial.println(F("ICE"));

  // Primera pulsació
  dispenserServo.write(SERVO_ICE_ANGLE);
  delay(ICE_PRESS_MS);

  dispenserServo.write(SERVO_REST_ANGLE);
  delay(ICE_PAUSE_MS);

  // Segona pulsació
  dispenserServo.write(SERVO_ICE_ANGLE);
  delay(ICE_PRESS_MS);

  dispenserServo.write(SERVO_REST_ANGLE);
  delay(300);

  Serial.println(F("OK ICE"));
}

// -------------------- HOME / B0 --------------------
void homeToLimit() {
  Serial.println(F("HOME"));

  // Abans de moure cap a home, servo a posició segura baixa.
  dispenserServo.write(SERVO_REST_ANGLE);
  delay(200);

  digitalWrite(DIR_PIN, DIR_HOME);
  delayMicroseconds(20);

  long maxSteps = 1000000;

  for (long i = 0; i < maxSteps; i++) {
    if (isLimitPressed()) {
      Serial.println(F("LIMIT"));

      // Quan arriba al final de carrera a B0, puja servo a 50.
      dispenserServo.write(SERVO_HOME_ANGLE);
      Serial.print(F("SERVO HOME "));
      Serial.println(SERVO_HOME_ANGLE);
      delay(200);

      releaseLimit();

      currentPosition = 0;

      Serial.println(F("HOME OK"));
      printPosition();
      return;
    }

    digitalWrite(STEP_PIN, HIGH);
    delayMicroseconds(4);
    digitalWrite(STEP_PIN, LOW);
    delayMicroseconds(STEP_DELAY_US);
  }

  Serial.println(F("ERR HOME"));
}

// -------------------- SORTIR DEL FINAL DE CARRERA --------------------
void releaseLimit() {
  Serial.print(F("RELEASE "));
  Serial.println(LIMIT_RELEASE_STEPS);

  digitalWrite(DIR_PIN, DIR_RELEASE);
  delayMicroseconds(20);

  for (long j = 0; j < LIMIT_RELEASE_STEPS; j++) {
    digitalWrite(STEP_PIN, HIGH);
    delayMicroseconds(4);
    digitalWrite(STEP_PIN, LOW);
    delayMicroseconds(STEP_DELAY_US);
  }

  Serial.println(F("RELEASE OK"));
}

// -------------------- MOURE STEPPER --------------------
void moveSteps(long steps) {
  if (steps == 0) {
    Serial.println(F("NO MOVE"));
    return;
  }

  // Sempre posem el servo a 30 abans de moure el carro.
  dispenserServo.write(SERVO_REST_ANGLE);
  delay(150);

  bool direction = steps > 0 ? DIR_POSITIVE : !DIR_POSITIVE;
  long totalSteps = labs(steps);

  digitalWrite(DIR_PIN, direction);
  delayMicroseconds(20);

  for (long i = 0; i < totalSteps; i++) {

    // Si toca el final de carrera durant un moviment normal:
    // parem, sortim una mica i posem posició 0.
    if (isLimitPressed()) {
      Serial.println(F("STOP LIMIT"));

      // En moviment normal NO pugem el servo a 50.
      // Només ens assegurem que estigui a 30.
      dispenserServo.write(SERVO_REST_ANGLE);
      delay(100);

      releaseLimit();

      currentPosition = 0;

      Serial.println(F("LIMIT ZERO"));
      break;
    }

    int delayNow = STEP_DELAY_US;

    // Rampa simple d'acceleració i frenada
    long accelIndex = i;
    long decelIndex = totalSteps - 1 - i;
    long rampIndex = min(accelIndex, decelIndex);

    if (rampIndex < RAMP_STEPS) {
      delayNow = map(rampIndex, 0, RAMP_STEPS, START_DELAY_US, STEP_DELAY_US);
    }

    // Pols STEP
    digitalWrite(STEP_PIN, HIGH);
    delayMicroseconds(4);
    digitalWrite(STEP_PIN, LOW);
    delayMicroseconds(delayNow);

    // Actualitzem posició estimada
    if (direction == DIR_POSITIVE) {
      currentPosition++;
    } else {
      currentPosition--;
    }

    // Stop manual: enviar X durant el moviment
    if (Serial.available()) {
      char c = Serial.peek();
      if (c == 'X' || c == 'x') {
        Serial.read();
        Serial.println(F("STOP"));
        break;
      }
    }
  }

  Serial.println(F("DONE"));
}

// -------------------- FINAL DE CARRERA --------------------
bool isLimitPressed() {
  return digitalRead(LIMIT_PIN) == LIMIT_PRESSED_STATE;
}

void printLimitState() {
  if (isLimitPressed()) {
    Serial.println(F("LIMIT ON"));
  } else {
    Serial.println(F("LIMIT OFF"));
  }
}

// -------------------- MOSTRAR POSICIÓ --------------------
void printPosition() {
  Serial.print(F("POS "));
  Serial.println(currentPosition);
}

// -------------------- PASSAR TEXT A MAJÚSCULES --------------------
void uppercase(char *text) {
  while (*text) {
    if (*text >= 'a' && *text <= 'z') {
      *text = *text - 32;
    }
    text++;
  }
}