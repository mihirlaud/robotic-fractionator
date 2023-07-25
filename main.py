from time import sleep, time
from math import floor
from adafruit_motorkit import MotorKit
from adafruit_motor import stepper
from gpiozero import LED
import tkinter as tk

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
		
class TextEntry:
	def __init__(self, window, text, row):
		self.label = tk.Label(text=text)
		self.label.grid(row=row, column=0, columnspan=1)
		self.var = tk.StringVar()
		self.entry = tk.Entry(window, textvariable=self.var)
		self.entry.grid(row=row, column=1, columnspan=2, sticky="we")
	
	def get(self):
		return self.var.get()

NEMA_17_STEPS_PER_DEGREE = 3200.0 / 360.0
LEAD_SCREW_PITCH_IN_CM = 4.0

table_motor = StepperMotor(2, NEMA_17_STEPS_PER_DEGREE, LEAD_SCREW_PITCH_IN_CM, True)
carriage_motor = StepperMotor(1, NEMA_17_STEPS_PER_DEGREE, LEAD_SCREW_PITCH_IN_CM, True)
pump = LED("5")

ROWS = 0
COLS = 0
well_size = 0
pump_time = 0.0

window = tk.Tk()
window.title("Robotic Fractionator GUI v0.1")
#window.geometry("800x600")

rows_text_entry = TextEntry(window, "Enter # of rows:", 0)
cols_text_entry = TextEntry(window, "Enter # of columns:", 1)
ws_text_entry = TextEntry(window, "Enter well size in cm:", 2)
pump_rate_text_entry = TextEntry(window, "Enter pump rate in cc/hr:", 3)
vol_text_entry = TextEntry(window, "Enter desired volume in cc:", 4)

tk.Label(text="Move table to: ").grid(row=5, column=0, columnspan=1)
tk.Label(text="Move carriage to: ").grid(row=6, column=0, columnspan=1)
table_entry = tk.Entry(window)
table_entry.grid(row=5, column=1, columnspan=1)
carriage_entry = tk.Entry(window)
carriage_entry.grid(row=6, column=1, columnspan=1)

for i in range(3):
	window.grid_columnconfigure(i, weight=1, uniform="a")

def set_table_carriage():
	table_motor.move_dist_absolute(float(table_entry.get()))
	carriage_motor.move_dist_absolute(float(carriage_entry.get()))

table_motor.move_dist_relative(-0.1)
carriage_motor.move_dist_relative(-0.1)

movement_btn = tk.Button(window, text="Move", command=set_table_carriage)
movement_btn.grid(row=5, column=2, columnspan=1, rowspan=2, sticky="we")

canvas = tk.Canvas(window, width=500, height=300, bd=0, highlightthickness=0)
canvas.grid(row = 10, column = 0, columnspan=3)

pump_is_on = False
def toggle_pump():
	global pump_is_on
	
	pump_is_on = not pump_is_on
	if pump_is_on:
		pump.on()
	else:
		pump.off()
		
pump_btn = tk.Button(window, text="Toggle pump", command=toggle_pump)
pump_btn.grid(row=7, column=0, columnspan=3, sticky="we")

progress_lbl = tk.Label(text="System idle.")
progress_lbl.grid(row=9, column=0, columnspan=3, sticky="we")

def run_checks():
	global ROWS, COLS, well_size, pump_time
	
	ROWS = int(rows_text_entry.get())
	COLS = int(cols_text_entry.get())
	well_size = float(ws_text_entry.get())
	
	pump_time = float(vol_text_entry.get()) / (float(pump_rate_text_entry.get()) / 3600)
	
	if ROWS != 0 and COLS != 0 and well_size != 0 and pump_time != 0:
		movement()

def movement():
	global canvas, progress_lbl
	
	canvas.create_rectangle(0, 0, COLS * 25 + 5, ROWS * 25 + 5, fill="black")
	window.update()
	
	table_motor.tare()
	carriage_motor.tare()
	
	carriage_forwards = True
	
	progress_lbl["text"] = "Fractionation in progress..."
	
	for n in range(0, COLS):
		for m in range(0, ROWS):
			if m > 0:
				carriage_motor.move_dist_relative(well_size * (1 if carriage_forwards else -1))
			x1, x2 = 5 + 25 * n, 25 + 25 * n
			y_pos = m if carriage_forwards else ROWS - 1 - m
			y1, y2 = 5 + 25 * y_pos, 25 + 25 * y_pos
			
			pump.on()
			canvas.create_rectangle(x1, y1, x2, y2, fill="green")
			window.update()
			sleep(pump_time)
			pump.off()
			canvas.create_rectangle(x1, y1, x2, y2, fill="blue")
			window.update()
			sleep(pump_time)
		table_motor.move_dist_relative(-well_size)
		sleep(1)
		carriage_forwards = not carriage_forwards
	
	progress_lbl["text"] = "Fractionation finished!"

btn = tk.Button(window, text="Begin fractionation", command=run_checks)
btn.grid(row=8, column=0, columnspan=3, sticky="we")

window.mainloop()

table_motor.release()
carriage_motor.release()
