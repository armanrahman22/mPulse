from time import sleep

#Control communication on a bit-banged i2c bus on generial I/O pins
#IF YOU ARE WANT TO READ FROM SDA PIN YOU MUST CALL startReading() before starting, and call stopReading() after ending
# Default state of the SDA pin is OUTPUT
class SMBus:
	#Init - takes the GPIO instance and the pin #s for scl and sda
	def __init__(self,GPIO,sclpin,sdapin):
		self.GPIO = GPIO
		self.sclpin = sclpin
		self.sdapin = sdapin
		self.GPIO.setup(self.sclpin, self.GPIO.OUT)
		self.GPIO.setup(self.sdapin, self.GPIO.OUT)
	
	#Set the clock signal high
	def clockHigh(self):
		self.GPIO.output(self.sclpin,self.GPIO.HIGH)
		
	#Set clock signal low
	def clockLow(self):
		self.GPIO.output(self.sclpin,self.GPIO.LOW)
		
	#Set SDA pin to output
	def stopReading(self):
		self.GPIO.setup(self.sdapin, self.GPIO.OUT)
		
	#Set SDA pin to input	
	def startReading(self):
		self.GPIO.setup(self.sdapin, self.GPIO.IN)
		
	#Set the SDA line high
	def signalHigh(self):
		self.GPIO.output(self.sdapin,self.GPIO.HIGH)
		
	#Set the SDA line low
	def signalLow(self):
		self.GPIO.output(self.sdapin,self.GPIO.LOW)
		
	#Read bit on SDA line
	def readSignal(self):
		self.clockHigh()
		resp = self.GPIO.input(self.sdapin)		
		self.clockLow()
		return resp
	
		
	#Send the I2C start signal
	#A HIGH to LOW transition of the SMBDAT line while SMBCLK is HIGH indicates a message 
	# START condition
	def sendStart(self):
		self.clockLow()
		self.signalHigh()
		self.clockHigh()
		self.signalLow()
		self.clockLow()
	
	#Send the I2C stop signal
	#A LOW to HIGH transition of the SMBDAT line while SMBCLK is HIGH defines a message STOP 
	# condition.
	def sendStop(self):
		self.clockLow()
		self.signalLow()
		self.clockHigh()
		self.signalHigh()
		self.clockLow()
		
	#Sends an 8-bit byte and returns either ack or nack
	# returns 0 for ack and 1 for nack
	def sendByte(self,commandout):
		for i in range(8):
			if (commandout & 0x80):
				self.signalHigh()
			else:
				self.signalLow()
			commandout <<= 1
			self.clockHigh()
			self.clockLow()
			
		self.startReading()
		nack = self.readSignal()
		self.stopReading()
		return nack

		
	#Receives an 8-bit byte, sends ack, and returns it
	def receiveByte(self):
		self.startReading()
		result = 0x0
		for i in range(8):
			if (self.readSignal()): #readSignal() takes care of clock edges
					result |= 0x1
			result <<= 1
		result >>=1
		self.stopReading()
		
		#Send ack
		self.signalHigh()
		self.clockHigh()
		self.clockLow()
		return result
	
	#Write a word command to a given address
	# Sends addr, cmd, then data1, data2, and pec
	def write_word(self,addr,cmd,data1,data2,pec):
		#Send start signal
		self.sendStart()
		#Send address + write signal - try 5 times
		word = (addr << 1) | 0x00
		nack = self.sendByte(word)
		if nack:
			self.sendStop()
			return False 
		
		#Send cmd
		nack = self.sendByte(cmd)
		if nack:
			self.sendStop()
			return False 
		
		#Send data1, data2, pec
		nack = self.sendByte(data1)
		if nack:
			self.sendStop()
			return False 
		nack = self.sendByte(data2)
		if nack:
			self.sendStop()
			return False 
		nack = self.sendByte(pec)
		if nack:
			self.sendStop()
			return False 
		
		#Send stop signal
		self.sendStop()
		
		
	#Read a word from a given address 
	# returns the word
	# returns false if a NACK was received -> sender should try again
	def read_word(self,addr,cmd):
		#Send start signal
		self.sendStart()
		#Send address + write signal - try 5 times
		word = (addr << 1) | 0x00
		nack = self.sendByte(word)
		if nack:
			self.sendStop()
			return False
		
		#Send cmd
		nack = self.sendByte(cmd)
		if nack:
			self.sendStop()
			return False
			
		#Send second start
		self.sendStart()
		
		#Send address + read signal - try 5 times
		word = (addr << 1) | 0x01
		nack = self.sendByte(word)
		if nack:
			self.sendStop()
			return False
		
		#Read low byte
		lsb = self.receiveByte()
		
		#Read high byte
		msb = self.receiveByte()
		
		#Read PEC
		pec = self.receiveByte()
		
		#Send stop signal
		self.sendStop()
		
		#Return value
		return (msb << 8) | lsb
		