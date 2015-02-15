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
		self.writing = True
	
	#Set the clock signal high
	def clockHigh(self):
		self.GPIO.output(self.sclpin,GPIO.HIGH)
		
	#Set clock signal low
	def clockLow(self):
		self.GPIO.output(self.sclpin,GPIO.LOW)
		
	#Set SDA pin to output
	def.stopReading(self):
		self.GPIO.setup(self.sdapin, self.GPIO.OUT)
		self.writing = True
		
	#Set SDA pin to input	
	def startReading(self):
		self.GPIO.setup(self.sdapin, self.GPIO.IN)
		self.writing = False
		
	#Set the SDA line high
	def signalHigh(self):
		self.GPIO.output(self.sdapin,GPIO.HIGH)
		
	#Set the SDA line low
	def signalLow(self):
		self.GPIO.output(self.sdapin,GPIO.LOW)
		
	#Read bit on SDA line
	def readSignal(self):
		return self.GPIO.input(self.sdapin)
	
		
	#Send the I2C start signal
	#A HIGH to LOW transition of the SMBDAT line while SMBCLK is HIGH indicates a message 
	# START condition
	def sendStart(self):
		self.signalHigh()
		self.signalLow()
		self.clockLow()
	
	#Send the I2C stop signal
	#A LOW to HIGH transition of the SMBDAT line while SMBCLK is HIGH defines a message STOP 
	# condition.
	def sendStop(self):
		self.clockHigh()
		self.signalLow()
		self.signalHigh()
		
	#Sends an 8-bit byte until either receiving ACK or 
	#	trying n times
	# Returns True on success, False on timeout
	def sendByte(self,commandout, n):
		ack = 0
		for i in range(n):
			for i in range(8):
				if (commandout & 0x80):
					signalHigh()
				else:
					signalLow()
				commandout <<= 1
				clockHigh()
				clockLow()
				
			self.startReading()
			ack = self.readSignal()
			self.stopReading()
			if ack:
				return True
		return False
		
	#Receives an 8-bit byte, sends ack, and returns it
	def receiveByte(self):
		self.startReading()
		result = 0
		for i in range(8):
			self.clockHigh()
			self.clockLow()
			result <<= 1
			if (readSignal()):
					result |= 0x1
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
		self.sendByte(word,5)
		
		#Send cmd
		self.sendByte(cmd,5)
		
		#Send data1, data2, pec
		self.sendByte(data1,5)
		self.sendByte(data2,5)
		self.sendByte(pec)
		
		#Send stop signal
		self.sendStop()
		
		
	#Read a word from a given address 
	# returns the word
	def read_word(self,addr,cmd):
		#Send start signal
		self.sendStart()
		#Send address + write signal - try 5 times
		word = (addr << 1) | 0x00
		self.sendByte(word,5)
		
		#Send cmd
		self.sendByte(cmd,5)
		
		#Send address + read signal - try 5 times
		word = (addr << 1) | 0x01
		self.sendByte(word,5)
		
		#Read low byte
		lsb = self.receiveByte()
		
		#Read high byte
		msb = self.receiveByte()
		
		#Read PEC
		pec = self.receiveByte()
		
		#Send stop signal
		self.sendStop()
		
		#Return value
		return (msb << 8) + lsb
		