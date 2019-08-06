#!/usr/bin/python
# -*- coding: utf-8 -*-

import io         # used to create file streams
from io import open
import fcntl      # used to access I2C parameters like addresses
import serial     # for CO2 serial connection
from sht_sensor import Sht

import time       # used for sleep delay and timestamps
import string     # helps parse strings

import RPi.GPIO as GPIO

import Tkinter as tk
from Tkinter import *
import ttk
import threading
import tkMessageBox

import matplotlib
matplotlib.use('TkAgg')

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure

import numpy as np

#from toggle import Toggle


#----Initialization----#
sht75_datagpio=27
sht75_clkgpio=17

GPIO.setup(sht75_datagpio,GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(sht75_clkgpio,GPIO.OUT, initial=GPIO.LOW)
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(6,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(11,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(9,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(10,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
i2c_list = [99,100,102] #99 is pH, 100 is EC, 102 is Temp
ser = serial.Serial("/dev/serial0",bytesize=8,baudrate =9600,timeout = .5) #serial connection for CO2

pH_addr, EC_addr, temp_addr = i2c_list


#----PhSettings defines an interface for calibrating the pH probe----#
class PHSettings(ttk.Frame):
    
    #TODO:
    #Account for temperature in calibration
    def __init__(self, *args, **kwargs):
        self.low = IntVar()
        self.mid = IntVar()
        #self.high = IntVar()
        self.low.set(0)
        self.mid.set(0)
        
        self.levels = [("Mid",self.mid), ("Low",self.low)] #, ("High",self.high)]
        #commented out high for 2 point calibration
        #mid should be calibrated first, then low, then high

    #----run_cal is called from calib_sett to query the pH probe based on user entered pH values----#
    def run_cal(self, win):
        #need to do mid, then low, then high
        device.set_i2c_address(pH_addr) #check that we are communicating with pH (99) and not EC (100)
        device.query("Cal, clear") #clear previous calibration settings
        global Temp_value
        if(Temp_value > 27 or Temp_value < 23): #if solution temp is more than 2 degrees from 25C
            cal = "T,{}".format(Temp_value.get()) #send query to adjust calibration
            device.query(cal)
        for level in self.levels:
            cal = "Cal, " + str(level[0]) + ", " + str(level[1].get()) #e.g. "Cal, low, 3"
            tkMessageBox.showinfo("{} Calibration".format(str(level[0])),"Place probe in pH {} solution".format(str(level[1].get()))) #popup box for each calibration level
            root.update()
            time.sleep(10)
            device.query(cal)

        #TODO:countdown clock to wait a minute for stabilization after placing in solution?
        #OR display readings and tell user to wait until they are stable to press "ok"

    #----calib_sett is called from __init__ in the AtlasI2C class----#
    #----Creates interface requesting calibration values from the user----#
    def calib_sett(self):
        win = tk.Toplevel()
        win.wm_title("PH Calibration")
        entries = [self.low, self.mid]
        fields = "Enter Low pH Value: ", "Enter Mid pH Value: "#, "Enter High pH Value: "
        x=0
        for field in fields: #create entry form
            lab = tk.Label(win, width=20, text=field, anchor='w')
            ent = tk.Entry(win, textvariable=entries[x])
            x+=1
            lab.grid(sticky=W)
            ent.grid(sticky=E)

        b = tk.Button(win, text="Run Calibration", command=lambda: self.run_cal(win)) #send values to run_cal
        b.grid(row=9, column = 0)


#----ECSettings defines an interface for calibrating the EC probe----#
#----Also allows users to specify which parameters (EC, TDS, Salinity, Specific Gravity) they want to see----#
class ECSettings(ttk.Frame):
    #TODO:
    #booleans or 1/0 for conductivity (default true), TDS, salinity, and specific gravity.
    #getters and setters for those
    #dry cal? default 0?
    #high cal
    #low cal
    def __init__(self, *args, **kwargs):
        self.conductivity = IntVar()
        self.TDS = IntVar()
        self.salinity = IntVar()
        self.SG = IntVar()
        self.Dry = StringVar()
        self.Dry.set("dry")
        self.Low = IntVar()
        self.High = IntVar()
        self.Levels = [("Dry",self.Dry), ("Low",self.Low), ("High",self.High)]
    
    #---setConductivity() toggles whether EC meter is reading Electrical Conductivity----#
    #----Sends query "O, EC, x" where x=1 if Conductivity box is checked and x=0 if not----#
    def setECVals(self, vals):
        try:
            device.set_i2c_address(EC_addr)
            toggle="O,{},".format(vals[0]) + str(vals[1].get())
            device.query(toggle)

        except IOError:
            print("{} query failed in setECVals()\n - Address may be invalid, use List_addr command to see available addresses".format(vals[0]))

    def close_window(self):
        win.destroy()

    #----Called from __init__ in AtlasI2C class, creates thread for calib_sett but might not make a difference----#
    def start(self):
        self._thread = threading.Thread(target=self.calib_sett)
        self._thread.start()

    #----Called from calib_sett
    def run_cal(self, root):
        #need to do dry, then low, then high
        device.set_i2c_address(EC_addr) #check that we are communicating with EC (100)
        device.query("Cal, clear") #clear previous calibration settings
        global Temp_value
        if(Temp_value > 30 or Temp_value < 20):
            #TODO: need to use calibration levels on the bottle label if Temp is more than 5C away from 25C
            pass
        
        for level in self.Levels:
            cal = "Cal, " + str(level[0]) + ", " + str(level[1].get()) #e.g. cal, low, 12880
            tkMessageBox.showinfo("{} Calibration".format(str(level[0])),"Place probe in EC {} solution".format(str(level[1].get()))) #popup box for each calibration level
            root.update()
            time.sleep(10)
            try:
                device.query(cal)

            except IOError:
                print("{} query faied in ECSettings.run_cal()".format(cal))

        #countdown clock to wait a minute for stabilization after placing in solution?
        #OR display readings and ask user to wait until they are stable to click "ok"

    #----Called from start() (maybe change to be called from __init__ in AtlasI2C class----#
    #----Interface to let user select values to be displayed and/or enter calibration values----#
    def calib_sett(self, **kwargs):
        global win
        win = tk.Toplevel()
        win.wm_title("EC settings")
        #----for some reason, lambda is needed in the checkbutton commands to prevent them from executing at runtime----#
        Checkbutton(win, text="Conductivity", variable=self.conductivity, command=lambda: self.setECVals(["EC", self.conductivity]))\
                         .grid(row=0, sticky=W)
        Checkbutton(win, text="Total Dissolved Solids", variable=self.TDS, command=lambda: self.setECVals(["TDS", self.TDS]))\
                         .grid(row=1, sticky=W)
        Checkbutton(win, text="Salinity", variable=self.salinity, command=lambda: self.setECVals(["S", self.salinity]))\
                         .grid(row=2,sticky=W)
        Checkbutton(win, text="Specific Gravity", variable=self.SG, command=lambda: self.setECVals(["SG", self.SG]))\
                         .grid(row=3,sticky=W)

        variables = [self.Low, self.High]
        # -*- coding: utf-8 -*-
        fields = "Enter Low EC Value (µS): ", "Enter High EC Value (µS): "
        x=0
        for field in fields: #create calibration entry form
            lab = tk.Label(win, width=20, text=field, anchor='w')
            #print(self.levels)
            ent = tk.Entry(win, textvariable=variables[x])
            x+=1
            lab.grid(sticky=W)
            ent.grid(sticky=E)


        b = tk.Button(win, text="Run Calibration", command=lambda: self.run_cal(win)) #call run_cal
        b.grid(row=9, column = 0)
        c = tk.Button(win, text="Exit", command=self.close_window)
        c.grid(row=9, column=2)


#----Sample code taken from Atlas Scientific----#
#----Allows communication with I2C devices----#
class AtlasI2C(ttk.Frame):          #ttk.Frame is a container used to group other widgets together
        long_timeout = 1.5          # the timeout needed to query readings and calibrations
        short_timeout = .5          # timeout for regular commands
        default_bus = 1             # the default bus for I2C on the newer Raspberry Pis, certain older boards use bus 0
        default_address = 99        # the default address for the sensor, also the pH probe address
        current_addr = default_address
    

        def __init__(self, bus=default_bus):
            # open two file streams, one for reading and one for writing
            # the specific I2C channel is selected with bus
            # it is usually 1, except for older revisions where its 0
            # wb and rb indicate binary read and write
            self.file_read = io.open("/dev/i2c-"+str(bus), "rb", buffering=0)
            self.file_write = io.open("/dev/i2c-"+str(bus), "wb", buffering=0)

            #button for EC settings and calibration
            self.ecSettings = ECSettings()
            b = tk.Button(root, text="EC settings and calibration", command=self.ecSettings.start)#self.ecSettings.calib_sett)
            b.grid(row=8,sticky=W)

            #button for pH calibration
            self.phSettings = PHSettings()
            c = tk.Button(root, text="PH calibration", command=self.phSettings.calib_sett)
            c.grid(row=9, sticky=W)


        #----initializes I2C to either a user specified or default address----#
        #----self.set_i2c_address(address)----#
        def set_i2c_address(self, addr):
            # set the I2C communications to the slave specified by the address
            # The commands for I2C dev using the ioctl functions are specified in
            # the i2c-dev.h file from i2c-tools
            I2C_SLAVE = 0x703
            fcntl.ioctl(self.file_read, I2C_SLAVE, addr)
            fcntl.ioctl(self.file_write, I2C_SLAVE, addr)
            self.current_addr = addr
            

        def write(self, cmd):
                # appends the null character and sends the string over I2C
                cmd += "\00"
                self.file_write.write(cmd.encode('latin-1'))

        def read(self, num_of_bytes=31):
                global value_list
                # reads a specified number of bytes from I2C, then parses and displays the result
                device.write("R")
                time.sleep(self.long_timeout)
                res = self.file_read.read(num_of_bytes)         # read from the board
                if type(res[0]) is str:                 # if python2 read           
                    response = [i for i in res if i != '\x00']
                    if ord(response[0]) == 1:             # if the response isn't an error
                        # change MSB to 0 for all received characters except the first and get a list of characters
                        # NOTE: having to change the MSB to 0 is a glitch in the raspberry pi, and you shouldn't have to do this!
                        char_list = list(map(lambda x: chr(ord(x) & ~0x80), list(response[1:])))
                        value_list = ''.join(char_list)
                        return ''.join(char_list)     # convert the char list to a string and returns it
                    else:
                        return "Error " + str(ord(response[0]))
                        
                else:                                   # if python3 read
                    if res[0] == 1:
                        # change MSB to 0 for all received characters except the first and get a list of characters
                        # NOTE: having to change the MSB to 0 is a glitch in the raspberry pi, and you shouldn't have to do this!
                        char_list = list(map(lambda x: chr(x & ~0x80), list(res[1:])))
                        return ''.join(char_list)     # convert the char list to a string and returns it
                    else:
                        return "Error " + str(res[0])

        def query(self, string):
            # write a command to the board, wait the correct timeout, and read the response
            self.write(string)

            # the read and calibration commands require a longer timeout
            if((string.upper().startswith("R")) or
               (string.upper().startswith("CAL"))):
                time.sleep(1.5)
            elif string.upper().startswith("SLEEP"):
                return "sleep mode"
            else:
                time.sleep(0.5)

            return self.read()

        #display pH values read from i2c device
        def pH_reading(self):
            global pH_value
            device.set_i2c_address(pH_addr)
            device.read(num_of_bytes=31)
            pH_value.set(value_list) #value_list is initialized in device.read()

        #display EC values read from i2c device
        def EC_reading(self):
            global EC_value
            device.set_i2c_address(EC_addr)
            device.read(num_of_bytes=31)
            split = value_list.split(",")
            if(self.ecSettings.conductivity.get() == 1):
                EC_value.set(split[0])
            else:
                EC_value.set("not read")

        #display Total Dissolved Solids values read from i2c device
        def TDS_reading(self):
            global TDS_value
            device.set_i2c_address(EC_addr)
            device.read(num_of_bytes=31)
            split = value_list.split(",")
            if(self.ecSettings.TDS.get() == 1):
                TDS_value.set(split[1])
            else:
                TDS_value.set("not read")

        #display Salinity values read from i2c device
        def Sal_reading(self):
            global Sal_value
            device.set_i2c_address(EC_addr)
            device.read(num_of_bytes=31)
            split = value_list.split(",")
            if(self.ecSettings.salinity.get() == 1):
                Sal_value.set(split[2])
            else:
                Sal_value.set("not read")

        #display Specific Gravity values read from i2c device        
        def SG_reading(self):
            global SG_value
            device.set_i2c_address(EC_addr)
            device.read(num_of_bytes=31)
            split = value_list.split(",")
            if(self.ecSettings.SG.get() == 1):
                SG_value.set(split[2])
            else:
                SG_value.set("not read")

        #change water line labels to blue if above that point
        #or red if below
        def status_IO(self):
            global IO_state
            states = []
            states.append(GPIO.input(10)) #full
            states.append(GPIO.input(9))    #3/4 tank
            states.append(GPIO.input(11))   #1/2 tank
            states.append(GPIO.input(6))    #1/4 tank
            count = 0 #TODO: use this to keep track of which line should be changed.
            for state in states:
                if state:
                    #IO_state.set("On")
                    w.itemconfig(lines[count], fill="blue")
                    count+=1
                else:
                    #IO_state.set("Off")
                    w.itemconfig(lines[count], fill="red")
                    count+=1

        #display CO2 values read from serial connection            
        def CO2_reading(self):
            global CO2_value
            ser.flushInput()
            ser.write("\xFE\x44\x00\x08\x02\x9F\x25")
            time.sleep(.5)
            resp = ser.read(7)
            high = ord(resp[3])
            low = ord(resp[4])
            CO2_value.set(str((high*256) + low))

        #display Temperature values read from i2c device
        def Temp_reading(self):
            global Temp_value
            device.set_i2c_address(temp_addr)
            
            device.read(num_of_bytes=31)
            Temp_value.set(value_list)


    
def main():
    #while True:

        #----Thread readings for each component on main interface----#
        t1 = threading.Thread(target=device.pH_reading())
        t2 = threading.Thread(target=device.EC_reading())
        t3 = threading.Thread(target=device.TDS_reading())
        t4 = threading.Thread(target=device.Sal_reading())
        t5 = threading.Thread(target=device.SG_reading())
        #t6 = threading.Thread(target=device.status_IO())
        t7 = threading.Thread(target=device.CO2_reading())
        t8 = threading.Thread(target=device.Temp_reading())


        t1.start()
        t2.start()
        t3.start()
        t4.start()
        t5.start()
        #t6.start()
        t7.start()
        t8.start()

        t1.join()
        t2.join()
        t3.join()
        t4.join()
        t5.join()
        #t6.join()
        t7.join()
        t8.join()

        global current, date
        current=time.strftime("%H:%M")
        date=time.strftime("%A, %b %d, %Y")
        ClockText.configure(text=current)
        DateText.configure(text=date)
		
        root.after(1000,main)



#---Panel Layout---#
root = Tk()
root.config(bg="black")
root.wm_title("Dashboard")
root.geometry("1000x800") #dimensions of whole panel

#---Styles---#
red_bg = "#CC0000"
h1 = ("Calibri",14)

#---Frame Layout---#
Clock_frame=Frame(root,bg="black")
Clock_frame.grid(row=0,column=6,sticky="e")

pH_frame=Frame(root,bg="black")
pH_frame.grid(row=0,column=0,sticky="w")

EC_frame=Frame(root,bg=red_bg)
EC_frame.grid(row=1,column=0,sticky="w")

TDS_frame=Frame(root, bg=red_bg)
TDS_frame.grid(row=2,column=0,sticky="w")

Sal_frame=Frame(root, bg=red_bg)
Sal_frame.grid(row=3,column=0,sticky="w")

SG_frame=Frame(root, bg=red_bg)
SG_frame.grid(row=4, column=0, sticky="w")

CO2_frame=Frame(root,bg=red_bg)
CO2_frame.grid(row=5,column=0,sticky="w")

Temp_frame=Frame(root,bg=red_bg)
Temp_frame.grid(row=6,column=0,sticky="w")


#---Tkinter init/layout---#
pH_value = StringVar()
pH_value.set(0.00)
EC_value = StringVar()
EC_value.set(0.00)
TDS_value = StringVar()
TDS_value.set(0.00)
Sal_value = StringVar()
Sal_value.set(0.00)
SG_value = StringVar()
SG_value.set(0.00)
CO2_value = StringVar()
CO2_value.set(0.00)
Temp_value = StringVar()
Temp_value.set(0.00)


DateText=Label(Clock_frame,text="",bg="black",fg="red", font=h1)
DateText.grid(row=0,column=0,sticky=W+E)
ClockText=Label(Clock_frame,text="",bg="black",fg="white", font=h1)
ClockText.grid(row=1,column=0,sticky=E+W)

Label(pH_frame,text="pH Value: ",bg="gray",fg="White",font=h1).grid(row=0,column=0)
Label(pH_frame,textvariable=pH_value, bg="blue", fg="White",font=h1).grid(row=0,column=1)

Label(EC_frame,text="EC Value: ",bg="purple",fg="White",font=h1).grid(row=0,column=0)
Label(EC_frame,textvariable=EC_value, bg="blue", fg="White",font=h1).grid(row=0,column=1)

Label(TDS_frame,text="TDS Value: ",bg="purple",fg="white",font=h1).grid(row=0,column=0)
Label(TDS_frame,textvariable=TDS_value,bg="blue",fg="white",font=h1).grid(row=0,column=1)

Label(Sal_frame,text="Salinity Value: ",bg="purple",fg="white",font=h1).grid(row=0,column=0)
Label(Sal_frame,textvariable=Sal_value,bg="blue",fg="white",font=h1).grid(row=0,column=1)

Label(SG_frame,text="Specific Gravity Value: ",bg="purple",fg="white",font=h1).grid(row=0,column=0)
Label(SG_frame,textvariable=SG_value,bg="blue",fg="white",font=h1).grid(row=0,column=1)

Label(CO2_frame,text="CO2: ",bg="green",fg="White",font=h1).grid(row=0,column=0)
Label(CO2_frame,textvariable=CO2_value, bg="blue", fg="White",font=h1).grid(row=0,column=1)

Label(Temp_frame,text="Solution Temperature: ",bg="green",fg="White",font=h1).grid(row=0,column=0)
Label(Temp_frame,textvariable=Temp_value, bg="blue", fg="White",font=h1).grid(row=0,column=1)




Frame3 = Frame(root, bg="purple",width=400,height=200).grid(row=6,rowspan=2,column=17,columnspan=3,sticky=N+S+E+W)

fig = Figure(figsize=(5, 4), dpi=100)
t = np.arange(0, 3, .01)
fig.add_subplot(111).plot(t, 2 * np.sin(2 * np.pi * t))

canvas1 = FigureCanvasTkAgg(fig, master=Frame3)  # A tk.DrawingArea.
#canvas1.show()
#fig.canvas.draw()
canvas1.get_tk_widget().grid(row=6,column=17)

###----Water level graphic----#
##w = Canvas(root, 
##           width=10, 
##           height=400,
##           bg="light grey")
##w.grid(row=0, column=6)
##
##w.create_line(5,400,5,0,fill="grey",width=4)
##
###----Water Lines----#
##lines = []
##fullLine = w.create_line(1,5,10,5, fill="blue", width=6)
##topLine = w.create_line(1,105,10,105,fill="blue",width=6)
##middleLine = w.create_line(1,205,10,205,fill="blue", width=6)
##bottomLine = w.create_line(1,305,10,305,fill="blue",width=6)
##lines.append(fullLine)
##lines.append(topLine)
##lines.append(middleLine)
##lines.append(bottomLine)


device = AtlasI2C()
main()
#if __name__ == '__main__':
#	main()


root.mainloop()
