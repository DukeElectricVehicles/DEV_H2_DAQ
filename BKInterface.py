'''
Name:					BKInterface.py
Description:	BK load communication class
Author:  			Gerry Chen
Created: 			May 10, 2018
Modified:			May 15, 2018

'''

import sys, time
from BK import dcload
from CommInterface import CommInterface
import numpy as np
import traceback

class BKInterface(dcload.DCLoad,CommInterface):
	def __init__(self,port = '/dev/tty.usbserial',baudrate = 38400):
		CommInterface.__init__(self, logfileName='powerstats')
		dcload.DCLoad.__init__(self)
		self.port        = port
		self.baudrate    = baudrate
		self.sp = None
		def loadFunc(t,dcload):
			return # don't do anything
		self.setLoadFunc(loadFunc)
		self.running = False
		self.mostRecentData = [0,0,0]

	def initialize(self):
		self.Initialize(self.port, self.baudrate)

	def checkValidSerial(self, closeWhenDone = True):
		self.initialize()
		for i in range(3):
			try:
				if self.SetLocalControl():
					toRet = False
					self.resetConnection()
				else:
					toRet = True
					break
			except AssertionError as e:
				toRet = False
		if (closeWhenDone):
			self.sp.close()
		return toRet

	def setLoadFunc(self,	loadFunc):
		self.loadFunc = loadFunc

	def run(self, updateRate=.1, startT=None):
		print('Running DC load')
		self.initialize()
		def test(cmd, results):
			if results:
				print(cmd, "failed:")
				print("  ", results)
				exit(1)
			else:
				print(cmd)
		for i in range(3):
			try:
				test('\tSetting to remote control: ',self.SetRemoteControl())
				break
			except AssertionError as e:
				print('error starting up BK:',e)
				traceback.print_exc()
				if (i>0):
					self.resetConnection()
		print('DC load initialized')
		print("\tGetting original setpoint ")
		origV = self.GetCCCurrent()
		print("\tGetting original mode     ")
		origM = self.GetMode()
		print("\toriginal setpoint          =", origV)
		print("\toriginal mode              =", origM)
		test("\tSet max current to 10 A", self.SetMaxCurrent(10))
		test("\tturning load on",self.TurnLoadOn())
		if (startT is None):
			startT = time.time()
		self.startT = startT
		index = 0 # for the loadFunc function
		while self.running:
			try:
				self.thisT = time.time()-self.startT
				try:
					index = self.loadFunc(self.thisT,self,index=index)
				except TypeError as t:
					self.loadFunc(self.thisT,self)

				while((time.time()-self.startT)-self.thisT<updateRate):
					dataStr,thisDat = self.GetInputValues()
					self.mostRecentData = thisDat
					self.log(time.time()-self.startT,dataStr)
					self.allData.append([time.time()-self.startT]+thisDat)
			except AssertionError as e:
				print(e)
			except Exception as e:
				print(e)
		test("\trestoring original setpoint", self.SetCCCurrent(origV))
		test("\trestoring original mode    ", self.SetMode(origM))
		test("\tturning load off", self.TurnLoadOff())
		test("\tSet to local control", self.SetLocalControl())
		self.sp.close()

	def resetConnection(self):
		self.sp.close()
		self.initialize()
		# self.sp.flush()

def main():
	pass

if __name__ == '__main__':
	main()