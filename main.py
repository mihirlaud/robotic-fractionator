from time import sleep, time
from math import floor
from adafruit_motorkit import MotorKit
from adafruit_motor import stepper
from gpiozero import LED

"""
StepperMotor Class

Used to keep track of stepper motor states. All angles in degrees
"""

class StepperMotor:
	def __init__(self, index, steps_per_degree, lead_screw_pitch, reverse=False):
		kit = MotorKit()
		
		self.motor = kit.stepper2 if index == 2 else kit.stepper1
		self.angle = 0.0
		self.steps_per_degree = steps_per_degree
		self.cm_per_deg = lead_screw_pitch / 360.0
		self.reverse = reverse
		self.forwards = True
	
	def get_angle(self):
		return self.angle
		
	def tare(self):
		self.angle = 0.0
		
	def release(self):
		self.motor.release()
	
	def move_relative(self, angle):
		backlash = 0.3 / self.cm_per_deg
		
		if self.forwards and angle < 0:
			angle -= backlash
			self.forwards = False
		elif not self.forwards and angle > 0:
			angle += backlash
			self.forwards = True
		
		steps_needed = floor(self.steps_per_degree * angle)
		
		# FORWARD if positive angle and not reversed or if negative angle and reversed
		
		direction = stepper.FORWARD if (angle > 0 and not self.reverse) or (angle < 0 and self.reverse) else stepper.BACKWARD
		
		for _ in range(0, abs(steps_needed)):
			self.motor.onestep(direction=direction, style=stepper.MICROSTEP)
			sleep(0.0001)
	
		self.angle = self.angle + steps_needed / self.steps_per_degree
		
		self.release()

	def move_absolute(self, angle):
		delta_angle = angle - self.angle
		self.move_relative(delta_angle)
	
	def move_dist_relative(self, dist):
		self.move_relative(dist / self.cm_per_deg)
		
	def move_dist_absolute(self, dist):
		self.move_absolute(dist / self.cm_per_deg)

NEMA_17_STEPS_PER_DEGREE = 3200.0 / 360.0
LEAD_SCREW_PITCH_IN_CM = 4.0

table_motor = StepperMotor(2, NEMA_17_STEPS_PER_DEGREE, LEAD_SCREW_PITCH_IN_CM, True)
carriage_motor = StepperMotor(1, NEMA_17_STEPS_PER_DEGREE, LEAD_SCREW_PITCH_IN_CM, True)
pump = LED("5")

ROWS = 0
COLS = 0
well_size = 0
pump_time = 0.0

def calibrate():
	global ROWS, COLS, well_size, pump_time
	
	ROWS = int(input("Enter number of rows: "))
	COLS = int(input("Enter number of columns: "))
	well_size = float(input("Enter well size in cm: "))
	print("---------------------------------------------------------------------")
	print("Use the following prompts to center the tubing above the first well.")
	print("This will be the closest to the stepper motors. Enter distances in")
	print("cm until the tubing is centered. Positive distance indicates motion")
	print("away from the motor, negative indicates motion towards. When you")
	print("are done, enter a number greater than 17 or less than -17 to exit.\n")
	
	dist = -0.1
	while -17 <= dist <= 17:
		table_motor.move_dist_relative(dist)
		dist = float(input("How much should the table move? "))
	table_motor.tare()
	
	print()
	
	dist = -0.1
	while -17 <= dist <= 17:
		carriage_motor.move_dist_relative(dist)
		dist = float(input("How much should the carriage move? "))
	carriage_motor.tare()
	
	print("\nThe pump will now be turned on for calibration. Press enter to turn")
	print("it on, and press enter immediately after a single drop falls out of")
	print("the tubing.\n")
	
	input("Press enter to start the pump.")
	pump.on()
	input("Press enter to stop the pump.")
	pump.off()
	
	pump_speed = float(input("\nEnter the pump rate in cc/hr: "))
	desired_volume = float(input("Enter the desired volume in cc: "))
	
	pump_time = desired_volume / (pump_speed / 3600.0)
	
	print("\nPump time:", pump_time)
	
	print("---------------------------------------------------------------------")
	response = "n"
	while response != "y" and response != "Y":
		response = str(input("Begin fractionation ? [Y/N]"))

def movement():
	
	print("Beginning movement...")
	
	carriage_forwards = True
	
	for n in range(0, COLS):
		for m in range(0, ROWS):
			print("Moving to (" + str(n) + ", " + str(m) + ")")
			if m > 0:
				carriage_motor.move_dist_relative(well_size * (1 if carriage_forwards else -1))
			pump.on()
			sleep(pump_time)
			pump.off()
			sleep(pump_time)
		print("Moving to (" + str(n) + ", 0)")
		table_motor.move_dist_relative(-well_size)
		sleep(1)
		carriage_forwards = not carriage_forwards
	
	print("Fractionation finished!")

calibrate()
movement()

table_motor.release()
carriage_motor.release()
