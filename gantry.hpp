#define SCREW_LEAD_X	2
#define SCREW_LEAD_Y	8
#define SCREW_LEAD_Z	8
#define STEPS_PER_REVOLUTION	200
#define STEPS_TO_Y_HOME	1250
#define NEEDLE_Z_PROJ	10
#define	NEEDLE_Y_PROJ	10
#define NEEDLE_X_PROJ	20
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
#define STEP_PIN_Z 32
#define DIR_PIN_X 48
#define DIR_PIN_Y1 51
#define DIR_PIN_Y2 50
#define DIR_PIN_Z 34
#define CAP_SENSE_PIN	36
#define SERVO_PIN	A0
#define LIMIT_Y_HOME_PIN 20
#define LIMIT_X_HOME_PIN 21
#define LIMIT_Z_HOME_PIN 22

// Command Bytes
#define CMD_WAIT_COORDINATE (int) '8'
#define CMD_FINISH (int) '9'

/*extern volatile int x_coord;
extern volatile int y_coord;
extern volatile int z_coord;*/

void 	gantry_init();
void 	move_y_home();
int 	wait_for_coordinate();
void 	move_cap_to_IL();
void 	position_needle();
void 	wait_for_error_check();
void 	inject_needle();
void	go_home();

int 	mm_to_steps(int axis, double distance);
void 	select_direction_pin(int dir);
int 	select_step_pin(int axis);
int 	move_stepper(int axis, int coordinate_mm, int dir);
int		depth_finder();
