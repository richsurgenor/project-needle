#define SCREW_LEAD_X	2
#define SCREW_LEAD_Y	8
#define SCREW_LEAD_Z	8
#define STEPS_PER_REVOLUTION	200
#define STEPS_TO_Y_HOME	1250
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

/*extern volatile int x_coord;
extern volatile int y_coord;
extern volatile int z_coord;*/

int 	mm_to_steps(int axis, double distance);
void 	select_direction_pin(int dir);
int 	select_step_pin(int axis);
void 	gantry_init();
void 	move_stepper(int axis, int coordinate_mm, int dir);
void 	move_y_home();
int 	wait_for_coordinate();
void 	move_xyz_to_IL();
int 	wait_for_error_check();
int		depth_finder();