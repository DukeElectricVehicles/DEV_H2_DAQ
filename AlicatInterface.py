'''
Name:               AlicatInterface.py
Description:      	Alicat communication class
Author:             Gerry Chen
Created:            May 10, 2018
Modified:           May 11, 2018

'''

import sys
import serial
from serial.tools import list_ports
from parse import compile
from parse import *
import threading
import time
from CommInterface import CommInterface

class AlicatInterface(CommInterface):
	def __init__(self,port = '/dev/tty.usbserial',baudrate = 9600):
		CommInterface.__init__(self, logfileName='H2flow')
		self.serialLock = threading.Lock()
		self.serialName = port
		self.baudRate = baudrate
		self.timeout = 0.1
		self.ser = serial.Serial()
		self.ser.baudrate = self.baudRate
		self.ser.port = self.serialName
		self.ser.timeout = self.timeout
		self.ser.write_timeout = self.timeout;
		datVec = "A +0.0 +0.0 +0.0 +0.0 Air".split(' ');
		self.mostRecentData = datVec;
		self.running = False;

	def checkValidSerial(self):
		assert(not self.running)
		if not self.ser.isOpen():
			self.ser.open()
		self.flushSerial()
		self.poll()
		tmp = self.readLineData();
		# print(tmp)
		if ((len(tmp)==6) or (len(tmp)==11) or (len(tmp)>=12)):
			toRet = True
		else:
			toRet = False
		self.ser.close()
		return toRet

	def run(self):
		if not self.ser.isOpen():
			self.ser.open()
		self.flushSerial()
		startT = time.time()
		while self.running:
			self.poll()
			tmp = self.readLineData();
			if ((len(tmp)==6) or (len(tmp)==11) or (len(tmp)>=12)):
				self.mostRecentData = tmp
				self.log((time.time()-startT),str(tmp))
			else:
				print('alicat read error',str(tmp))
				self.ser.close()
				self.ser.open()
				self.flushSerial()
		self.ser.close()
	def close(self):
		if self.ser.isOpen():
			self.ser.close()
	def getMostRecentData(self):
		print(self.mostRecentData)
		return self.mostRecentData
	def flushSerial(self):
		self.serialLock.acquire()
		try:
			self.ser.write(b'\r')
			self.ser.write(b'\r')
		except:
			pass
		self.serialLock.release()

	def poll(self):
		self.serialLock.acquire()
		try:
			self.ser.write(b'\r')
			self.ser.write(b'A\r')
			time.sleep(0.001);
		except:
			print('Alicat Poll Error')
		self.serialLock.release()
	def readLine(self):
		self.serialLock.acquire()
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
		self.serialLock.release()
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

if __name__ == '__main__':
	ali = AlicatInterface()
	ali.start(attempt = 0);
	# print("started")
	# ali.poll()
	# print("polled")
	# #dat = ali.ser.read(10).decode()
	# print(ali.readLine())
	# print("readline")
	# ali.close()
