//*********************************************************
//	gantry.cpp					                          *
//	Jackson Solley				                          *		
//	10/31/2019					                          *
//	Summary:  				                              *
//	Source file with all of the functions required to     *
//	tell the gantry how/where to move the needle.	      *
//	Need to fiugre out a way for Arduino to receive       *
//	various commands from Pi without polling.             *
//							                              *
//*********************************************************


#include <gantry.hpp>
#include <Servo.h>

Servo myservo;  // create servo object to control a servo

static int x_coord, y_coord, z_coord = 0;
static int z_depth = 0, z_found = 0;
static bool enable = 0;

//String cmd = "";

/**********************************
 * FUNCTIONS IN ORDER OF EXECUTION
***********************************/

/********************************************************************
*Function: gantry_init
*Purpose: Initializes serial baud rate
*Returns:  void
*Inputs:   No input
/********************************************************************/
void gantry_init(){
	Serial.begin(115200);
	pinMode(4, OUTPUT);
	digitalWrite(4, HIGH);
	delay(3000);
	digitalWrite(4, LOW);
	myservo.attach(A2);  // attaches the servo on pin A2 to the servo object
	#if !HEADLESS
	    status_msg("Initialized Gantry...");
	    delay(1000);
	    send_cmd(CMD_GANTRY_INITIALIZED);
    #endif
}

/********************************************************************
*Function: move_y_home
*Purpose:  Move to y-axis to the predefined working area origin
*Returns:  void
*Inputs:   no input
/********************************************************************/
void move_y_home(){

	move_stepper(Y_AXIS, MM_TO_Y_HOME, FORWARD); // changed because STEPS_TO_Y_HOME was not declared

}

/********************************************************************
*Function: wait_for_coordinate
*Purpose:  Waits to receive a valid coordinate from the Pi in the
		   format (8xxxxxx) where xxx represents a 3 digit mm value
		   and 8 being the command opcode to validate that this
		   is a valid wait-for-coordinate packet
*Returns:  0 (valid coordinate received)
*		   1 (invalid coordinate packet)
*Inputs:   no input
/********************************************************************/
int wait_for_coordinate(){

	int value[8];
	while(Serial.available() < 8);
	for(int i=0; i<8; i++){
		value[i] = Serial.read();
		Serial.write(value[i]);
		Serial.println(value[i]);
	}
	Serial.println(""); // send eol
	if (value[0] == CMD_WAIT_COORDINATE && value[4] == CMD_FINISH){
         /* Concerns
          * If value[0] is not the start of this packet.. but value[1+n] happens to be..
          * in reality we will be waiting to read in cmds and flushing the buffer definitely shouldnt happen
          * if the cmd happens to be a different one...
          * May be slow.. google says pi is 40 times faster than the arduino.
          * Mathematics Type	Arduino Performance	Raspberry Pi Performance
          * Integer	5.2 DMIPS	875 DMIPS
          * Floating Point	0.089 Linpack MFLOPS	280 Linpack MFLOPS
          * May be worth ofloading some of these calculations to the rpi and let arduino focus on actually
          * moving the needle...
          */

		for(int n = 1; n<4; n++){ // what is the purpose of this? offsetting the mm given?
			value[n] -= 48; // put whatever 48 is in a gantry.hpp as a named constant.
			value[n+4] -= 48;
		}

		x_coord = (value[1]*100)+(value[2]*10)+value[3];
		y_coord = (value[5]*100)+(value[6]*10)+value[7];
		Serial.println(x_coord);
		Serial.println(y_coord);
	}
	else{ // this shouldnt be handled here... but by what is taking in the cmds..
		Serial.write("Invalid packet");
		Serial.flush();
		return(1);
	}
	Serial.flush();
	return(0);

}

/********************************************************************
*Function: move_cap_to_IL
*Purpose:  Moves the capacitive sensor to the insertion coordinate
*Returns:  void
*Inputs:   no input
/********************************************************************/
void move_cap_to_IL(){

	int dir;

	dir = FORWARD;
	move_stepper(X_AXIS, x_coord, dir);
	move_stepper(Y_AXIS, y_coord, dir);
	move_stepper(Z_AXIS, z_coord, dir);

}

/********************************************************************
*Function: position_needle
*Purpose:  Move the needle back in the z and y axes to allow a little
*		   space for the needle to gain momentum before penetrating
*		   the skin/vein.  Also shift x axis over since cap sensor is
*		   to the right of needle.
*Returns:  void
*Inputs:   no input
/********************************************************************/
void position_needle(){

	move_stepper(Z_AXIS, NEEDLE_Z_PROJ, BACKWARD);
	move_stepper(Y_AXIS, NEEDLE_Y_PROJ, BACKWARD);
	move_stepper(X_AXIS, NEEDLE_X_PROJ, FORWARD);
	move_stepper(Z_AXIS, Z_REALIGN, FORWARD);

}

/********************************************************************
*Function: wait_for_error_check
*Purpose:  Waits to receive the coordinate of the tip of the needle.
*		   It then calculates the distance needed to travel to move
*		   to the correct location, and moves the needle to that spot.
*Returns:  0 (tip was off by less than 3mm, no correction needed)
*		   1 (location was off by more than 3mm and they were corrected)
*Inputs:   no input
/********************************************************************/
void wait_for_error_check(){

	int old_x_coord,
		old_y_coord,
		old_z_coord,
		dx, dy, dz, dirx, diry;

	old_x_coord = x_coord;		//store insertion location
	old_y_coord = y_coord;
	old_z_coord = z_coord;

	int m=1;
	while(m != 0){
		m = wait_for_coordinate();	//wait for needle tip coordinate
	}

	dx = old_x_coord - x_coord;		//calculate distance of needle tip to IL
	dy = old_y_coord - y_coord;

	if(dx < 0){						//if dx or dy are negative account to move in opposite direction
		dirx = FORWARD;				//move (+) if they are not negative
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


	if(dx > 3){						//if dx or dy are off by more than 3mm then adjust tip location
		move_stepper(X_AXIS, dx, dirx);
	}
	if(dy > 3){
		move_stepper(Y_AXIS, dy, diry);
	}
}

/********************************************************************
*Function: inject_needle
*Purpose:  Verify that needle is fully actuated back, then stick the
*		   the needle (actuate predefined distance).
*		   void
*Inputs:   no input
/********************************************************************/
void inject_needle(){

	int val;
	//delay(3000);
	val = myservo.read();            // reads the value of the potentiometer (value between 0 and 1023)
	Serial.println("resetting");
	Serial.println(val);
	val = map(val, 0, 1023, 110, 180);     // scale it to use it with the servo (value between 0 and 180)
	Serial.println(val);
	myservo.write(val);                  // sets the servo position according to the scaled value
	delay(3000);                           // waits for the servo to get there
	Serial.println("pushing");
	val = myservo.read();
	Serial.println(val);
	val = map(val, 0, 1023, 30, 180);
	Serial.println(val);
	myservo.write(val);

}

void pull_needle(){

	int val;
	delay(3000);
	val = analogRead(potpin);            // reads the value of the potentiometer (value between 0 and 1023)
	Serial.println("pulling");
	Serial.println(val);
	val = map(val, 0, 1023, 110, 180);     // scale it to use it with the servo (value between 0 and 180)
	Serial.println(val);
	myservo.write(val);                  // sets the servo position according to the scaled value
	//delay(3000);                           // waits for the servo to get there

}
void move_back_from_IL(){	//this will probably only be used for my testing purposes

	int y_dist_travelled = ( MM_TO_Y_HOME + y_coord ) - NEEDLE_Y_PROJ;
	int x_dist_travelled = x_coord + NEEDLE_X_PROJ;
	

	move_stepper(Z_AXIS, z_depth, BACKWARD);			//this is not correct to make z go back home need to account for realignment
	move_stepper(X_AXIS, x_dist_travelled, BACKWARD);
	move_stepper(Y_AXIS, y_dist_travelled, BACKWARD);

}

/********************************************************************
*Function: go_home
*Purpose:  Move all axes back to home location (until limit switches
*		   are activated)
*		   void
*Inputs:   no input
/********************************************************************/
void go_home(){

	while((digitalRead(LIMIT_X_HOME_PIN) != 0)){
		move_stepper(X_AXIS, 10, BACKWARD);
	}
	while((digitalRead(LIMIT_X_HOME_PIN) != 0)){
		move_stepper(Y_AXIS, 10, BACKWARD);
	}
	while((digitalRead(LIMIT_X_HOME_PIN) != 0)){
		move_stepper(Z_AXIS, 10, BACKWARD);
	}
}


/**********************************
 * END OF FUNCTIONS IN ORDER OF EXECUTION
***********************************/

/**********************************
 * HELPER FUNCTIONS
***********************************/

/********************************************************************
*Function: mm_to_steps
*Purpose:  Converts total # mm to travel to steps required to achieve
		   this distance
*Returns:  totalSteps - # steps to send to stepper motors
*Inputs:   axis (X_AXIS, Y_AXIS, Z_AXIS) - axis to move
*		   distance (e.g. 0 to 1000)mm - distance to travel
/********************************************************************/
int mm_to_steps(int axis, double distance){

	int totalSteps;
	int screw_lead_axis;

	if(axis == X_AXIS){
		screw_lead_axis = SCREW_LEAD_X;
	}
	if(axis == Y_AXIS){
		screw_lead_axis = SCREW_LEAD_Y;
	}
	if(axis == Z_AXIS){
		screw_lead_axis = SCREW_LEAD_Z;
	}

	totalSteps = (double)STEPS_PER_REVOLUTION * ( 1 / (double)screw_lead_axis) * ((double)(distance + 1));

	return(totalSteps);
}

/********************************************************************
*Function: select_direction_pin
*Purpose:  Selects the direction to travel
*Returns:  void
*Inputs:   dir (FORWARD, BACKWARD) - direction to travel, see
		   the Chapter 8.1 of PDR for polarity. FORWARD(+),
		   BACKWARD(-)
/********************************************************************/
void select_direction_pin(int dir){

	if(dir == FORWARD){
		digitalWrite(DIR_PIN_X,  HIGH);
		digitalWrite(DIR_PIN_Y, HIGH);
		//digitalWrite(DIR_PIN_Y, HIGH);
		digitalWrite(DIR_PIN_Z,  HIGH);
	}

	if(dir == BACKWARD){
		digitalWrite(DIR_PIN_X,  LOW);
		digitalWrite(DIR_PIN_Y, LOW);
		//digitalWrite(DIR_PIN_Y, LOW);
		digitalWrite(DIR_PIN_Z,  LOW);
	}
}

/********************************************************************
*Function: select_step_pin
*Purpose:  Select which axis to move
*Returns:  stepPin (which axis to move)
*Inputs:   axis (X_AXIS, Y_AXIS, Z_AXIS) - axis to move
/********************************************************************/
int select_step_pin(int axis){

	int stepPin;

	if(axis == X_AXIS){
		stepPin = STEP_PIN_X;
	}
	if(axis == Y_AXIS){
		stepPin = STEP_PIN_Y;
	}
	if(axis == Z_AXIS){
		stepPin = STEP_PIN_Z;
	}
	return(stepPin);
}

/********************************************************************
*Function: move_stepper
*Purpose:  Moves an axis a certain distance in a particular direction
*Returns:  0 (stepper moved successfully)
*		   1	(stepper was disabled)
*Inputs:   axis (X_AXIS, Y_AXIS, Z_AXIS) - axis to move
*		   coordinate_mm (e.g. 0mm to 1000mm) - distance to travel
*		   dir (FORWARD, BACKWARD) - direction to move actuator
/********************************************************************/
int move_stepper(int axis, int coordinate_mm, int dir){

    /*
     * Status msgs
     * Hoping we can get a status msg of where the gantry is. Not every time it moves but at least whenever
     * coordinate_mm % 10 == 0 steps or so
     */
	int i,
		stepPin,
		steps;
		
	steps = mm_to_steps(axis, coordinate_mm);
	if(coordinate_mm == z_depth){
		steps = z_depth;
	}
	select_direction_pin(dir);
	stepPin = select_step_pin(axis);

	if(axis == Z_AXIS  && dir == FORWARD  && z_found == 0){
	    /*
         * Would like a status msg with the z depth found
         */
		z_depth = depth_finder();
	}

	for(i=0; i<steps; i++){
		if(enable != 0){
			return(1);
		}
		digitalWrite(stepPin, HIGH);
		/*if(axis == Y_AXIS){
			digitalWrite(STEP_PIN_Y2, HIGH);
		}*/
		delay(2);
		digitalWrite(stepPin, LOW);
		/*if(axis == Y_AXIS){
			digitalWrite(STEP_PIN_Y2, LOW);
		}*/
		//digitalWrite(STEP_PIN_Y2, LOW);
		delay(2);
		Serial.println(i);
	}
	return(0);
}

/********************************************************************
*Function: depth_finder
*Purpose:  Move z-axis down until capacitive sensor is triggered.
*		   "Debounce" the capacitive sensor to ensure good read.
*Returns:  z_depth (distance (mm) the z-axis travelled
*Inputs:   no input
/********************************************************************/
int depth_finder(){

	int capSamples[10], debounceCap;
	bool capOut;

	capOut = digitalRead (CAP_SENSE_PIN);
		while(capOut == 0){
			if(enable == 0){
			//Serial.println(z_depth);
			capOut = digitalRead(CAP_SENSE_PIN);
			#if HEADLESS
			Serial.println(capOut);
			#endif
			digitalWrite(STEP_PIN_Z, HIGH);
			delay(10);
			z_depth++;
			digitalWrite(STEP_PIN_Z, LOW);
			delay(10);
			}
		}
		for(int n = 0; n<10; n++){
			capSamples[n] = digitalRead(CAP_SENSE_PIN);
			debounceCap += capSamples[n];
			Serial.println("abort");
		}
		if(debounceCap > 7){
			z_found = 1;
			return(z_depth);
		}
	return(0);
}

void send_cmd(int cmd) {
    Serial.write(cmd);
    Serial.println("");
}

void status_msg(const char* msg) {
    Serial.write(CMD_STATUS_MSG);
    Serial.println(msg);
}

/********************************************************************
*Function: process_req
*Purpose:  Process serial requests as they come in from the Pi
*Returns:  Currently 0 unless a reset is requested then 100. This is because it's a bit
*          of a pain to get functions from the ino->these library files, and the reset
*          handler function wouldn't work unless it was defined in the ino :)
*Inputs:   input msg with the command as the first byte
/********************************************************************/
int process_req(const char* msg) {
    int cmd = int(msg[0]);
    int m;
    int *coordinate_result;
    switch(cmd) {
        case REQ_ECHO_MSG:
            status_msg(msg+1); // pass ptr to msg+1 because first byte is cmd byte (this will just echo)
            break;
        case REQ_MOVE_Y_HOME:
            status_msg("Moving Y Home...");
            move_y_home();
            send_cmd(CMD_WAIT_COORDINATE);

            m = wait_for_coordinate();
            break;
        case REQ_WAIT_COORDINATE:
            decode_coordinate(msg+1);
            //move_stepper
        case REQ_MOVE_STEPPER:
            status_msg("Moving stepper...");
            decode_req_move_stepper(msg+1);
            //move_stepper()
            // TODO: splice string from msg
            break;
        case REQ_GO_TO_WORK:
            status_msg("Going to work...");
            move_cap_to_IL();
            while(digitalRead(LIMIT_Y_HOME_PIN) != HIGH); // i dont think this will work because the gantry will never move after it hits this line... need interrupts on limit switches
            position_needle();
            while(digitalRead(LIMIT_Y_HOME_PIN) != HIGH);
            inject_needle();
            while(digitalRead(LIMIT_Y_HOME_PIN) != HIGH);
            pull_needle();
            while(digitalRead(LIMIT_Y_HOME_PIN) != HIGH);
            move_back_from_IL();
            break;
        case REQ_RESET:
            status_msg("Resetting...");
            return 100;
        default:
            status_msg("undefined req!!");
            break;
    }

    return 0;

    //Serial.write(in_cmd);
}

void move_y_back(){

	move_stepper(Y_AXIS, MM_TO_Y_HOME, BACKWARD);
	
}

void decode_coordinate(const char* msg) {
    // For now we will say xxxx xxxx where each group of x is the x then y
    if (strlen(msg) != 9) {
        char output[50];
        sprintf(output, "Invalid coordinate. You passed size: %d", strlen(msg));
        status_msg(output);
        return;
    }
    char x[5];
    char y[5];

    memcpy( x, msg, 4 ); // read first 4 chars
    x[4] = '\0';
    memcpy( y, msg+4, 4 ); // read last 4 chars
    y[4] = '\0';

    int result[2];
    result[0] = atoi(x);
    result[1] = atoi(y);
	
	char output[50];
    sprintf(output, "x: %d y: %d\n", result[0], result[1]);
    status_msg(output);
}
/**********************************
 * END HELPER FUNCTIONS
***********************************/

/**********************************
 * UNUSED FUNCTIONS
***********************************/
