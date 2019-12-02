#include <gantry.hpp>
#include <Servo.h>

String inputString = "";
bool stringComplete = false;

void setup() {
  /*int m = 1, z_depth;
  gantry_init();
  delay(3000);*/

  Serial.begin(115200);
  inputString.reserve(200);
  
  int m = 1;
  gantry_init();
  

  #if HEADLESS
  //move_y_home();
  //while(m != 0){
  //m = wait_for_coordinate();
  //}
  /*move_cap_to_IL();
  while(digitalRead(LIMIT_Y_HOME_PIN) != HIGH); // i dont think this will work because the gantry will never move after it hits this line... need interrupts on limit switches
  position_needle();
  while(digitalRead(LIMIT_Y_HOME_PIN) != HIGH);
  inject_needle();
  while(digitalRead(LIMIT_Y_HOME_PIN) != HIGH);
  pull_needle();
  while(digitalRead(LIMIT_Y_HOME_PIN) != HIGH);
  move_back_from_IL();*/
  //while(digitalRead(LIMIT_Y_HOME_PIN) != HIGH);
  move_y_back();
  while(1);
  #endif

  /*while(digitalRead(LIMIT_Y_HOME_PIN) != HIGH);
  move_y_home();
  while(m != 0){
  m = wait_for_coordinate();
  Serial.println(m);
  }
  z_depth = move_cap_to_IL();
  Serial.println("z_depth 3: ");
  Serial.println(z_depth);
  position_needle();
  inject_needle();
  pull_needle();
  move_back_from_IL(z_depth);
  //move_y_back();*/
  
}

void(* resetFunc) (void) = 0;

void loop() {
  #if !HEADLESS
  if (stringComplete) {
    //Serial.print(inputString);
    int result = process_req(inputString.c_str());
    if (result == 100) {
      resetFunc();
    }
    // clear the string:
    inputString = "";
    stringComplete = false;
  }
  #endif
}

#if !HEADLESS
void serialEvent() {
  while (Serial.available()) {
    // get the new byte:
    char inChar = (char)Serial.read();
    // add it to the inputString:
    inputString += inChar;
    // if the incoming character is a newline, set a flag so the main loop can
    // do something about it:
    if (inChar == '\n') {
      stringComplete = true;
    }
  }
}
#endif
