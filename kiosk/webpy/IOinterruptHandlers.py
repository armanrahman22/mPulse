#Interrupt handlers for each pin on each block
# args[0] is always the control instance from utils
# return 0 to clear the interrupt (default value), return 1 to leave the interrupt triggered (used in some cases where DEFVAL is set)
Aints = []
def intA0(args):
	return 0
	
Aints.append(intA0)
	
def intA1(args):
	return 0

Aints.append(intA1)

def intA2(args):
	return 0
	
Aints.append(intA2)

def intA3(args):
	return 0
	
Aints.append(intA3)
	
def intA4(args):
	return 0
	
Aints.append(intA4)

def intA5(args):
	return 0
	
Aints.append(intA5)
	
def intA6(args):
	return 0
	
Aints.append(intA6)
	
def intA7(args):
	return 0
	
Aints.append(intA7)
	
Bints = []
def intB0(args):
	return 0
	
Bints.append(intB0)
	
def intB1(args):
	return 0

Bints.append(intB1)

def intB2(args):
	return 0
	
Bints.append(intB2)

def intB3(args):
	return 0
	
Bints.append(intB3)
	
def intB4(args):
	return 0
	
Bints.append(intB4)

def intB5(args):
	return 0
	
Bints.append(intB5)
	
def intB6(args):
	return 0
	
Bints.append(intB6)
	
def intB7(args):
	return 0
	
Bints.append(intB7)
	
#Send an interrupt to the approriate handler
#	block is A or B
#	INTF is the contents of the INTFA or INTFB register
#	args are any args to return 0 to the handler
# 	args[0] is the control instance from utils

def handleInterrupt(block,INTF,args):
	#Figure out which pin casued interrupt
	pin = None
	mask = 0x01
	for i in range(8):
		if INTF == mask:
			pin = i
		mask = mask << 1
		
	if not pin: #unable to identify cause of interrupt
		return 0 
		
	if block == 'A':
		Aints[pin](args)
	else:
		Bints[pin](args)
		
	
	