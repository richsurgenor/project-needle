#include <gantry.hpp>
#include <Servo.h>


void setup() {
  int m = 1, z_depth;
  gantry_init();
  delay(3000);

  while(digitalRead(LIMIT_Y_HOME_PIN) != HIGH);
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
  //move_y_back();
  
}

void loop() {
  // put your main code here, to run repeatedly:
  while(1);
}

