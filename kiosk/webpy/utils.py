from threading import Thread,Event,Semaphore
from datetime import datetime,timedelta,date
import time
#from serial import Serial
import json
import numpy as np
import spidev
#import smbus
from bitbangI2C import SMBus
from IOinterruptHandlers import handleInterrupt

#Control class for the GPIO pins
#Controls which pins will be used and how and provides functions for GPIO I/O
class Control:
	def __init__(self,GPIO,settings):
		self.settings = settings
		#Lists of pins that are being controlled
		self.outputs = settings.outputs
		self.inputs = settings.inputs
		self.blinkControlsList = settings.blinkControlsList
		self.blinkControls = {}
		self.GPIO = GPIO
		self.GPIO_mode = settings.GPIO_mode
 		
 		#ADC communication pins
 		#self.clockpin = settings.SPICLK
 		#self.mosipin = settings.SPIMOSI
 		#self.misopin = settings.SPIMISO
 		#self.cspin = settings.SPICS
 		
 		#SPI communication
 		self.spi = None
 		
 		#I2C
 		self.SMbus = None #initialized in start GPIO
 
		
		#Vars
		#self.doorMonitorTrue = 0
		#self.doorMonitorEvent = Event()
		
		#ecgReader
		self.ecgReader = None
		
		#scale
		self.scaleConnected = False #Will set to true if scale pins are set in adcInputs in settings
		self.scaleZero = settings.scaleZero
		self.scaleZeroThreshold = settings.scaleZeroThreshold
	
	#def doorMonitorTrigger(self,channel):
	#	self.doorMonitorEvent.set()
		
	

	#Sets the ecg light to blink at val 
	#	0 for always on
	#	-1 for always off
	#	Other values for # of seconds per blink if ecgLight is a blink control, else set output to 1
	def setECGLight(self,val):
		if self.settings.ecgLightPin in self.blinkControlsList:
			self.changeBlink(self.settings.ecgLightPin,val)
		elif self.settings.ecgLightPin in self.outputs:
			if val == -1:
				out = 0
			else:
				out = 1
			self.setOutput(self.settings.ecgLightPin,out)
		return
	
	#Doesn't return until someone is detected in the kiosk as per the thresholds defined in settings
	def waitForDoor(self):
		doorEvent = False
		while not doorEvent:
			#Wait for the scale value to pass the threshold - check every quarter second
			if self.readRawScale()[4] > (self.scaleZero + self.scaleZeroThreshold):
				doorEvent = True
			time.sleep(0.25)
		return True
		
		#self.doorMonitorEvent.clear()
		#self.doorMonitorEvent.wait()
		#return True
		
	#Returns whether the ECG leads connected or not
	def checkECGDown(self):
		return self.GPIO.input(self.settings.ecgMonitorPin)
		
	#Interrupt handling for the I/O expander
	def intA(self,channel):
		clearInterrupt = handleInterrupt('A',self.readIORegisterByte(0x0E),[self])
		if not clearInterrupt:
			self.readIORegisterByte(0x10) #clear interrupt by reading INTCAP (state of registers at interrupt)
		
	def intB(self,channel):
		clearInterrupt = handleInterrupt('B',self.readIORegisterByte(0x0F),[self])
		if not clearInterrupt:
			self.readIORegisterByte(0x11) #clear interrupt by reading INTCAP (state of registers at interrupt)
	
	#Setup the GPIO to work with desired pins
	def gpioStartup(self):
		
		if self.GPIO_mode == 'BCM':
			self.GPIO.setmode(self.GPIO.BCM)
		else:
			self.GPIO.setmode(self.GPIO.BOARD)
		
		#Setup outputs
		for out in self.outputs:
			self.GPIO.setup(out,self.GPIO.OUT)

		
		#Setup blink controls
		for bc in self.blinkControlsList:
			BC = BlinkControl(bc,-1,self.GPIO)
			BC.start()
			self.blinkControls[bc] = BC
		
		#Setup inputs
		for input in self.inputs:
			self.GPIO.setup(input,self.GPIO.IN,pull_up_down=self.GPIO.PUD_DOWN)

		#Setup Door Monitor Interrupt pin
		#if self.settings.doorMonitorPin in self.inputs:
		#	self.GPIO.add_event_detect(self.settings.doorMonitorPin, self.GPIO.RISING, callback=self.doorMonitorTrigger,bouncetime=200)
		
		
		# set up the SPI interface to the ADC and I/O
		self.spi = spidev.SpiDev()
		#Setup ADC
		if self.settings.ADCConnected:
			
			#Setup ecgReader
			if 'ecg' in self.settings.ADCInputs:
				def getValue():
					return self.getAnalogInput(self.settings.ADCInputs['ecg']) * 5 / 1023.0
				self.ecgReader = ECGReader(getValue,self.settings.ECGSampleInterval) #1 sample per ms
				self.ecgReader.start() #Start the thread
				
			#Setup scale
			if 'scale1' in self.settings.ADCInputs and 'scale2' in self.settings.ADCInputs and 'scale3' in self.settings.ADCInputs and 'scale4' in self.settings.ADCInputs:
				self.scaleConnected = True
				self.scaleLinearCoeffs = self.settings.scaleLinearCoeffs
				#self.scaleQuadraticCoeffs = self.settings.scaleQuadraticCoeffs
				#Zero out the scale
				self.zeroScale()
		#Setup I/O expander inputs and outputs
		if self.settings.IOConnected:
			self.spi.open(0,self.settings.IOCE)
			#Configure inputs and outputs
			opCode = 0x40 | (self.settings.IOADDR << 1) | 0x00 #Write to registers
			#Set pin directions
			self.spi.xfer2([opCode,0x00,self.settings.IOADIR, self.settings.IOBDIR]) #Auto-increments address
			#Set pull-up resistors
			self.spi.xfer2([opCode,0x0C,self.settings.IOAPU,self.settings.IOBPU])
			#Set all pins to 0 start
			self.IOAOutputState = 0x00
			self.IOBOutputState = 0x00
			self.spi.xfer2([opCode,0x12,self.IOAOutputState,self.IOBOutputState])
			#Configure interrupts
			if self.settings.interruptsEnabled:
				self.spi.xfer2([opCode,0x04,self.settings.IOINTENA,self.settings.IOINTENB,self.settings.IODEFVALA,self.settings.IODEFVALB,self.settings.IOINTCONA,self.settings.IOINTCONB])
				self.GPIO.setup(self.settings.INTAPIN,self.GPIO.IN)
				self.GPIO.setup(self.settings.INTBPIN,self.GPIO.IN)
				self.GPIO.add_event_detect(self.settings.INTAPIN, self.GPIO.FALLING, callback=self.intA)
				self.GPIO.add_event_detect(self.settings.INTBPIN, self.GPIO.FALLING, callback=self.intB)
				
			self.spi.close()
		
				
		#Set up I2C
		self.SMbus = SMBus(self.GPIO,self.settings.sclpin,self.settings.sdapin)
		
	#Shutdown the GPIO, kill threads
	def gpioShutdown(self):
		
		#Turn output pins off
		try:
			self.GPIO.output(11,self.GPIO.HIGH)
		except:
			pass
	
		#End any waiting for door
		#self.doorMonitorEvent.set()
		
		#Kill threads
		for pin,c in self.blinkControls.iteritems():
			c.kill()
		if self.ecgReader:
			self.ecgReader.kill()
		#self.doorMonitorThread.kill()
		
		
		self.GPIO.cleanup()
		
	#Put all pins back in their start state
	def reset(self):
			
		for pin,c in self.blinkControls.iteritems():
			c.setSec(-1)
			
		#Reset door monitor and ecg monitor
		#self.doorMonitorTrue = 0
		
		#Pause ecg
		if self.ecgReader:
			self.ecgReader.pause()
			
		#Zero out the scale if it appears no one is on it
		self.zeroScale()

	
	#Set an output pin on the GPIO 
	# val in [0,1]
	def setOutput(self,pin,val):
		#Set an output
		if val == 0:
			self.GPIO.output(pin,self.GPIO.LOW)
			return 1
		elif val == 1:
			self.GPIO.output(pin,self.GPIO.HIGH)
			return 1
		else: 
			return 0
	
	#Read a digital input from the GPIO
	def getDigitalInput(self,pin):
		return self.GPIO.input(pin)

	#Read an analog input from the ADC connected to the GPIO
	#Returns -1 if no ADC is connected or if adcnum is not in [0,7]
	def getAnalogInput(self,adcnum):
		return self.readADC(adcnum)

	#Changes the blink speed of a blink control object	
	def changeBlink(self,pin,sec):
		self.blinkControls.get(pin).setSec(sec)
		
	#Function to read from the MCP3008 analog to digital converter via spi pins
	#Returns a value between 0 and 1023
	#Takes as input:
	#	adcnum - [0,7] - the analog input to read
	#returns -1 if not connected
	def readADC(self,adcnum):
		if self.settings.ADCConnected:
			self.spi.open(0,self.settings.ADCCE)
			
			if ((adcnum > 7) or (adcnum < 0)):
				return -1
				
			#Get instruction bits to send
			r = self.spi.xfer2([1,(8+adcnum)<<4,0])
			
			#Process and return response
			adcout = ((r[1]&3) << 8) + r[2]
			self.spi.close()
			return adcout
		else:
			return -1
			
	#Functions for MCP23S17 I/O expander
	
	#Write a byte val to the given register address
	# addr and val are bytes
	def writeIORegisterByte(self,addr,val):
		self.spi.open(0,self.settings.IOCE)
		opCode = 0x40 | (self.settings.IOADDR << 1) | 0x00
		self.spi.xfer2([opCode,addr,val])
		self.spi.close()
		
	#Read a byte from the given register address
	def readIORegisterByte(self,addr):
		self.spi.open(0,self.settings.IOCE)
		opCode = 0x40 | (self.settings.IOADDR << 1) | 0x01
		val = self.spi.xfer2([opCode,addr,0x00])
		self.spi.close()
		return val[2]
		
	#Read from MCP23S17 I/O expander
	# returns -1 if not connected, or if block of pin not valid
	# ionum is in [0,7], block is A or B
	def readIO(self,block,ionum):
		if self.settings.IOConnected and ionum >= 0 and ionum <= 7:
			if block == 'A':
				blockAddr = 0x12
			elif block == 'B':
				blockAddr = 0x13
			else:
				return -1
			read = self.readIORegisterByte(blockAddr)
			ioOut = ((read & (1 << ionum)) >> ionum)
			return ioOut
		else:
			return -1
			
	#Returns true if a pin is configured as an output
	def ioIsOutput(self,block,ionum):
		if ionum < 0 or ionum > 7:
			return 0
		if block == 'A':
			dir = self.settings.IOADIR
		elif block == 'B':
			dir = self.settings.IOBDIR
		else:
			return 0
		return not ((dir & (1<<ionum)) >> ionum)
		
	#Write to MCP23S17 I/O expander output pin
	# returns -1 if not connected or if pin is configured as an input, or bock or ionum invalid
	# ionum is 0-7, block is A or B, val is 0 or 1
	def writeIO(self,block,ionum,val):
		if self.settings.IOConnected and self.ioIsOutput(block,ionum):
			if block == 'A':
				blockAddr = 0x12
				self.IOAOutputState = (self.IOAOutputState & (~(1<<ionum))) + (val << ionum)
				writeState = self.IOAOutputState
			else:
				blockAddr = 0x13
				self.IOBOutputState = (self.IOBOutputState & (~(1<<ionum))) + (val << ionum)
				writeState = self.IOBOutputState
			
			self.writeIORegisterByte(blockAddr,writeState)
		else:
			return -1
		
		
	
	########### ECG methods ########### 
	#Unpauses the ecgReader thread
	def startECG(self):
		if not self.ecgReader:
			return False
		self.ecgReader.unpause()
		return True
	#Gets a list of readings from the ecgReader thread
	def readECG(self,n):
		if not self.ecgReader:
			return False
		return self.ecgReader.getReading(n)

	#Pauses the ecgReader thread
	def stopECG(self):
		if not self.ecgReader:
			return False
		self.ecgReader.pause()
		return True
		
	############  Scale methods ########### 
	
	#Gets a weight reading from the scale
	#Returns -1 if scale not connected
	def getWeight(self):
		if self.scaleConnected:
			total = sum([self.readADC(self.settings.ADCInputs[name]) for name in ['scale1','scale2','scale3','scale4']])
			return max(0,self.scaleLinearCoeffs[0]*(total-self.scaleZero)) #+ self.scaleLinearCoeffs[1])
			#return max(0,self.scaleQuadraticCoeffs[0]*(total**2)+self.scaleQuadraticCoeffs[1]*total + self.scaleQuadraticCoeffs[2])
		return -1
		
	#Return a reading from the scale in lbs
	#Averages 6 readings over 3 seconds
	#If no scale is connected in the inputs in settings, return -1
	def readScale(self):
		if self.scaleConnected:
			#Set coeffs based on zero
			#self.scaleLinearCoeffs[1] = -self.scaleLinearCoeffs[0]*self.scaleZero
			#self.scaleQuadraticCoeffs[2] = -self.scaleQuadraticCoeffs[0]*(self.scaleZero**2) - self.scaleQuadraticCoeffs[1] * self.scaleZero
			readings = []
			for i in range(6):
				readings.append(self.getWeight())
				time.sleep(0.5)
			avgWeight = sum(readings)/len(readings)
			for val in readings:
				if abs(avgWeight-val) > 10:
					readings.remove(val)
			#Return the average with big outliers removed
			return ("%.2f" % (sum(readings)/len(readings)))
		return -1
	
	#Dynamically set the scale zero
	# Get ten readings
	def zeroScale(self):
		for i in range(10):
			total = sum([self.readADC(self.settings.ADCInputs[name]) for name in ['scale1','scale2','scale3','scale4']])
			if total < self.scaleZero+self.scaleZeroThreshold:
				self.scaleZero = 0.8*total + 0.2*self.scaleZero
	
	#Get raw values from the scale
	def readRawScale(self):
		list = [self.readADC(self.settings.ADCInputs[name]) for name in ['scale1','scale2','scale3','scale4']]
		s = sum(list)
		list.append(s)
		return list
		
	########## Temperature methods ########### 
	#Return a reading from the temperature sensor in degrees fahrenheit
	#	Tries 5 times before returning -1
	#If no sensor is connected in the inputs in settings, return -1
	# If ambient is true, reads the ambient temperature
	def readTemperature(self,ambient=False):
		if self.settings.IRConnected:
			cmd = 0x07 #Read object temperature
			if ambient: #Read the ambient temperature instead of object
				cmd = 0x06
			checkTemp = None
			for i in range(5):
				temp = self.SMbus.read_word(self.settings.IRtempSMBAddress,cmd)
				if temp:
					if not ((0x8000 & temp) >> 15): #error condition
						tempDegrees = (temp/50.0 - 273.15)* 1.8 + 32.0
						if tempDegrees > 115:
							if checkTemp and abs(checkTemp-tempDegrees) < 2:
								return ("%.2f" % tempDegrees)
							checkTemp = tempDegrees
						else:
							return ("%.2f" % tempDegrees)
		return -1
		
#Thread class to control blinking behaviour for a pin
#set seconds to 0 for always HIGH, -1 for always LOW
#Starts low and will go low on kill
#@pin = pin number to control 
class BlinkControl(Thread):
    def __init__(self,pin,sec,GPIO):
        Thread.__init__(self)
        #Set class vars
        self.sec = sec
        self.pin = pin
        self.GPIO = GPIO
        
        #Set up pin and set LOW
        self.GPIO.setup(pin,self.GPIO.OUT)
        self.GPIO.output(pin,self.GPIO.LOW)
        
        #initialize state
        self.state = False
        self.stop = False 
        self.change = Event()
        return

    def run(self):
		while not self.stop:
			self.change.clear() #Clear the change flag
			#If should be LOW, check if HIGH and if so make LOW
			if self.sec == -1:
				 if self.state:
				 	self.GPIO.output(self.pin,self.GPIO.LOW)
				 	self.state = False
				 self.change.wait()
			#If should be HIGH, check if LOW and if so make HIGH
			elif self.sec == 0:
				if not self.state:
					self.GPIO.output(self.pin,self.GPIO.HIGH)
					self.state = True
				self.change.wait()
			#Else should be blinking, change if necessary
			else:
				if self.state:
					self.GPIO.output(self.pin,self.GPIO.LOW)
				else:
					self.GPIO.output(self.pin,self.GPIO.HIGH)
				self.state = not self.state
				self.change.wait(self.sec)
		
		#do on kill
		try:
			self.GPIO.output(self.pin,self.GPIO.LOW)
		except:
			pass
		return


    def setSec(self,sec):
        self.sec = sec
        self.GPIO.output(self.pin,self.GPIO.LOW)
        self.state = False
        self.change.set()
        return
        
    def kill(self):
        self.stop = True
        self.change.set()
        return

# Class to read in input from a single analog-output ECG
# Contains methods to start reading, to stop reading, and to get a reading,
# 	which consists of n datapoints, where n is passed as a variable
class ECGReader(Thread):
	#init method. Takes as input a method that will return one value from the ECG,
	# , a number (n) of max values to return at once on a reading,
	# and a number of seconds to wait between readings
	def __init__(self,getValue,sec):
		Thread.__init__(self)
		self.getValue = getValue
		self.isStopped = False
		self.readingsList = []
		self.sec = sec
		self.isPaused = True
		#self.startTime = None
		self.change = Event() #Event to tell loop there's been a change
	
	#Thread's run method
	def run(self):
		while not self.isStopped:
			self.change.clear()
			#If not paused, take readings every sec seconds and add them to readingsList
			while not self.isPaused: 
				#self.readingsList.append([(datetime.now() - self.startTime).total_seconds(),self.getValue()])
				self.readingsList.append([time.time()*1000,self.getValue()])
				self.change.wait(self.sec)
				
			self.change.wait() #If paused, wait for unpause or kill to resume
		return
	#unpause method
	# Clears out old readings and unpauses the thread
	def unpause(self):
		self.readingsList = []
		self.isPaused = False
		#self.startTime = datetime.now()
		self.change.set()
		return
		
	#Read method
	#Returns maximum n readings
	def getReading(self,n):
		numReadings = len(self.readingsList)
		if numReadings > 5 * n:
			self.readingsList = []
			return 'resync'
		if numReadings > 0:
			index = min(numReadings,n)
			resp = self.readingsList[:index]
			self.readingsList = self.readingsList[index:]
			return resp
		return None
	
	#Pause method
	# Pauses the thread
	def pause(self):
		self.isPaused = True
		
	#Kill method - stops the thread permanently
	def kill(self):
		self.isStopped = True
		self.change.set()
		return

	
#Class to read and write values from the JSON file containing current session data
class DataFile:
	def __init__(self,filePath):
		self.filePath = filePath
		self.lock = Semaphore()
		self.data = None
		self.file = None
		
	#Opens the JSON file
	def open(self):
		self.file = open(self.filePath,'r+')
		self.data = json.loads(self.file.read())
		
	#Writes the existing data object to a json file
	#If path is unspecified, uses the filepath
	#If path is specified, saves to given path
	def writeOut(self,path=None):
		self.lock.acquire() #Acquire the lock on the data object
		if path != None:
			file = open(path,'w+')
		else:
			file = self.file
		file.seek(0)
		file.truncate()
		file.write(json.dumps(data,sort_keys=True,indent=4, separators=(',', ': ')))
		self.lock.release() #Release the lock on the data object
		
	#Closes the file
	def close(self):
		self.file.close()
	
	#Writes a value into the current data object in the field sessionData -> name
	def writeSessionValue(self,name,val):
		self.lock.acquire() #Acquire the lock on the data object
		for item in self.data['sessionData']:
			if item[0] == name:
				item[1] = val
		self.lock.release() #Release the lock on the data object
		
		
	#Extends the graph values in graphData -> name by the given values, keeping the length of the list under maxLength
	def extendGraphValues(self,name,maxLength,valList):
		self.lock.acquire() #Acquire the lock on the data object
		graphData = self.data['graphData']
		if name in graphData:
			newLength = len(graphData[name]) + len(valList)
			if newLength > maxLength: #restrict to maxLength
				overflow = newLength - maxLength
				graphData[name] = graphData[name][overflow:]
			graphData[name].extend(valList)
		else:
			graphData[name] = valList
		self.data['graphData'] = graphData
		self.lock.release() #Release the lock on the data object
		
	#Writes new values to graph values in graphData
	def writeGraphValues(self,name,values):
		self.lock.acquire() #Acquire the lock on the data object
		self.data['graphData'][name] = values
		self.lock.release() #Release the lock on the data object
		
	#Clears graph values of the given name
	def clearGraphValues(self,name):
		self.lock.acquire()
		self.data['graphData'][name] = []
		self.lock.release()
		
		
	#Returns a simple read-out of the file
	def getData(self):
		self.lock.acquire() #Acquire the lock on the data object
		data = self.data
		self.lock.release() #Release the lock on the data object
		return data
		
	#Clears out the sessionData and graphData fields
	def clearValues(self):
		self.lock.acquire() #Acquire the lock on the data object
		#Clear session data
		for item in self.data['sessionData']: 
			item[1] = None
		#Clear graph data
		self.data['graphData'] = {}
		self.lock.release() #Release the lock on the data object
		
	#Filters ECG data and processes it to get BPM
	def processECGData(self):
		self.lock.acquire()
		graphData = self.data['graphData']
		self.lock.release()
		if 'ecg' in graphData:
			graphData['ecg'] = graphData['ecg'][:-15] #chop off the last view values of data
			graphData['ecg'] = filterECG(graphData['ecg']) #returns [] if it's just noise
			if graphData['ecg'] != []:
				#get BPM and Re-store data
				timeRange = graphData['ecg'][-1][0]
				ecgY = [pair[1] for pair in graphData['ecg']]
				self.writeSessionValue('Pulse Rate',getBPMfromECG(timeRange,ecgY))
		
		self.lock.acquire() #Acquire the lock on the data object
		self.data['graphData'] = graphData
		self.lock.release() #Release the lock on the data object
		return
		
#Background generic worker thread for executing a given function
class GenericWorkerThread(Thread):
	#Takes a function and a list of parameters for the function
	def __init__(self,function,params):
		Thread.__init__(self)
		self.function = function
		self.params = params
	#Executes function(params)
	def run(self):
		self.function(self.params)
		return
		

		
#Returns bpm when given range of time over entire period and baseline-stabilized ecg data
#time range in seconds
def getBPMfromECG(timeRange,data):
	dataLength = len(data)
	
	heartbeats = np.zeros(dataLength)
	
	#Split the data into 5 second segments
	splitData = np.array_split(data,int(timeRange/5))
	heartbeatCount = 0
	#Go through the data splits and look for peaks
	for subData in splitData:
		subDataLength = len(subData)
		mean = sum(subData)/subDataLength
		deviation = np.zeros(subDataLength)
		difference = np.zeros(subDataLength)
	
		#Find each point's deviation from the mean and difference from it's neighboor
		for i in range(subDataLength-1):
			difference[i] = abs(subData[i]-subData[i+1])
			deviation[i] = abs(subData[i] - mean)
		
		#Set thresholds for the deviation and two-point difference of a heartbeat
		devThreshold = 0.5 * np.amax(deviation)
		diffThreshold = 0.5 * np.amax(difference)
		
		#Look for heartbeats
		for i in range(subDataLength-1):
			dev = abs(subData[i]-mean) 
			diff = abs(subData[i]-subData[i+1])
			if diff > diffThreshold or dev > devThreshold:
				heartbeats[heartbeatCount] = 1
			heartbeatCount += 1
		heartbeatCount += 1
		
	
	#Calculate the average distance between suspected heartbeats, attempting to ignore peak-trough double-counting
	oneIndices = np.nonzero(heartbeats)[0]
	beatDistances  = [(oneIndices[i+1] - oneIndices[i]) for i in range(len(oneIndices)-1) if (oneIndices[i+1] - oneIndices[i]) > 5]
	#minDist = np.amin(beatDistances)
	
	#Get rid of doubles
	avgBeatDist = np.mean(beatDistances)
 	for i in range(len(oneIndices) - 1):
 		beatDist = (oneIndices[i+1] - oneIndices[i])
 		if (beatDist < 0.7*avgBeatDist):
 			heartbeats[oneIndices[i+1]] = 0

	#Get rid of outliers		
	oneIndices = np.nonzero(heartbeats)[0]
	beatDistances  = [(oneIndices[i+1] - oneIndices[i]) for i in range(len(oneIndices)-1)]
	beatDistances = [dist for dist in beatDistances if dist < 1.5*np.mean(beatDistances)]
	timePerIndex = timeRange / dataLength
	avgBeatDist = np.mean(beatDistances)
	
	#Calculate and return bpm
	bpm = int(round((1.0/avgBeatDist) * (1.0 / timePerIndex) * 60.0)) #1 beat/avgBeatDist * 1/timePerIndex 1/sec   * 60 sec/min 
	return bpm
	
#Baseline-stabilize raw ecg data, normalize time to seconds,  and return filtered data
#graphData is a list of [milliseconds,voltage] pairs
def filterECG(graphData):
	dataLength = len(graphData)
	ecgY = np.zeros(dataLength)
	ecgData = []
	
	#Eliminate low-frequency 'moving baseline' from ecg data
	j = 0
	for i in range(dataLength): #Get voltage values
		if graphData[i] != None:
			ecgY[j] = graphData[i][1]
			j += 1
	#See if the ECG is just pure noise. if so return blank
	#if (sum(ecgY)/len(ecgY)) > 0.5*(max(ecgY)-min(ecgY)):
	#	return []
	fft=np.fft.rfft(ecgY) 
	freq=np.fft.fftfreq(dataLength)
	bp=fft[:]  
	for i in range(len(bp)):
		if i<70:
			bp[i]=0  
	
	ecgYhp=np.fft.irfft(bp,dataLength)
	
	#Normalize time 
	firstVal = None
	j = 0
	for i in range(len(graphData)):
		pair = graphData[i]
		if pair != None:
			if not firstVal:
				firstVal = pair[0]
			x = (pair[0]-firstVal) / 10.0**3 #convert back to seconds
			ecgData.append([x,ecgYhp[j]])
			j += 1			
	return ecgData

#Extends the list curList with newVals up to maxLength - overwrites oldest values to make room for new ones
def extendList(maxLength,curList,newVals):
	newLength = len(curList) + len(newVals)
	if newLength > maxLength: #restrict to maxLength
		overflow = newLength - maxLength
		curList = curList[overflow:]
	curList.extend(newVals)
	return curList
	 
##### Error pages #####
# def notfound():
# 	return web.notfound("404 Not Found")
# 
# def internalerror():
# 	return web.internalerror("500 Internal Server Error")	
	
		