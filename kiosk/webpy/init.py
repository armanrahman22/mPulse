import RPi.GPIO as GPIO
from utils import Control,BlinkControl,DataFile
import settings
		
#Setup GPIO control, alamode communication, and session data file from settings
control = Control(GPIO,settings)
dataFile = DataFile(settings.sessionDataPath)
dataFile.open()