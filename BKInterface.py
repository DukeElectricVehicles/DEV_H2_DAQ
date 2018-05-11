'''
Name:					BKInterface.py
Description:	BK load communication class
Author:  			Gerry Chen
Created: 			May 10, 2018
Modified:			May 11, 2018

'''

import sys, time
from BK import dcload
from CommInterface import CommInterface

class BKInterface(dcload.DCLoad,CommInterface):
	def __init__(self,port = '/dev/tty.usbserial',baudrate = 9600):
		self.port        = port
		self.baudrate    = baudrate
		dcload.DCLoad.__init__(self)
		def loadFunc(t,dcload):
			return # don't do anything
		self.setLoadFunc(loadFunc)
		self.running = False
		# self.ser = self.sp # for compatibility

	def initialize(self):
		self.Initialize(self.port,self.baudrate)

	def checkValidSerial(self):
		self.Initialize(self.port,self.baudrate)
		try:
			if self.SetLocalControl():
				toRet = False
			else:
				toRet = True
		except AssertionError:
			toRet = False
		self.sp.close()
		return toRet

	def GetInputValuesList(self):
		'''Returns voltage in V, current in A, and power in W, op_state byte,
		and demand_state byte.
		'''
		cmd = self.StartCommand(0x5F)
		cmd += self.Reserved(3)
		cmd += chr(self.CalculateChecksum(cmd))
		assert(self.CommandProperlyFormed(cmd))
		response = self.SendCommand(cmd)
		self.PrintCommandAndResponse(cmd, response, "Get input values")
		voltage = self.DecodeInteger(response[3:7])/self.convert_voltage
		current = self.DecodeInteger(response[7:11])/self.convert_current
		power   = self.DecodeInteger(response[11:15])/self.convert_power
		op_state = hex(self.DecodeInteger(response[15]))
		demand_state = hex(self.DecodeInteger(response[16:18]))

		return [voltage,current,power,op_state,demand_state]

	def setLoadFunc(self,	loadFunc):
		self.loadFunc = loadFunc

	def run(self, updateRate=.1):
		print('Running DC load')
		self.Initialize(self.port,self.baudrate)
		self.SetRemoteControl()
		def test(cmd, results):
			if results:
				print(cmd, "failed:")
				print("  ", results)
				exit(1)
			else:
				print(cmd)
		origV = self.GetCCCurrent()
		origM = self.GetMode()
		print("\toriginal setpoint          =", origV)
		print("\toriginal mode              =", origM)
		test("\tSet max current to 7 A", self.SetMaxCurrent(7))
		test("\tturning load on",self.TurnLoadOn())
		startTime = time.time()
		while self.running:
			thisT = time.time()-startTime
			print(self.GetInputValues())
			self.loadFunc(thisT,self)
			# s,v = self.loadFunc(thisT)
			# if s=='power':
			# 	self.SetMode('cw')
			# 	self.SetCWPower(v)
			# elif s=='voltage':
			# 	self.SetMode('cv')
			# 	self.SetCVVoltage(v)
			# elif s=='current':
			# 	self.SetMode('cc')
			# 	self.SetCCCurrent(v)
			# elif s=='resistance':
			# 	self.SetMode('cr')
			# 	self.SetCRResistance(v)
			# elif s=='pass' or s=='passive':
			# 	pass
			# else:
			# 	print('BK error: unknown setpoint variable')
			while((time.time()-startTime)-thisT<updateRate):
				print(self.GetInputValues())
				# time.sleep(0.001)
		test("\trestoring original setpoint", self.SetCCCurrent(origV))
		test("\trestoring original mode    ", self.SetMode(origM))
		test("\tturning load off", self.TurnLoadOff())
		test("\tSet to local control", self.SetLocalControl())
		self.sp.close()
	
	# def setShortCircuitTrans

def main():
	if len(sys.argv) != 4: 
		Usage()
	access_type = sys.argv[1]
	port        = sys.argv[2]
	baudrate    = int(sys.argv[3])
	if access_type == "com":
		load = Dispatch('BKServers.DCLoad85xx')
	elif access_type == "obj":
		load = dcload.DCLoad()
	else:
		Usage()
	TalkToLoad(load, port, baudrate)
	return 0

if __name__ == '__main__':
	main()