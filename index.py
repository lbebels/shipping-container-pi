#!/usr/bin/python

import io         # used to create file streams
from io import open
import fcntl      # used to access I2C parameters like addresses

import time       # used for sleep delay and timestamps
import string     # helps parse strings

import RPi.GPIO as GPIO

import Tkinter as tk
from Tkinter import *
import ttk

#from toggle import Toggle


#---Initialization---#
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(6,GPIO.IN,pull_up_down = GPIO.PUD_DOWN)
i2c_list = [99,100]
pH_addr, EC_addr = i2c_list


class ECSettings(ttk.Frame):
    def __init__(self):
        self.CondCheck = IntVar(value=1)
        self.TDSCheck = IntVar(value=0)
        self.SalCheck = IntVar(value=0)
        self.SGCheck = IntVar(value=0)
    
    def calib_sett(self, **kwargs):
        win = tk.Toplevel()
        win.wm_title("EC settings")
        #master = Tk()
        var1 = IntVar(value=1)
        Checkbutton(win, text="Conductivity", variable=self.CondCheck).grid(row=0, sticky=W)
        var2 = IntVar()
        Checkbutton(win, text="Total Dissolved Solids", variable=var2).grid(row=1, sticky=W)
        var3 = IntVar()
        Checkbutton(win, text="Salinity", variable=var2).grid(row=2,sticky=W)
##
##        try:
##            print(device.query("O,EC,1"))
##        except IOError:
##            print("Query failed \n - Address may be invalid, use List_addr command to see available addresses")



class AtlasI2C(ttk.Frame):              #ttk.Frame is a container used to group other widgets together
        long_timeout = 1.5          # the timeout needed to query readings and calibrations
        short_timeout = .5          # timeout for regular commands
        default_bus = 1             # the default bus for I2C on the newer Raspberry Pis, certain older boards use bus 0
        default_address = 99        # the default address for the sensor
        current_addr = default_address
    

        def __init__(self, bus=default_bus):
            # open two file streams, one for reading and one for writing
            # the specific I2C channel is selected with bus
            # it is usually 1, except for older revisions where its 0
            # wb and rb indicate binary read and write
            self.file_read = io.open("/dev/i2c-"+str(bus), "rb", buffering=0)
            self.file_write = io.open("/dev/i2c-"+str(bus), "wb", buffering=0)

            e = ECSettings()
            b = tk.Button(root, text="EC settings and calibration", command=e.calib_sett)
            b.grid()

            # initializes I2C to either a user specified or default address
            #self.set_i2c_address(adress)
        

        def set_i2c_address(self, addr):
            # set the I2C communications to the slave specified by the address
            # The commands for I2C dev using the ioctl functions are specified in
            # the i2c-dev.h file from i2c-tools
            I2C_SLAVE = 0x703
            fcntl.ioctl(self.file_read, I2C_SLAVE, addr)
            fcntl.ioctl(self.file_write, I2C_SLAVE, addr)
            self.current_addr = addr
        
        def query(self, string):
            # write a command to the board, wait the correct timeout, and read the response
            self.write(string)

            # the read and calibration commands require a longer timeout
            if((string.upper().startswith("R")) or
               (string.upper().startswith("CAL"))):
                time.sleep(self.long_timeout)
            elif string.upper().startswith("SLEEP"):
                return "sleep mode"
            else:
                time.sleep(self.short_timeout)

            return self.read()
            

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
                        #print "Command succeeded " + ''.join(char_list)     # convert the char list to a string and returns it
                    else:
                        return "Error " + str(ord(response[0]))
                        
                else:                                   # if python3 read
                    if res[0] == 1:
                        # change MSB to 0 for all received characters except the first and get a list of characters
                        # NOTE: having to change the MSB to 0 is a glitch in the raspberry pi, and you shouldn't have to do this!
                        char_list = list(map(lambda x: chr(x & ~0x80), list(res[1:])))
                        return "Command succeeded " + ''.join(char_list)     # convert the char list to a string and returns it
                    else:
                        return "Error " + str(res[0])


        def pH_reading(self):
            global pH_value
            device.set_i2c_address(pH_addr)
            device.read(num_of_bytes=31)
            #pH_value = value_list
            pH_value.set(value_list)

        def EC_reading(self):
            global EC_value
            device.set_i2c_address(EC_addr)
            device.read(num_of_bytes=31)
            #EC_value = value_list
            EC_value.set(value_list)

        def status_IO(self):
            global IO_state
            state = GPIO.input(6)
            if state:
                IO_state.set("On")
            else:
                IO_state.set("Off")
	    

#class EC(AtlasI2C):
    #TODO:
    #booleans or 1/0 for conductivity (default true), TDS, salinity, and specific gravity.
    #getters and setters for those
    #dry cal? default 0?
    #high cal
    #low cal
    


def main():
    #while True:
        
        device.pH_reading()
        device.EC_reading()
        device.status_IO()
        #print type(pH_value)
		
        root.after(1000,main)



#---Panel Layout---#
root = Tk()
root.config(bg="black")
root.wm_title("Dashboard")
#root.geometry("800x800")

#---Styles---#
red_bg = "#CC0000"
h1 = ("Calibri",14)

#---Frame Layout---#
pH_frame=Frame(root,bg="black")
pH_frame.grid(row=0,column=0,stick="w")

EC_frame=Frame(root,bg=red_bg)
EC_frame.grid(row=1,column=0,sticky="w")

IO_frame=Frame(root,bg=red_bg)
IO_frame.grid(row=2,column=0,sticky="w")


#---Tkinter init/layout---#
pH_value = StringVar()
pH_value.set(0.00)
EC_value = StringVar()
EC_value.set(0.00)
IO_state = StringVar()
IO_state.set("")


Label(pH_frame,text="pH Value: ",bg="gray",fg="White",font=h1).grid(row=0,column=0)
Label(pH_frame,textvariable=pH_value, bg="blue", fg="White",font=h1).grid(row=0,column=1)

Label(EC_frame,text="EC Value: ",bg="purple",fg="White",font=h1).grid(row=0,column=0)
Label(EC_frame,textvariable=EC_value, bg="blue", fg="White",font=h1).grid(row=0,column=1)

Label(IO_frame,text="State: ",bg="green",fg="White",font=h1).grid(row=0,column=0)
Label(IO_frame,textvariable=IO_state, bg="blue", fg="White",font=h1).grid(row=0,column=1)


device = AtlasI2C()
main()
#if __name__ == '__main__':
#	main()


root.mainloop()
