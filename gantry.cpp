#include <gantry.hpp>
#include <Arduino.h>

int x_coord, y_coord, z_coord = 0;

int mm_to_steps(int axis, double distance){

	int totalSteps;
	
	if(axis == X_AXIS){
		totalSteps = (double)STEPS_PER_REVOLUTION * ( 1 / (double)SCREW_LEAD_X) * ((double)(distance + 1));
	}
	if(axis == Y_AXIS){
		totalSteps = (double)STEPS_PER_REVOLUTION * ( 1 / (double)SCREW_LEAD_Y) * ((double)(distance + 1));
	}
	if(axis == Z_AXIS){
		totalSteps = (double)STEPS_PER_REVOLUTION * ( 1 / (double)SCREW_LEAD_Z) * ((double)(distance + 1));
	}
	
	return(totalSteps);
}

void select_direction_pin(int dir){

	if(dir == FORWARD){
		digitalWrite(DIR_PIN_X,  HIGH);
		digitalWrite(DIR_PIN_Y1, HIGH);
		digitalWrite(DIR_PIN_Y2, HIGH);
		digitalWrite(DIR_PIN_Z,  HIGH);	
	}
	
	if(dir == BACKWARD){
		digitalWrite(DIR_PIN_X,  LOW);
		digitalWrite(DIR_PIN_Y1, LOW);
		digitalWrite(DIR_PIN_Y2, LOW);
		digitalWrite(DIR_PIN_Z,  LOW);
	}
}

int select_step_pin(int axis){
	
	int stepPin;
	
	if(axis == X_AXIS){
		stepPin = STEP_PIN_X;
	}
	if(axis == Y_AXIS){
		stepPin = STEP_PIN_Y1;
	}
	if(axis == Z_AXIS){
		stepPin = STEP_PIN_Z;
	}
	return(stepPin);
}

void gantry_init(){
	Serial.begin(115200);
}

void move_stepper(int axis, int coordinate_mm, int dir){
	
	int i, 
		stepPin, 
		steps,
		z_depth;
	
	steps = mm_to_steps(axis, coordinate_mm);
	select_direction_pin(dir);
	stepPin = select_step_pin(axis);
	
	if(axis = Z_AXIS  && dir == FORWARD){
		z_depth = depth_finder();
	}
	
	for(i=0; i<steps; i++){
		digitalWrite(stepPin, HIGH);
		if(axis == Y_AXIS){
			digitalWrite(STEP_PIN_Y2, HIGH);
		}
		delay(2);
		digitalWrite(stepPin, LOW);
		if(axis == Y_AXIS){
			digitalWrite(STEP_PIN_Y2, LOW);
		}
		digitalWrite(STEP_PIN_Y2, LOW);
		delay(2);
	}
	
}

void move_y_home(){
	
	int i;
	
	select_direction_pin(FORWARD);
	
	for(i=0; i<STEPS_TO_Y_HOME; i++){
		digitalWrite(STEP_PIN_Y1, HIGH);
		digitalWrite(STEP_PIN_Y2, HIGH);
		delay(2);
		digitalWrite(STEP_PIN_Y1, LOW);
		digitalWrite(STEP_PIN_Y2, LOW);
		delay(2);
	}
}

int wait_for_coordinate(){
	
	int value[8];
	while(Serial.available() < 8);
	for(int i=0; i<8; i++){
		value[i] = Serial.read();
	}
	if(value[0] == 56 && value[4] == 57){
		for(int n = 1; n<4; n++){
			value[n] -= 48;
			value[n+4] -= 48;
		}
	
		x_coord = (value[1]*100)+(value[2]*10)+value[3];
		y_coord = (value[5]*100)+(value[6]*10)+value[7];
		Serial.println(x_coord);
		Serial.println(y_coord);
	}
	else{
	Serial.flush();
	return(1);
	}
	
	return(0);
	
}

void move_xyz_to_IL(){
	
	int dir;
	
	dir = FORWARD;
	move_stepper(X_AXIS, x_coord, dir);
	move_stepper(Y_AXIS, y_coord, dir);
	move_stepper(Z_AXIS, z_coord, dir);

}


int wait_for_error_check(){

	int old_x_coord, 
		old_y_coord, 
		old_z_coord,
		dx, dy, dz, dirx, diry;
		
	old_x_coord = x_coord;
	old_y_coord = y_coord;
	old_z_coord = z_coord;
	
	int m=1;
	while(m != 0){
		m = wait_for_coordinate();
	}
	
	dx = old_x_coord - x_coord;
	dy = old_y_coord - y_coord;
	
	if(dx < 0){
		dirx = FORWARD;
		dx *= -1;
	}
	else{
		dirx = BACKWARD;
	}
	if(dy < 0){
		diry = FORWARD;
		dy *= -1;
	}
	else{
		diry = BACKWARD;
	}
	
	
	if(dx > 3){
		move_stepper(X_AXIS, dx, dirx);
	}
	if(dy > 3){
		move_stepper(Y_AXIS, dy, diry);
	}
}

int depth_finder(){
	
	int capSamples[10], debounceCap;
	bool capOut;
	int z_depth = 0;
	
	capOut = digitalRead (CAP_SENSE_PIN);
		while(capOut == 0){
			capOut = digitalRead(CAP_SENSE_PIN);
			digitalWrite(STEP_PIN_Z, HIGH);
			delay(2);
			z_depth++;
			digitalWrite(STEP_PIN_Z, LOW);
			delay(2);
		}
		for(int n = 0; n<10; n++){
			debounceCap += capSamples[n];
		}
		if(debounceCap > 7){
			
		}
	return(z_depth);
}

void echo() {
    Serial.println("hi");
}
