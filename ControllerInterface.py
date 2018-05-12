'''
Name:					ControllerInterface.py
Description:	Communication with the FC controller
Author:  			Gerry Chen
Created: 			May 11, 2018
Modified:			May 11, 2018

'''

import sys, time, os
import serial
from CommInterface import CommInterface

class ControllerInterface(CommInterface):
	def __init__(self,port = '/dev/tty.teensy',baudrate = 9600):
		CommInterface.__init__(self, logfileName='controller')
		self.serialName = port
		self.baudRate = baudrate
		self.timeout = 0.1
		self.ser = serial.Serial()
		self.ser.baudrate = self.baudRate
		self.ser.port = self.serialName
		self.ser.timeout = self.timeout
		self.ser.write_timeout = self.timeout

	def checkValidSerial(self):
		if not self.ser.isOpen():
			self.ser.open()
		self.ser.write(b'\r')
		self.ser.write(b'\r')
		self.poll()
		tmp = self.readLineData();
		if ((len(tmp)==6) or (len(tmp)==11)or (len(tmp)==12)):
			toRet = True
		else:
			toRet = False
		self.ser.close()
		return toRet

	def collectData(self):
		startT = time.time()
		while self.collecting:
			self.poll()
			tmp = self.readLineData();
			if ((len(tmp)==6) or (len(tmp)==11)):
				self.mostRecentData = tmp
				self.log(time.time()-startT,tmp)
			else:
				print('alicat read error')
	def stop(self):
		self.collecting = False
	def close(self):
		if self.ser.isOpen():
			self.ser.close()
	def getMostRecentData(self):
		print(self.mostRecentData)
		return self.mostRecentData
	def poll(self):
		try:
			self.ser.write(b'\r')
			self.ser.write(b'(\r')
			time.sleep(0.001);
		except:
			print('Controller Poll Error')
	def readLine(self):
		try:
			startTime = time.time()
			toRet = ""
			thisChar = ""
			while (thisChar != chr(13)) and (time.time()-startTime<self.timeout):
				thisChar = self.ser.read().decode()
				toRet = toRet+thisChar
		except:
			print("error")
			return ""
		while(len(toRet)!=0 and (toRet[-1]=='\n' or toRet[-1]=='\r')):
			toRet = toRet[0:-1]
		return toRet
	def readLineData(self):
		dat = self.readLine();
		datVec = dat.split(' ');
		return datVec;

	def setSerialName(self,name):
		self.serialName = name
	def setBaud(self,baud):
		self.baudRate = baud
	def setTimeout(self,time):
		self.timeout = time
	def setLineFormat(self,strFormat):
		self.lineFormat = compile(strFormat+"{:s}")