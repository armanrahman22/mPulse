import RPi.GPIO as GPIO
from utils import blinkControl
from time import sleep

GPIO.setmode(GPIO.BOARD)
#GPIO.setup(11, GPIO.OUT) #GPIO0 on pin 11
#Start a blink control on pin 22
pin22 = blinkControl(11,-1,GPIO)
pin22.start()
sleep(120)
pin22.kill()

