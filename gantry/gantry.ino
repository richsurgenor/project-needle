#include <gantry.hpp>

void setup() {
  int m=1;
  
  gantry_init();    //initialize gantry parameters (serial)
  move_y_home();    //move y-axis to work area origin
  
  while(m != 0){    //wait to receive valid coordinate from Pi
    m = wait_for_coordinate();  
  }
  move_cap_to_IL();  //move the capacitive sensor over the IL
  position_needle(); //move needle to spot just behind IL
  wait_for_error_check();  //adjust position of needle tip
  inject_needle();
  go_home();
  
  while(1);
}

void loop() {
  // put your main code here, to run repeatedly:
}
