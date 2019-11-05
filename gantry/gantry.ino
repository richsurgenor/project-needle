#include <gantry.hpp>
#include <Servo.h>


void setup() {
  int m = 1;
  gantry_init();
  
  move_y_home();
  while(m != 0){
  m = wait_for_coordinate();
  }
  move_cap_to_IL();
  while(digitalRead(LIMIT_Y_HOME_PIN) != HIGH);
  position_needle();
  while(digitalRead(LIMIT_Y_HOME_PIN) != HIGH);
  inject_needle();
  while(digitalRead(LIMIT_Y_HOME_PIN) != HIGH);
  pull_needle();
  while(digitalRead(LIMIT_Y_HOME_PIN) != HIGH);
  move_back_from_IL();
  //while(digitalRead(LIMIT_Y_HOME_PIN) != HIGH);*/
  //move_y_back();
  while(1);
}

void loop() {
  // put your main code here, to run repeatedly:
}
