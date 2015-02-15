#Settings file for classes and functions in init.py, utils.py and code.py

#Base URL to post data to
mpulseBaseURL = 'https://maby.scripts.mit.edu/mpulse/'

#GPIO mode
GPIO_mode = 'BCM' #'BOARD' or 'BCM'

#Path to file to temporarily store session data 
#Should be a valid JSON file
sessionDataPath = 'sessionData.json'

#################### I/O pins ###################
#GPIO
ecgMonitorPin = 25

#Blink controls
#blinkControlsList = [ecgLightPin]
blinkControlsList = []

################### GPIO Outputs / Inputs (DO NOT add ADC inputs here) ###################
outputs = []
inputs = [ecgMonitorPin] #These are by default pull-down


################### ECG Settings ################
ECGSampleInterval = 0.001 #How often to take an ECG reading (approximate)
ECGDataLength = 6000 #The number of readings to store as an ECG. 

################### ADC inputs ###################
ecgInputPin = 7

scaleInputPin1 = 0
scaleInputPin2 = 1
scaleInputPin3 = 2
scaleInputPin4 = 3

#Dictionary of inputs on the ADC as 'name': pin pairs.
#Pin is in [0,7]
ADCInputs = {'ecg':ecgInputPin,'scale1':scaleInputPin1,'scale2':scaleInputPin2,'scale3':scaleInputPin3,'scale4':scaleInputPin4}

#Toggle whether to use an ADC and all of its inputs
# ADC should be connected on raspberry pi's SPI interface on the given chip select line
ADCConnected = True
ADCCE = 0

#Toggler whether to use I/O expander
# I/O expander should be on SPI interface on given chip select line
IOConnected = True
IOCE = 1
IOADDR = 0 #Address of the I/O expander (0-7, controlled by pins 15-17)
#Configure A and B blocks of I/O pins as inputs or outputs
# 1 - Input
# 0 - Output
# All inputs: 0xFF, all outputs: 0x00
IOADIR = 0xFF
IOBDIR = 0xFF
#Configure pull-up resistors on A and B pin blocks
# 1 - pull-up enabled
# 0 - pull-up disabled
IOAPU = 0x00
IOBPU = 0x00
#Configure interrupts on A and B pin blocks
# Interrupts will set the INTA or INTB pin high
# Interrupt functions are defined in IOinterruptHandlers.py
INTAPIN = 27
INTBPIN = 17
# Interrupt enable:
#	0 - disabled
#	1 - enabled
interruptsEnabled = 0
IOINTENA = 0x00
IOINTENB = 0x00
#Controls whether interrupt is on change, or on being the opposite value from DEFVAL
# 	0 - any change
#	1 - opposite from DEFVAL (interrupt condition persists as long as pin has the opposite value from DEFVAL)
IOINTCONA = 0x00
IOINTCONB = 0x00
#Values to compare against if INTCON is set to 1
IODEFVALA = 0x00
IODEFVALB = 0x00

#Scale calibration
#Values from the scale come as analog inputs [0,1023] from the ADC
#These coeffs convert the sum of the 4 analog inputs to weights
scaleLinearCoeffs = [0.779566430564499]#,-540.890749087787]
#scaleQuadraticCoeffs = [6.58907612e-04, -3.70215658e-01, 7.62060178e+00]
#Initial zero value and threshold for saying no one is on the scale
#This will get updated and averaged
scaleZero = 1010
scaleZeroThreshold = 50 #The number of units above scaleZero to consider the scale as being occupied

#I2C bus
sclpin = 18
sdapin = 23

#IR temp sensor on I2C bus
IRConnected = True
IRtempSMBAddress = 0x5a

