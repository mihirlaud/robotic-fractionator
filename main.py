from time import sleep, time
from math import floor
from adafruit_motorkit import MotorKit
from adafruit_motor import stepper
from gpiozero import LED
import tkinter as tk
import json

NEMA_17_STEPS_PER_DEGREE = 3200.0 / 360.0
LEAD_SCREW_PITCH_IN_CM = 4.0

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
		
	def set(self, text):
		self.entry.delete(0, tk.END)
		self.entry.insert(0, text)
		
	def grid_forget(self):
		self.label.grid_forget()
		self.entry.grid_forget()
		
class App(tk.Tk):
	def __init__(self):
		super().__init__()
		self.title("Robotic Fractionator GUI v0.1")
		
		self.mode = "Automated"
		self.mode_btn = tk.Button(self, text="Mode: Automated", command=self.cycle_mode)
		self.mode_btn.grid(row=0, column=0, columnspan=3, sticky="we")
		
		self.set_mode_automated(True)
	
	def cycle_mode(self):
		if self.mode == "Automated":
			self.mode = "Manual"
			self.set_mode_manual()
		elif self.mode == "Manual":
			self.mode = "Cleaning"
			self.set_mode_cleaning()
		elif self.mode == "Cleaning":
			self.mode = "Automated"
			self.set_mode_automated(False)
		
		self.mode_btn["text"] = "Mode: " + self.mode
		
	def set_mode_automated(self, first):
		if not first:
			self.carriage_lbl.grid_forget()
			self.carriage_entry.grid_forget()
			self.movement_btn.grid_forget()
			self.pump_btn.grid_forget()
			self.progress_lbl.grid_forget()
		else:
			self.step_lbl = tk.Label(text="")
			self.step_forwards_btn = tk.Button(self, text="", command=lambda: self.manual_step(True))
			self.step_backwards_btn = tk.Button(self, text="", command=lambda: self.manual_step(False))
		
		self.json_lbl = tk.Label(text="Load well plate file: ")
		self.json_lbl.grid(row=1, column=0, columnspan=1)
		self.json_entry = tk.Entry(self)
		self.json_entry.grid(row=1, column=1, columnspan=1)
		
		self.json_btn = tk.Button(self, text="Load", command=self.load_json)
		self.json_btn.grid(row=1, column=2, columnspan=1, sticky="we")
		
		self.rows_text_entry = TextEntry(self, "Enter # of rows:", 2)
		self.cols_text_entry = TextEntry(self, "Enter # of columns:", 3)
		self.ws_text_entry = TextEntry(self, "Enter well size in cm:", 4)
		self.pump_rate_text_entry = TextEntry(self, "Enter pump rate in cc/hr:", 5)
		self.vol_text_entry = TextEntry(self, "Enter desired volume in cc:", 6)
		
		self.table_lbl = tk.Label(text="Move table to: ")
		self.table_lbl.grid(row=7, column=0, columnspan=1)
		self.carriage_lbl = tk.Label(text="Move carriage to: ")
		self.carriage_lbl.grid(row=8, column=0, columnspan=1)
		self.table_entry = tk.Entry(self)
		self.table_entry.grid(row=7, column=1, columnspan=1)
		self.carriage_entry = tk.Entry(self)
		self.carriage_entry.grid(row=8, column=1, columnspan=1)
		
		self.movement_btn = tk.Button(self, text="Move", command=self.set_table_carriage)
		self.movement_btn.grid(row=7, column=2, columnspan=1, rowspan=2, sticky="we")
		
		for i in range(3):
			self.grid_columnconfigure(i, weight=1, uniform="a")
			
		self.pump_btn = tk.Button(self, text="Toggle pump", command=self.toggle_pump)
		self.pump_btn.grid(row=9, column=0, columnspan=3, sticky="we")
		
		self.btn = tk.Button(self, text="Begin fractionation", command=self.run_checks)
		self.btn.grid(row=10, column=0, columnspan=3, sticky="we")
		
		self.pause_btn =tk.Button(self, text="Click to pause", command = self.toggle_pause)
		self.pause_btn.grid(row=11, column=0,columnspan=3, sticky="we")
		self.is_paused = False
			
		self.progress_lbl = tk.Label(text="System idle.")
		self.progress_lbl.grid(row=12, column=0, columnspan=3, sticky="we")

		self.canvas = tk.Canvas(self, width=500, height=300, bd=0, highlightthickness=0)
		self.canvas.grid(row = 13, column = 0, columnspan=3)
			
		self.table_motor = StepperMotor(2, NEMA_17_STEPS_PER_DEGREE, LEAD_SCREW_PITCH_IN_CM, True)
		self.carriage_motor = StepperMotor(1, NEMA_17_STEPS_PER_DEGREE, LEAD_SCREW_PITCH_IN_CM, True)
		
		if first:
			self.pump = LED("5")
		
		self.table_motor.move_dist_relative(-0.1)
		self.carriage_motor.move_dist_relative(-0.1)
		self.pump_is_on = False
		
		self.ROWS = 0
		self.COLS = 0
		self.well_size = 0
		self.pump_time = 0.0
		
		self.taskId = None
		self.state = "idle"
		
		self.x = 0
		self.y = 0
		self.carriage_forwards = True
		
	def set_mode_manual(self):
		self.json_lbl.grid_forget()
		self.json_entry.grid_forget()
		self.json_btn.grid_forget()
		self.rows_text_entry.grid_forget()
		self.cols_text_entry.grid_forget()
		self.ws_text_entry.grid_forget()
		self.pump_rate_text_entry.grid_forget()
		self.vol_text_entry.grid_forget()
		self.table_lbl.grid_forget()
		self.table_entry.grid_forget()
		self.pump_btn.grid_forget()
		self.btn.grid_forget()
		self.pause_btn.grid_forget()
		self.progress_lbl.grid_forget()
		self.canvas.grid_forget()
		self.carriage_lbl.grid_forget()
		self.carriage_entry.grid_forget()
		self.movement_btn.grid_forget()
		
		
		self.rows_text_entry = TextEntry(self, "Enter # of rows:", 1)
		self.cols_text_entry = TextEntry(self, "Enter # of columns:", 2)
		self.ws_text_entry = TextEntry(self, "Enter well size in cm:", 3)
		
		self.table_lbl = tk.Label(text="Move table to: ")
		self.table_lbl.grid(row=4, column=0, columnspan=1)
		self.carriage_lbl = tk.Label(text="Move carriage to: ")
		self.carriage_lbl.grid(row=5, column=0, columnspan=1)
		self.table_entry = tk.Entry(self)
		self.table_entry.grid(row=4, column=1, columnspan=1)
		self.carriage_entry = tk.Entry(self)
		self.carriage_entry.grid(row=5, column=1, columnspan=1)
		
		self.movement_btn = tk.Button(self, text="Move", command=self.set_table_carriage)
		self.movement_btn.grid(row=4, column=2, columnspan=1, rowspan=2, sticky="we")
		
		self.step_lbl = tk.Label(text="Move the needle one step:")
		self.step_lbl.grid(row=6, column=0, columnspan=1, sticky="we")
		self.step_forwards_btn = tk.Button(self, text="Forwards", command=lambda: self.manual_step(True))
		self.step_forwards_btn.grid(row=6, column=1, columnspan=1, sticky="we")
		self.step_backwards_btn = tk.Button(self, text="Backwards", command=lambda: self.manual_step(False))
		self.step_backwards_btn.grid(row=6, column=2, columnspan=1, sticky="we")
		
		for i in range(3):
			self.grid_columnconfigure(i, weight=1, uniform="a")
			
		self.pump_btn = tk.Button(self, text="Toggle pump", command=self.toggle_pump)
		self.pump_btn.grid(row=7, column=0, columnspan=3, sticky="we")
		
		self.canvas = tk.Canvas(self, width=500, height=300, bd=0, highlightthickness=0)
		self.canvas.grid(row = 8, column = 0, columnspan=3)
		
		self.ROWS = 0
		self.COLS = 0
		self.well_size = 0
		
		self.x = 0
		self.y = 0
		self.carriage_forwards = True
		
		
	def set_mode_cleaning(self):
		self.rows_text_entry.grid_forget()
		self.cols_text_entry.grid_forget()
		self.ws_text_entry.grid_forget()
		self.pump_btn.grid_forget()
		self.canvas.grid_forget()
		self.movement_btn.grid_forget()
		self.step_lbl.grid_forget()
		self.step_forwards_btn.grid_forget()
		self.step_backwards_btn.grid_forget()
		
		self.carriage_lbl = tk.Label(text="Move carriage to: ")
		self.carriage_lbl.grid(row=1, column=0, columnspan=1)
		self.carriage_entry = tk.Entry(self)
		self.carriage_entry.grid(row=1, column=1, columnspan=1)
		self.carriage_entry.delete(0, tk.END)
		self.carriage_entry.insert(0, "14.0")
		
		self.movement_btn = tk.Button(self, text="Move", command=self.set_table_carriage)
		self.movement_btn.grid(row=1, column=2, columnspan=1, sticky="we")
		
		for i in range(3):
			self.grid_columnconfigure(i, weight=1, uniform="a")
			
		self.pump_btn = tk.Button(self, text="Toggle pump", command=self.toggle_pump)
		self.pump_btn.grid(row=2, column=0, columnspan=3, sticky="we")
			
		self.progress_lbl = tk.Label(text="System idle.")
		self.progress_lbl.grid(row=3, column=0, columnspan=3, sticky="we")
		
		self.table_motor.move_dist_relative(-0.1)
		self.carriage_motor.move_dist_relative(-0.1)
		self.pump_is_on = False
		self.carriage_forwards = True
			
	def load_json(self):
		json_spec = open(self.json_entry.get())
		data = json.load(json_spec)
	
		r = len(data["ordering"][0])
		c = len(data["ordering"])
	
		self.rows_text_entry.set(str(r))
		self.cols_text_entry.set(str(c))
		self.ws_text_entry.set(str(abs(data["wells"]["A1"]["y"] - data["wells"]["B1"]["y"]) / 10.0))
	
		self.table_entry.delete(0, tk.END)
		self.table_entry.insert(0, str(15 - data["wells"]["A1"]["x"] * 0.1))

		self.carriage_entry.delete(0, tk.END)
		self.carriage_entry.insert(0, str(0.1 * (data["dimensions"]["yDimension"] - data["wells"]["A1"]["y"]) - 0.5))
	
	def set_table_carriage(self):
		
		if self.table_entry.get() != '':
			self.table_motor.move_dist_absolute(float(self.table_entry.get()))
		
		if self.carriage_entry.get() != '':
			self.carriage_motor.move_dist_absolute(float(self.carriage_entry.get()))
		
	def toggle_pump(self):
	
		self.pump_is_on = not self.pump_is_on
		if self.pump_is_on:
			self.pump.on()
			if self.mode == "Cleaning":
				self.progress_lbl["text"] = "System cleaning."
		else:
			self.pump.off()
			if self.mode == "Cleaning":
				self.progress_lbl["text"] = "System idle."
			
	def toggle_pause(self):
		self.is_paused = not self.is_paused
		
		if self.is_paused:
			if self.taskId is not None:
				self.after_cancel(self.taskId)
				self.pump.off()
			self.pause_btn["text"] = "Click to unpause"
			self.progress_lbl["text"] = "Fractionation paused..."
		else:
			self.pause_btn["text"] = "Click to pause"
			self.progress_lbl["text"] = "Fractionation in progress..."
			
			if self.state == "pump":
				self.stop_pump()
			elif self.state == "wait":
				self.move()
			elif self.state == "move":
				self.pump()
				
			
	def run_checks(self):
	
		self.ROWS = int(self.rows_text_entry.get())
		self.COLS = int(self.cols_text_entry.get())
		self.well_size = float(self.ws_text_entry.get())
	
		self.pump_time = float(self.vol_text_entry.get()) / (float(self.pump_rate_text_entry.get()) / 3600)
	
		if self.ROWS != 0 and self.COLS != 0 and self.well_size != 0 and self.pump_time != 0:
			self.movement()
			
	def movement(self):
		self.canvas.create_rectangle(0, 0, self.COLS * 25 + 5, self.ROWS * 25 + 5, fill="black")
		self.update()
	
		self.carriage_forwards = True
	
		self.progress_lbl["text"] = "Fractionation in progress..."
		
		self.x = 0
		self.y = 0
		
		self.pump_liquid()
		
	def move(self):
		self.state = "move"
		if self.carriage_forwards:
			self.y = self.y + 1
			if self.y < self.ROWS:
				self.carriage_motor.move_dist_relative(self.well_size)
			else:
				self.y = self.ROWS - 1
				self.table_motor.move_dist_relative(-self.well_size)
				self.x = self.x + 1
				self.carriage_forwards = not self.carriage_forwards
		else:
			self.y = self.y - 1
			if self.y >= 0:
				self.carriage_motor.move_dist_relative(-self.well_size)
			else:
				self.y = 0
				self.table_motor.move_dist_relative(-self.well_size)
				self.x = self.x + 1
				self.carriage_forwards = not self.carriage_forwards
			
		if self.is_paused:
			return
		
		if self.x == self.COLS:
			self.progress_lbl["text"] = "Fractionation finished!"
			self.carriage_return()
		else:
			self.pump_liquid()
		
	def pump_liquid(self):
		self.state = "pump"
		self.pump.on()
		x1, x2 = 5 + 25 * self.x, 25 + 25 * self.x
		y1, y2 = 5 + 25 * self.y, 25 + 25 * self.y
		self.canvas.create_rectangle(x1, y1, x2, y2, fill="green")
		self.taskId = self.after(round(self.pump_time * 1000), self.stop_pump)
	
	def stop_pump(self):
		self.state = "wait"
		self.pump.off()
		x1, x2 = 5 + 25 * self.x, 25 + 25 * self.x
		y1, y2 = 5 + 25 * self.y, 25 + 25 * self.y
		self.canvas.create_rectangle(x1, y1, x2, y2, fill="blue")
		self.taskId = self.after(round(self.pump_time * 1000), self.move)
		
	def carriage_return(self):
		self.table_motor.move_dist_absolute(0.0)
		self.carriage_motor.move_dist_absolute(0.0)
		
	def manual_step(self, forwards):
		
		self.ROWS = int(self.rows_text_entry.get())
		self.COLS = int(self.cols_text_entry.get())
		self.well_size = float(self.ws_text_entry.get())
		
		self.canvas.create_rectangle(0, 0, self.COLS * 25 + 5, self.ROWS * 25 + 5, fill="black")
		for i in range(0, self.COLS):
			for j in range(0, self.ROWS):
				x1, x2 = 5 + 25 * i, 25 + 25 * i
				y1, y2 = 5 + 25 * j, 25 + 25 * j
				self.canvas.create_rectangle(x1, y1, x2, y2, fill="gray")
		
		if self.ROWS == 0 or self.COLS == 0 or self.well_size == 0:
			return
		
		if forwards:
			if self.x == self.COLS - 1 and self.y == (self.ROWS - 1 if self.COLS % 2 == 1 else 0):
				x1, x2 = 5 + 25 * self.x, 25 + 25 * self.x
				y1, y2 = 5 + 25 * self.y, 25 + 25 * self.y
				self.canvas.create_rectangle(x1, y1, x2, y2, fill="yellow")
		
				self.update()
				return
			if self.carriage_forwards:
				self.y = self.y + 1
				if self.y < self.ROWS:
					self.carriage_motor.move_dist_relative(self.well_size)
				else:
					self.y = self.ROWS - 1
					self.table_motor.move_dist_relative(-self.well_size)
					self.x = self.x + 1
					self.carriage_forwards = not self.carriage_forwards
			else:
				self.y = self.y - 1
				if self.y >= 0:
					self.carriage_motor.move_dist_relative(-self.well_size)
				else:
					self.y = 0
					self.table_motor.move_dist_relative(-self.well_size)
					self.x = self.x + 1
					self.carriage_forwards = not self.carriage_forwards
		else:
			if self.x == 0 and self.y == 0:
				x1, x2 = 5 + 25 * self.x, 25 + 25 * self.x
				y1, y2 = 5 + 25 * self.y, 25 + 25 * self.y
				self.canvas.create_rectangle(x1, y1, x2, y2, fill="yellow")
		
				self.update()
				return
			if self.carriage_forwards:
				self.y = self.y - 1
				if self.y >= 0:
					self.carriage_motor.move_dist_relative(-self.well_size)
				else:
					self.y = 0
					self.table_motor.move_dist_relative(self.well_size)
					self.x = self.x - 1
					self.carriage_forwards = not self.carriage_forwards
			else:
				self.y = self.y + 1
				if self.y < self.ROWS:
					self.carriage_motor.move_dist_relative(self.well_size)
				else:
					self.y = self.ROWS - 1
					self.table_motor.move_dist_relative(self.well_size)
					self.x = self.x - 1
					self.carriage_forwards = not self.carriage_forwards
		
		x1, x2 = 5 + 25 * self.x, 25 + 25 * self.x
		y1, y2 = 5 + 25 * self.y, 25 + 25 * self.y
		self.canvas.create_rectangle(x1, y1, x2, y2, fill="yellow")
		
		self.update()


app = App()

app.mainloop()

app.table_motor.release()
app.carriage_motor.release()
