#include <Arduino.h>

#define SCREW_LEAD_X	2
#define SCREW_LEAD_Y	8
#define SCREW_LEAD_Z	8
#define STEPS_PER_REVOLUTION	200
#define MM_TO_Y_HOME	126
#define NEEDLE_Z_PROJ	4.29
#define	NEEDLE_Y_PROJ	9.22
#define NEEDLE_X_PROJ	21.5
#define SERVO_BEGIN		0
#define SERVO_INJECT_DIST 100
#define X_AXIS	0
#define Y_AXIS	1
#define Z_AXIS	2
#define FORWARD 0
#define BACKWARD 1
#define STEP_PIN_X 49
#define STEP_PIN_Y1 53
#define STEP_PIN_Y2 52
#define STEP_PIN_Z 46
#define DIR_PIN_X 48
#define DIR_PIN_Y1 51
#define DIR_PIN_Y2 50
#define DIR_PIN_Z 47
#define CAP_SENSE_PIN	30
#define SERVO_PIN	A0
#define LIMIT_Y_HOME_PIN 2
#define LIMIT_X_HOME_PIN 21
#define LIMIT_Z_HOME_PIN 22
#define potpin A2  // analog pin used to connect the potentiometer

#define HEADLESS 0 // where we just go through a basic series of operations with no cmds expected from pi

// Requests from Pi
#define REQ_ECHO_MSG (int) '0'
#define REQ_POSITION_UPDATE (int) '1'
#define REQ_MOVE_Y_HOME (int) '2'
#define REQ_MOVE_STEPPER (int) '3'
#define REQ_GO_TO_WORK (int) '4' // after pi gives coordinate pi tells to go ahead...
#define REQ_RESET (int) '9'

// Commands to Pi
#define CMD_STATUS_MSG (int) '0'
#define CMD_GANTRY_INITIALIZED (int) '1'
#define CMD_POSITION_UPDATE (int) '2'
#define CMD_WAIT_COORDINATE (int) '8'
#define CMD_FINISH (int) '9'

/*extern volatile int x_coord;
extern volatile int y_coord;
extern volatile int z_coord;*/

int 	mm_to_steps(int axis, double distance);
void 	select_direction_pin(int dir);
int 	select_step_pin(int axis);
void 	gantry_init();
int 	move_stepper(int axis, int coordinate_mm, int dir);
void 	move_y_home();
int 	wait_for_coordinate();
void 	move_cap_to_IL();
void 	wait_for_error_check();
int		depth_finder();
void 	position_needle();
void 	inject_needle();
void	go_home();
void 	move_y_back();
void    move_back_from_IL();
void	pull_needle();

void    decode_req_move_stepper(char* msg);
void    send_cmd(int cmd);
void    status_msg(const char* msg);
int     process_req(const char* in_cmd);