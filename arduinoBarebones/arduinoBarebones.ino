#include <Metro.h>

#define LFET 4
#define HFET 3

#define FAN 6
#define PURGE 10
#define SUPPLY 5
#define TEMP A9

uint32_t startTime;
double fanSpeed = 0.4;


uint32_t Short_Intervals[12] = {99999999,100,100,100,100,100,
                                99999999,100,100,100,100,100};
const uint32_t Short_Durations[12] = {20,20,20,20,20,20,
                                      20,20,20,20,20,20};
uint8_t Short_ind = 0;
uint32_t Purge_Intervals[12] = {99999999,0,0,300,0,0,
                                300,0,0,300,0,0};
const uint32_t Purge_Durations[12] = {175,175,175,175,175,175,
                                      175,175,175,175,175,175};
uint8_t Purge_ind = 0;
uint32_t Reboot_Intervals[1] = {999999999}; // 9342
uint8_t Reboot_ind = 0;

uint32_t Short_Interval = Short_Intervals[0]*1000;
uint32_t Short_Duration = Short_Durations[0];
uint32_t Purge_Interval = Purge_Intervals[0]*1000;
uint32_t Purge_Duration = Purge_Durations[0];
uint32_t Reboot_Interval = Reboot_Intervals[0]*1000;
Metro Short_IntervalTimer = Metro(Short_Interval);
Metro Short_DurationTimer = Metro(Short_Duration);
Metro Purge_IntervalTimer = Metro(Purge_Interval);
Metro Purge_DurationTimer = Metro(Purge_Duration);
Metro Reboot_IntervalTimer = Metro(Reboot_Interval);

Metro watchdogTimer = Metro(10);
//Metro printStatsTimer = Metro(10); // polling mode
bool shorted, purged;

const uint32_t Short_StartupIntervals[6] = {0, 616, 616, 616, 313, 313};
const uint32_t Short_StartupDurations[6] = {50, 50, 50, 50, 100, 50};
uint8_t Short_StartupIndex = 0;

void setup() {
  kickDog();

  for (uint8_t i = 0; i<(sizeof(Short_Intervals)/sizeof(uint32_t)); i++){
    Short_Intervals[i] = Short_Intervals[i]*1000; // convert s to ms
  }
  for (uint8_t i = 0; i<(sizeof(Purge_Intervals)/sizeof(uint32_t)); i++){
    Purge_Intervals[i] = Purge_Intervals[i]*1000; // convert s to ms
  }
  for (uint8_t i = 0; i<(sizeof(Reboot_Intervals)/sizeof(uint32_t)); i++){
    Reboot_Intervals[i] = Reboot_Intervals[i]*1000; // convert s to ms
  }

  analogWriteFrequency(FAN,100000);
  
  Serial.begin(115200);

  pinMode(LFET,OUTPUT);
  digitalWrite(LFET,HIGH); // NOTE: this output is inverted by gate driver
  analogWrite(FAN,LOW);
  analogWrite(PURGE,LOW);
  analogWrite(SUPPLY,LOW);
  pinMode(13,OUTPUT);
  
  startTime = micros();

  bootup();
  printInstructions();
}

void loop() {
  if (Short_IntervalTimer.check()){
    SC();
  }
  if (Short_DurationTimer.check()){
    digitalWrite(LFET,HIGH);
  }
  if (Purge_IntervalTimer.check()){
    purge();
  }
  if (Purge_DurationTimer.check()){
    digitalWrite(PURGE,LOW);
  }
  if (Reboot_IntervalTimer.check()){
    reboot();
  }
  
  if (watchdogTimer.check()){
    kickDog();
  }
//  if (printStatsTimer.check()){
//    printStats();
//  }
  readSerial();
}

// this code is blocking
void bootup(){
  kickDog();
  digitalWrite(FAN,LOW);
  digitalWrite(SUPPLY,HIGH);
  // 3s purge
  digitalWrite(PURGE,HIGH);
  delay2(3000);
  digitalWrite(PURGE,LOW);
  delay2(2000);
  
  for(uint8_t ind = 0; ind<(sizeof(Short_StartupIntervals)/sizeof(uint32_t)); ind++){
    delay2(Short_StartupIntervals[ind]);
    digitalWrite(LFET,LOW);
    delay2(Short_StartupDurations[ind]);
    digitalWrite(LFET,HIGH);
  }
  analogWrite(FAN,HIGH);
  delay2(100);
  analogWrite(FAN,fanSpeed*256);

  for (uint8_t ind = 0; ind<2; ind++){
    Purge_IntervalTimer.reset();
    Short_IntervalTimer.reset();
    delay2(4900);
    digitalWrite(PURGE,HIGH);
    delay2(100);
    digitalWrite(PURGE,LOW);
    delay2(4900);
    digitalWrite(LFET,LOW);
    delay2(100);
    digitalWrite(LFET,HIGH);
    delay(100);
  }
  
  Purge_IntervalTimer.reset();
//  delay2(5000);
  Short_IntervalTimer.reset();
  kickDog();
  Reboot_IntervalTimer.reset();
}
void SC(){
  digitalWrite(LFET,LOW);
  Short_Duration = Short_Durations[Short_ind];
  Short_DurationTimer.interval(Short_Duration);
  Short_DurationTimer.reset();
  shorted = true;
  if (Short_ind<(sizeof(Short_Durations)/sizeof(uint32_t)-1)){
    Short_ind++;
  }
  else{
    Short_ind = 0;
  }
  Short_Interval = Short_Intervals[Short_ind];
  Short_IntervalTimer.interval(Short_Interval);
  Short_IntervalTimer.reset();
}
void purge(){
  digitalWrite(PURGE,HIGH);
  Purge_Duration = Purge_Durations[Purge_ind];
  Purge_DurationTimer.interval(Purge_Duration);
  Purge_DurationTimer.reset();
  purged = true;
  if (Purge_ind<(sizeof(Purge_Durations)/sizeof(uint32_t)-1)){
    Purge_ind++;
  }
  else{
    Purge_ind = 0;
  }
  Purge_Interval = Purge_Intervals[Purge_ind];
  Purge_IntervalTimer.interval(Purge_Interval);
  Purge_IntervalTimer.reset();
}

void reboot(){
  if (Reboot_ind<(sizeof(Reboot_Intervals)/sizeof(uint32_t)-1)){
    Reboot_ind++;
  }
  else{
    Reboot_ind = 0;
  }
  Reboot_Interval = Reboot_Intervals[Reboot_ind];
  Reboot_IntervalTimer.interval(Reboot_Interval);
  Reboot_IntervalTimer.reset();
  bootup();
}
double readTemp(){
  double prct = analogRead(TEMP)/1024.0;
  return (20 + (prct/(1-prct)*1208 - 1076)/3.8) * 9/5 + 32;
}

// serial commands
void printStats(){
  char toPrint [100];
  sprintf(toPrint,"%d\t%d\t%d\t",Short_Interval,Short_Duration,shorted);
  Serial.print(toPrint);
  sprintf(toPrint,"%d\t%d\t%d\t",Purge_Interval,Purge_Duration,purged);
  Serial.print(toPrint);
  Serial.print(readTemp(),2);
  Serial.println("°F");
  shorted = false;
  purged = false;
}
void printInstructions(){
  Serial.println("Key Commands:");
  Serial.println("\t'h'  - print this help menu");
  Serial.println("\t'C'  - poll for stats");
  Serial.println("\t'b'  - initiate bootup procedure");
  Serial.println("\t'r'  - manually apply short circuit");
  Serial.println("\t'q'  - manually apply purge");
  Serial.println("\t'#F' - set fan speed to # (out of 1)");
  Serial.println("\t'#S' - set SC interval to # milliseconds");
  Serial.println("\t'#P' - set purge interval to # milliseconds");
  Serial.println("\t'#s' - set SC duration to # milliseconds");
  Serial.println("\t'#p' - set purge duration to # milliseconds");
}
char buf[50];
uint8_t bufInd = 0;
void readSerial(){
  if (Serial.available()){
    char c = Serial.read();
    switch(c){
      case 'h':
        printInstructions();
        break;
      case 'C':
        printStats();
        break;
      case 'b':
        bootup();
        break;
      case 'r':
        digitalWrite(LFET,LOW);
        Short_DurationTimer.reset();
        Serial.println("short circuit started");
        break;
      case 'q':
        digitalWrite(PURGE,HIGH);
        Purge_DurationTimer.reset();
        break;
      case 'F':
        fanSpeed = (float)atof(buf);
        analogWrite(FAN,fanSpeed*256);
        resetSerialBuffer();
        break;
      case 'S':
        Short_Interval = (int)atoi(buf);
        Short_IntervalTimer.interval(Short_Interval);
        resetSerialBuffer();
        break;
      case 'P':
        Purge_Interval = (int)atoi(buf);
        Purge_IntervalTimer.interval(Purge_Interval);
        resetSerialBuffer();
        break;
      case 's':
        Short_Duration = (int)atoi(buf);
        Short_DurationTimer.interval(Short_Duration);
        resetSerialBuffer();
        break;
      case 'p':
        Purge_Duration = (int)atoi(buf);
        Purge_DurationTimer.interval(Purge_Duration);
        resetSerialBuffer();
        break;
      case '0':case '1':case '2':case '3':case '4':
      case '5':case '6':case '7':case '8':case '9':
      case '.':case '-':
        buf[bufInd] = c;
        bufInd++;
        break;
    }
  }
}
void resetSerialBuffer(){
  for (uint8_t i=0;i<bufInd;i++){
    buf[i] = 0;
  }
  bufInd = 0;
}

void kickDog()
{
  noInterrupts();
  WDOG_REFRESH = 0xA602;
  WDOG_REFRESH = 0xB480;
  interrupts();
  digitalWriteFast(13,!digitalReadFast(13));
}
void delay2(uint32_t duration){
  uint32_t nowT = millis();
  while((millis()-nowT)<duration){
    delay(10);
    kickDog();
  }
  watchdogTimer.reset();
}
