'''
Name:               AlicatInterface.py
Description:      	Alicat communication class
Author:             Gerry Chen
Created:            May 10, 2018
Modified:           May 13, 2018

'''

import sys
import serial
from serial.tools import list_ports
from parse import compile
from parse import *
import threading
import time
from CommInterface import CommInterface
import numpy as np

class ControllerInterface(CommInterface):
	def __init__(self,port = '/dev/tty.usbmodem',baudrate = 115200):
		CommInterface.__init__(self, logfileName='controller')
		self.serialLock = threading.Lock()
		self.serialName = port
		self.baudRate = baudrate
		self.timeout = 0.1
		self.ser = serial.Serial()
		self.ser.baudrate = self.baudRate
		self.ser.port = self.serialName
		self.ser.timeout = self.timeout
		self.ser.write_timeout = self.timeout;
		datVec = [0,0,0,0,0,0,0];
		self.mostRecentData = datVec;
		self.running = False;
		self.ID = 'C'

	def checkValidSerial(self):
		assert(not self.running)
		for ID in ['C']:
			self.ID = ID
			if not self.ser.isOpen():
				self.ser.open()
			self.flushSerial()
			self.poll()
			tmp = self.readLineData();
			# print(tmp)
			if ((len(tmp)==7)):
				toRet = True
				break
			else:
				toRet = False
		self.ser.close()
		return toRet

	def run(self,startT = None):
		if not self.ser.isOpen():
			self.ser.open()
		self.flushSerial()
		if (startT is None):
			startT = time.time()
		countE = 0
		while self.running:
			try:
				self.poll()
				tmp = self.readLineData();
				if ((len(tmp)==7)):
					data = [int(d) for d in tmp[0:6]]
					data.append(float(tmp[6][0:-3]))
					self.mostRecentData = data
					self.log((time.time()-startT),str(data))
					self.allData.append([time.time()-startT]+data)
					countE = 0
				else:
					countE += 1
					print('controller read error',str(tmp))
					if(countE>1):
						self.resetConnection()
					else:
						self.flushSerial()
			except:
				print('controller read error...')
		self.ser.close()
	def stringifyData(self,data):
		if len(data==4):
			return '%.2fpsia\t%.2f°C\t%.3fLPM\t%.3fmg/s\n'%tuple(data)
		elif len(data==5):
			return '%.2fpsia\t%.2f°C\t%.3fLPM\t%.3fmg/s%.3fg\n'%tuple(data)
		else:
			return str(data)
	def close(self):
		if self.ser.isOpen():
			self.ser.close()
	def resetConnection(self):
		self.ser.close()
		self.ser.open()
		self.flushSerial()
	def getMostRecentData(self):
		print(self.mostRecentData)
		return self.mostRecentData
	def flushSerial(self):
		self.serialLock.acquire()
		try:
			self.ser.write(b'\n')
			self.ser.write(b'\n')
		except:
			pass
		self.serialLock.release()

	def poll(self):
		self.serialLock.acquire()
		try:
			# self.ser.write(b'\r')
			self.ser.write((self.ID+'\n').encode())
			time.sleep(0.001);
		except:
			print('Controller Poll Error')
		self.serialLock.release()
	def readLine(self):
		self.serialLock.acquire()
		try:
			startTime = time.time()
			toRet = b''
			thisChar = ""
			while (thisChar != '\n') and (time.time()-startTime<self.timeout):
				thisChar = self.ser.read()
				toRet = toRet+thisChar
			toRet = toRet.decode()
		except Exception as e:
			print("error",e)
			return ""
		while(len(toRet)!=0 and (toRet[-1]=='\n' or toRet[-1]=='\r')):
			toRet = toRet[0:-1]
		self.serialLock.release()
		return toRet
	def readLineData(self):
		dat = self.readLine();
		datVec = dat.split('\t');
		return datVec;

	def setSerialName(self,name):
		self.serialName = name
	def setBaud(self,baud):
		self.baudRate = baud
	def setTimeout(self,time):
		self.timeout = time
	def setLineFormat(self,strFormat):
		self.lineFormat = compile(strFormat+"{:s}")