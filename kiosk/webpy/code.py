#Webpy
import web
# Sets up GPIO and sets pins to blinkControl, input, or output. 
# Defines gpioStartup function to start threads and gpioShutdown function to kill blinkControl threads
# Contains lists of available pins: outputs, inputs, blinkControls
from init import control,dataFile
#Worker thread
from utils import GenericWorkerThread #, notfound, internalerror
#URL handling
import urllib
import urllib2
#Date / Time
from datetime import datetime
from time import sleep
#Settings
import settings

web.config.debug = True

#Set url patters
urls = (
	'/', 'Index',
	'/index/','Index',
	'/shutdown/?','Shutdown',
	'/restart/?','Restart',
# 	'/controls/?','Controls',
	'/doorMonitor/?','DoorMonitor', #Door monitor wait for interupt call
	#Controls for GPIO pins on raspi + extended I/O pins
	'/outputControl/?','OutputControl',
	'/blinkControl/?','BlinkControl',
	'/readDigitalInput/?','GPIODigitalRead',
	'/readAnalogInput/?','GPIOAnalogRead',
	#Readings
	'/readings/temperature/?','ReadTemperature',
	'/readings/scale/?','ReadScale',
	'/readRawScale/?','ReadRawScale',
	'/readings/ecg/?','ReadECG',
	#Walkthrough of sensor stations
	'/ecg/?', 'ECG',
	'/temperatureHeight/?','TemperatureHeight',
	#'/walkthrough2/moveOn/?','Walkthrough2MoveOn',
	'/results/?','Results',

	#Post a session's data to the M-Pulse Site or email results to the user
	# GET options: email, action (save/email)
	'/postSession/?','PostSession',
)


### Templates
t_globals = {
    'datestr': web.datestr,
}
render = web.template.render('templates', base='base', globals=t_globals)

app = web.application(urls, globals())
 
class Index:
	def GET(self):
		getInput = web.input(quit=0)
		if (int(getInput.quit) == 1): #Quit the page	
			#Read the person's weight and write it to file (MOVED TO RESULTS PAGE, HTML)
			#dataFile.writeSessionValue('Weight',control.readScale())
			#GenericWorkerThread(lambda params: params[1].writeSessionValue('Weight',params[0].readScale()),[control,dataFile]).start()
			return None
		else: #Load the page
			#Reset session values when walkthrough starts
			dataFile.clearValues()	
			
			#Reset controls
			control.reset()
			
			#Render the page
			return render.index()
		
class Restart:
	def GET(self):	
		#Reset session values
		dataFile.clearValues()
		#reset all lights
		control.reset()
		#Turn off ecg in case it didn't quit properly
		control.stopECG()
		
		#Render index
		return render.index()

#Waits for waitForDoor() to return before returning -> when wait for door returns, someone is in the kiosk
class DoorMonitor:
	def GET(self):
		return control.waitForDoor()

#Controls pins set with blinkControl objects - can set the blink seconds parameter	
class BlinkControl:
	def GET(self):
		getInput = web.input(pin="",sec="")
		pin = int(getInput.pin)
		sec = float(getInput.sec)
		if pin in control.blinkControls:
			control.changeBlink(pin,sec)
		else:
			return 'not in blink controls: '+str(control.blinkControls)
		return 'success'

#Controls output pins - can set high or low
# Use A0 or B0 for writing to extended I/O
class OutputControl:
	def GET(self):
		getInput = web.input(pin="",val="")
		pin = getInput.pin
		if 'A' in pin or 'B' in pin:
			return control.writeIO(pin[0],int(pin[1]),int(getInput.val))
		else:
			if pin in control.outputs:
				if not control.setOutput(int(pin),int(getInput.val)):
					return 'not a valid value (0 or 1)'
			else:
				return 'not in output controls: '+str(control.outputs)
			return 'success'
		
#Reads and returns from a digital GPIO input
# Use A0 or B0 for reading from extended I/O
class GPIODigitalRead:
	def GET(self):
		getInput = web.input(pin="")
		pin = getInput.pin
		if 'A' in pin or 'B' in pin:
			return control.readIO(pin[0],int(pin[1]))
		else:
			return control.getDigitalInput(int(pin))
		
		
#Reads and returns from an analog GPIO input through the ADC
# adcnum in [0,7] (returns -1 otherwise)
class GPIOAnalogRead:
	def GET(self):
		getInput = web.input(adcnum="")
		adcnum = int(getInput.adcnum)
		return control.getAnalogInput(adcnum)
	
#Get temperature reading if sensor is connected
# if not connected - returns -1
# Also stores current reading in the data file
class ReadTemperature:
	def GET(self):
		getInput = web.input(ambient=0)
		amb = int(getInput.ambient)
		temp = control.readTemperature(amb)
		if not amb and temp != -1:
			dataFile.writeSessionValue('Skin Temperature',temp)
		return temp
			
#Get ECG reading from GPIO / ecgReader class	
#Also returns whether the user is done taking the ecg
#If started=0 is passed in the URL, returns True if the ecg sensor reads the handles are up, False otherwise
class ReadECG:
	def GET(self):
		#Get reading
		reading = control.readECG(1000)
		#Check if front end is showing the ecg graph 
		# - if they are: return reading
		# - if they aren't: toss the reading and return whether or not the handles are up
		getInput = web.input(started=0)
		if (int(getInput.started) == 0): #Graph not showing
			return bool(control.checkECGDown())
			
		#Graph showing:
		#If not, return either a reading or 'Done'
		if not control.checkECGDown(): #If the handles were put down then stop reading
			control.stopECG()
			return 'Done'
			
		if reading == 'resync':
			return 'resync'
		
		#Write new values to session data file in a worker thread
		GenericWorkerThread(lambda params: params[1].extendGraphValues('ecg',settings.ECGDataLength,params[0]),[reading,dataFile]).start()
		
		#Take temperature in worker thread
		def takeTemp(params):
			control,dataFile = params
			temp = control.readTemperature()
			if temp != -1:
				dataFile.writeSessionValue('Skin Temperature',temp)
		GenericWorkerThread(takeTemp,[control,dataFile]).start()
		#Convert to milliseconds and give every other pt
		#reading_p = [[reading[i][0]*1000,reading[i][1]] for i in range(0,len(reading),2)]
		return reading[::2] #Return every other pt in the reading
		
#Returns a reading from the scale if it's connected
# Averages over a few readings taken over 3 seconds
#	If not connected - returns -1
class ReadScale:
	def GET(self):
		getInput = web.input(store=0)
		reading = control.readScale()
		
		
		
		if (int(getInput.store) == 1): #Store reading in file
			dataFile.writeSessionValue('Weight',reading)
			
		return reading
		
class ReadRawScale:
	def GET(self):
		return control.readRawScale()
		
#Walkthrough of sensors
		
		
#First walkthrough page - ecg
class ECG:
	def GET(self):
		getInput = web.input(quit=0,retake=0)
		if (int(getInput.quit) == 1): #Quit the page
			#control.setECGLight(-1)
			control.stopECG()
			#Filter final ecg data and re-store, get heart rate from ECG data and store
			dataFile.processECGData()
			return None
		else: #Load the page
			dataFile.clearGraphValues('ecg') #Clear existing ECG data
			#control.setECGLight(0)
			control.startECG()
			return render.ecg(int(getInput.retake))
			
#Second walkthrough page - Temperature and height
class TemperatureHeight:
	def GET(self):
		getInput = web.input(retake=0)
		return render.temperatureheight(int(getInput.retake))
		
#Results page - sends data for a preview of the results to be sent or saved
class Results:
	def GET(self):
		
		data = dataFile.getData()
		sessionData = data['sessionData']
		graphData = data['graphData']
		if 'ecg' in graphData:
			ecgData = graphData['ecg']
		else:
			ecgData = None
		if ecgData and len(ecgData):
			return render.results(sessionData,ecgData[:len(ecgData)/2][::2])
		else:
			return render.results(sessionData,0)
		

#Send session data to the M-Pulse Server Site 
# Options:
#	email - the email address of the user to email or save the results for
#   action - email or save
class PostSession:
	def GET(self):
		#Get the email from URL and the action
		getInput = web.input(email="",action=[])
		email = getInput.email
		action = getInput.action
		
		#URL(s) to post the data to
		urls = []
		if 'email' in action:
			urls += [settings.mpulseBaseURL+'session/emailData/']
		if 'save' in action:
			urls += [settings.mpulseBaseURL+'session/saveData/']
		if 'email' not in action and 'save' not in action:
			return 'failure: no actions selected'
		
		#Get values from session data file
		data = dataFile.getData()
	
		#Get secret_key from file on disk
		file = open('../secret_key.txt')
		secret_key = file.read().strip()
		file.close()
		
		#Get kiosk_name from file on disk
		file = open('../kiosk_name.txt')
		kiosk_name = file.read().strip()
		file.close()
		
		#Set values
		values = {'userEmail' : email,
		  'kioskName' : kiosk_name,
          'datetimeTaken' : datetime.now(),
          'sessionData' : data['sessionData'],
          'graphData' : data['graphData'],
          'secret_key' : secret_key}

		data = urllib.urlencode(values)
		
		try:
			#Post the data
			responses = []
			for url in urls:
				request = urllib2.Request(url, data)
				response = urllib2.urlopen(request)
				responses += [response.read()]
		except:
			return render.endwalkthrough('Unable to establish connection to the server. Kiosk may not be connected to the Internet.')
			
		if sum([r != 'success' for r in responses]) > 0:	
			return render.endwalkthrough(str(responses))
		else:
			return render.endwalkthrough('success')
		
#Shuts down the app, including blinkControl objects and the comm with the alamode
class Shutdown:
	def GET(self):
		dataFile.close()
		control.gpioShutdown()
		app.stop()
		return 'Shutdown successful'
		

if __name__ == '__main__':
	control.gpioStartup()
	app.run()