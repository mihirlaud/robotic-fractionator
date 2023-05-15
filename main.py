from time import sleep
from math import floor
from adafruit_motorkit import MotorKit
from adafruit_motor import stepper

"""
StepperMotor Class

Used to keep track of stepper motor states. All angles in degrees
"""

class StepperMotor:
	def __init__(self, index, steps_per_degree):
		kit = MotorKit()
		
		self.motor = kit.stepper2 if index == 2 else kit.stepper1
		self.angle = 0.0
		self.steps_per_degree = steps_per_degree
	
	def get_angle(self):
		return self.angle
		
	def tare(self):
		self.angle = 0.0
	
	def move_relative(self, angle):
		steps_needed = floor(self.steps_per_degree * angle)
		
		direction = stepper.FORWARD if angle > 0 else stepper.BACKWARD
		
		for _ in range(0, steps_needed):
			self.motor.onestep(direction=direction, style=stepper.SINGLE)
			sleep(0.01)
	
		self.angle = self.angle + steps_needed / self.steps_per_degree

	def move_absolute(self, angle):
		delta_angle = angle - self.angle
		
		self.move_relative(delta_angle)

NEMA_17_STEPS_PER_DEGREE = 200.0 / 360.0

motor1 = StepperMotor(1, NEMA_17_STEPS_PER_DEGREE)
motor2 = StepperMotor(2, NEMA_17_STEPS_PER_DEGREE)

i = 1
while(True):
	print("Round", i)
	i += 1
	
	motor1.move_relative(90)
	sleep(1)
	
	if motor1.get_angle() == 360:
		motor1.tare()
		
	
	motor2.move_absolute(motor1.get_angle())
	sleep(1)
