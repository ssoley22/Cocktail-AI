#include <Servo.h>
#include <SPI.h>
#include <MFRC522.h>
#include <Adafruit_NeoPixel.h>

/*
  Ordres Sèrie:
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

// ---------- PINS HARDWARE ----------
const byte DIR_PIN = 2;        // DIR del driver stepper
const byte STEP_PIN = 3;       // STEP del driver stepper
const byte LIMIT_PIN = 4;      // Final de carrera
const byte LED_PIN = 6;        // Pin de control de la tira de LEDs
const byte SERVO_PIN = 9;      // Senyal del servo
const byte RFID_RST_PIN = 5;   // Reset del lector RFID
const byte RFID_SS_PIN = 10;   // SDA/SS del lector RFID

// ---------- CONFIGURACIÓ MATRIU LEDS ----------
const byte COLS = 6;           // 6 ampolles (columnes)
const byte ROWS = 4;           // 4 LEDs d'alçada per ampolla (files)
const byte NUM_LEDS = (COLS * ROWS); 

Adafruit_NeoPixel tira = Adafruit_NeoPixel(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);

// Paleta de colors
uint32_t VERD, ROSA, BLAU, BLANC, APAGAT = 0;

// ---------- STEPPER (MOTORS) ----------
const bool DIR_POSITIVE = HIGH;        
const bool DIR_HOME = !DIR_POSITIVE;   
const bool DIR_RELEASE = DIR_POSITIVE; 

const int STEP_DELAY_US = 700;   
const int START_DELAY_US = 2200; 
const int RAMP_STEPS = 200;      

const long LIMIT_RELEASE_STEPS = 100; 
const long MAX_HOME_STEPS = 1000000;  

const bool LIMIT_PRESSED_STATE = HIGH; 

// ---------- POSICIONS MECÀNIQUES ----------
const long POS_A[7] = {
  0,      // No usat; permet que A1 sigui índex 1
  2000,   // Coordenada Ampolla 1
  4200,   // Coordenada Ampolla 2
  6400,   // Coordenada Ampolla 3
  8500,   // Coordenada Ampolla 4
  10600,  // Coordenada Ampolla 5
  12700   // Coordenada Ampolla 6
};
const long POS_ICE = 14900; // Coordenada Estació de gel

// ---------- SERVO ACTUADOR ----------
const int SERVO_REST = 30;      
const int SERVO_PRESS = 80;     
const int SERVO_HOME = 55;      
const int SERVO_ICE = 50;       

const int SERVO_UNJAM = 60;     
const int UNJAM_DOWN_MS = 180;  
const int UNJAM_UP_MS = 180;    

const int DEFAULT_PRESS_MS = 3300; 
const int DEFAULT_ICE_MS = 600;    
const int ICE_PAUSE_MS = 250;      
const int MAX_PRESS_MS = 10000;    

// ---------- ESTATS DE LA MÀQUINA (LED CONTROL) ----------
enum MachineState { STATE_IDLE, STATE_MOVING, STATE_DISPENSING, STATE_PAYING };
MachineState estatActual = STATE_IDLE;

// ---------- VARIABLES GLOBALS ----------
Servo servo;
long pos = 0;
char cmd[24];
byte idx = 0;

MFRC522 rfid(RFID_SS_PIN, RFID_RST_PIN);
byte UID_USUARI[4] = {0x4D, 0x18, 0xA2, 0x30}; 
const unsigned long PAY_TIMEOUT_MS = 60000; 

// Variables de temps per a les animacions de fons no bloquejants
unsigned long darreraActualitzacioLED = 0;
int pasAnimacio = 0;
int patroActual = 0;

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

  // Inicialització de la matriu de NeoPixels
  tira.begin();
  VERD  = tira.Color(130, 255, 0);   
  ROSA  = tira.Color(255, 40,  140); 
  BLAU  = tira.Color(0,   255, 255); 
  BLANC = tira.Color(255, 255, 255);
  tira.clear();
  tira.show();

  if (home()) {
    Serial.println(F("HOME OK")); 
  } else {
    Serial.println(F("ERR"));
  }
}

// ---------- LOOP PRINCIPAL ----------
void loop() {
  readSerial();       
  gestionarLEDs();    
}

// ---------- SERIAL INTERPRETATION ----------
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

// ---------- ACTIONS ROUTINES ----------
void processCommand() {
  if (strcmp(cmd, "HOME") == 0) {
    if (home()) {
      Serial.println(F("HOME OK"));
    } else {
      Serial.println(F("ERR"));
    }
    estatActual = STATE_IDLE;
    return;
  }

  if (strcmp(cmd, "PAY") == 0) {
    estatActual = STATE_PAYING;
    if (waitPayment()) {
      Serial.println(F("PAY OK"));
    } else {
      Serial.println(F("ERR"));
    }
    estatActual = STATE_IDLE;
    return;
  }

  if (cmd[0] == 'A' && cmd[1] >= '1' && cmd[1] <= '6') {
    int bottle = cmd[1] - '0';
    int ms = getTime(cmd + 2, DEFAULT_PRESS_MS);

    if (!validTime(ms)) {
      Serial.println(F("ERR"));
      estatActual = STATE_IDLE;
      return;
    }

    estatActual = STATE_MOVING; 
    if (goTo(POS_A[bottle])) {
      estatActual = STATE_DISPENSING;
      buidarAmpollaAnimada(bottle - 1, ms); 
      Serial.println(F("OK"));
    } else {
      Serial.println(F("ERR"));
    }
    estatActual = STATE_IDLE;
    return;
  }

  if (cmd[0] == 'I' && cmd[1] == 'C' && cmd[2] == 'E') {
    int ms = getTime(cmd + 3, DEFAULT_ICE_MS);

    if (!validTime(ms)) {
      Serial.println(F("ERR"));
      estatActual = STATE_IDLE;
      return;
    }

    estatActual = STATE_MOVING;
    if (goTo(POS_ICE)) {
      estatActual = STATE_DISPENSING;
      pressIce(ms);
      Serial.println(F("ICE OK"));
    } else {
      Serial.println(F("ERR"));
    }
    estatActual = STATE_IDLE;
    return;
  }

  Serial.println(F("ERR"));
}

// ---------- HOME ----------
bool home() {
  // CORRECCIÓ 3: Apaguem els LEDs a cap abans d'entrar al bucle bloquejant del motor
  tira.clear();
  tira.show();

  servo.write(SERVO_REST);
  delay(200);

  digitalWrite(DIR_PIN, DIR_HOME);
  delayMicroseconds(20);

  for (long i = 0; i < MAX_HOME_STEPS; i++) {
    if (limitPressed()) {
      releaseLimit();
      pos = 0; 
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
  // CORRECCIÓ 3: Apaguem els LEDs directament en demanar moviment mecànic
  tira.clear();
  tira.show();

  servo.write(SERVO_REST); // Sempre baixa el servo abans de qualsevol canvi
  delay(150);

  // CORRECCIÓ 2: El comprovant de target és ara posterior a assegurar que el servo ha baixat completament
  if (steps == 0) return true;

  bool dir = (steps > 0) ? DIR_POSITIVE : !DIR_POSITIVE;
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

    if (dir == DIR_POSITIVE) pos++;
    else pos--;
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

// ---------- DISPENSACIÓ DE LÍQUIDS ----------
void buidarAmpollaAnimada(int columna, int tempsTotalMs) {
  servo.write(SERVO_PRESS);
  int tempsPerFila = tempsTotalMs / ROWS;
  
  for (int f = ROWS - 1; f >= 0; f--) {
    tira.clear();
    for (int i = 0; i <= f; i++) {
      pintarPixel(columna, i, BLANC); 
    }
    tira.show();
    delay(tempsPerFila);
  }
  
  servo.write(SERVO_UNJAM);
  delay(UNJAM_DOWN_MS);
  servo.write(SERVO_PRESS);
  delay(UNJAM_UP_MS);
  
  servo.write(SERVO_REST);
  tira.clear();
  tira.show();
  delay(300);
}

void pressIce(int ms) {
  for(int r=0; r<2; r++) {
    servo.write(SERVO_ICE);
    for(int c=0; c<COLS; c++) for(int f=0; f<ROWS; f++) pintarPixel(c, f, BLAU);
    tira.show();
    delay(ms/2);
    
    servo.write(SERVO_REST);
    tira.clear();
    tira.show();
    delay(ICE_PAUSE_MS);
  }
}

// ---------- RFID / PAGAMENT ----------
bool waitPayment() {
  unsigned long startTime = millis();
  while (millis() - startTime < PAY_TIMEOUT_MS) {
    // CORRECCIÓ 1: Cridem de forma explícita el gestor de NeoPixels dins del bucle de l'RFID per mantenir el cian bategant
    gestionarLEDs();

    if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
      delay(50);
      continue;
    }

    bool uidCorrecte = (rfid.uid.size == 4);
    if (uidCorrecte) {
      for (byte i = 0; i < 4; i++) {
        if (rfid.uid.uidByte[i] != UID_USUARI[i]) {
          uidCorrecte = false;
          break;
        }
      }
    }

    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();

    if (uidCorrecte) return true;
    delay(500); 
  }
  return false;
}

// ---------- GESTOR MATRICIAL NEOPIXEL ----------
void pintarPixel(int columna, int fila, uint32_t color) {
  int indexLED;
  if (columna % 2 == 0) {
    indexLED = (columna * ROWS) + fila;
  } else {
    indexLED = (columna * ROWS) + (ROWS - 1 - fila);
  }
  tira.setPixelColor(indexLED, color);
}

void gestionarLEDs() {
  unsigned long ara = millis();

  switch (estatActual) {
    case STATE_MOVING:
      tira.clear();
      tira.show();
      break;

    case STATE_PAYING:
      if (ara - darreraActualitzacioLED > 30) {
        darreraActualitzacioLED = ara;
        pasAnimacio += 4;
        if(pasAnimacio > 255) pasAnimacio = 0;
        int lluminositat = abs(128 - pasAnimacio) * 2;
        uint32_t colorCian = tira.Color(0, lluminositat, lluminositat);
        for(int c=0; c<COLS; c++) for(int f=0; f<ROWS; f++) pintarPixel(c, f, colorCian);
        tira.show();
      }
      break;

    case STATE_IDLE:
      if (ara - darreraActualitzacioLED > 120) { 
        darreraActualitzacioLED = ara;
        executarAnimacioFons();
      }
      break;
      
    case STATE_DISPENSING:
      break;
  }
}

void executarAnimacioFons() {
  pasAnimacio++;
  
  if (patroActual == 0) {
    tira.clear();
    int fila = pasAnimacio % (ROWS * 2);
    if (fila < ROWS) {
      for(int c=0; c<COLS; c++) pintarPixel(c, fila, VERD);
    } else {
      for(int c=0; c<COLS; c++) pintarPixel(c, (ROWS * 2 - 1) - fila, ROSA);
    }
    tira.show();
    if (pasAnimacio >= 12) { pasAnimacio = 0; patroActual = 1; }
  }
  else if (patroActual == 1) {
    tira.clear();
    pintarPixel(0, 3, ROSA); pintarPixel(5, 3, ROSA);
    pintarPixel(1, 2, ROSA); pintarPixel(4, 2, ROSA);
    pintarPixel(2, 2, ROSA); pintarPixel(3, 2, ROSA);
    pintarPixel(2, 0, ROSA); pintarPixel(3, 0, ROSA);
    pintarPixel(2, 1, ROSA); pintarPixel(3, 1, ROSA);
    tira.show();
    if (pasAnimacio >= 6) { pasAnimacio = 0; patroActual = 2; }
  }
  else if (patroActual == 2) {
    tira.clear();
    int diagonal = pasAnimacio % (COLS + ROWS - 1);
    for (int col = 0; col < COLS; col++) {
      int fila = diagonal - col;
      if (fila >= 0 && fila < ROWS) pintarPixel(col, fila, VERD);
    }
    tira.show();
    if (pasAnimacio >= 9) { pasAnimacio = 0; patroActual = 3; }
  }
  else if (patroActual == 3) {
    tira.clear();
    int fosa = pasAnimacio % 3;
    if (fosa == 0) {
      for(int f=0; f<ROWS; f++) { pintarPixel(2, f, VERD); pintarPixel(3, f, ROSA); }
    } else if (fosa == 1) {
      for(int f=0; f<ROWS; f++) { pintarPixel(1, f, VERD); pintarPixel(4, f, ROSA); }
    } else {
      for(int f=0; f<ROWS; f++) { pintarPixel(0, f, VERD); pintarPixel(5, f, ROSA); }
    }
    tira.show();
    if (pasAnimacio >= 12) { pasAnimacio = 0; patroActual = 0; }
  }
}

// ---------- AUXILIARS ----------
bool limitPressed() {
  return digitalRead(LIMIT_PIN) == LIMIT_PRESSED_STATE;
}

int getTime(char *text, int defaultMs) {
  while (*text == ' ') text++;
  if (*text == '\0') return defaultMs;
  return atoi(text);
}

bool validTime(int ms) {
  return (ms > 0 && ms <= MAX_PRESS_MS);
}