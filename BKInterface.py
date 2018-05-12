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
		CommInterface.__init__(self, logfileName='powerstats')
		self.port        = port
		self.baudrate    = baudrate
		dcload.DCLoad.__init__(self)
		def loadFunc(t,dcload):
			return # don't do anything
		self.setLoadFunc(loadFunc)
		self.running = False
		self.mostRecentData = [0,0,0]
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

	def setLoadFunc(self,	loadFunc):
		self.loadFunc = loadFunc

	def run(self, updateRate=.1):
		self.Initialize(self.port,self.baudrate)
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
			try:
				thisT = time.time()-startTime
				self.loadFunc(thisT,self)
				while((time.time()-startTime)-thisT<updateRate):
					# print(self.GetInputValues())
					dataStr,thisDat = self.GetInputValues()
					self.mostRecentData = thisDat
					self.log(thisT,dataStr)
					# time.sleep(0.001)
			except AssertionError as e:
				print(e)
			except Exception as e:
				print(e)
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