'''
Name:               AlicatInterface.py
Description:      	Alicat communication class
Author:             Gerry Chen
Created:            May 10, 2018
Modified:           May 15, 2018

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

'''
	AlicatInterface - class used to communicate with Alicat
'''
class AlicatInterface(CommInterface):
	def __init__(self,port = '/dev/tty.usbserial',baudrate = 9600):
		CommInterface.__init__(self, logfileName='H2flow')
		self.serialLock = threading.Lock()
		self.serialName = port
		self.baudRate = baudrate
		self.timeout = 0.2
		self.ser = serial.Serial()
		self.ser.baudrate = self.baudRate
		self.ser.port = self.serialName
		self.ser.timeout = self.timeout
		self.ser.write_timeout = self.timeout;
		datVec = "A +0.0 +0.0 +0.0 +0.0 Air".split(' '); # dummy initialization
		self.mostRecentData = datVec;
		self.running = False;
		self.ID = 'A'
		self.hasTot = False;

	def checkValidSerial(self):
		assert(not self.running)
		for ID in ['A','B']: # check whatever IDs you may have
			self.ID = ID
			if not self.ser.isOpen():
				self.ser.open()
			self.flushSerial()
			self.poll()
			tmp = self.readLineData();
			# print(tmp)
			if ((len(tmp)==6) or (len(tmp)==11) or (len(tmp)>=12)):
				toRet = True
				break
			else:
				toRet = False
			self.ser.close()
		return toRet

	# runthread
	def run(self, startT=None):
		if not self.ser.isOpen():
			self.ser.open()
		self.flushSerial()
		if (startT is None):
			startT = time.time()
		self.startT = startT
		countE = 0 # number of tries since last successful data read
		while self.running:
			try:
				self.poll()  # poll Alicat...
				tmp = self.readLineData(); # then read back
				# print(tmp)
				# number of returned values varies depending on which version of alicat
				if ((len(tmp)==6) or (len(tmp)==11 and (not self.hasTot)) or (len(tmp)>=12)):
					data = [float(d) for d in tmp[1:5]]
					if (tmp[-1]=='TMF' or len(tmp)==12): # new alicat with totalizer
						self.hasTot = True
						data.append(float(tmp[5]))
					self.mostRecentData = data
					self.log((time.time()-self.startT),self.stringifyData(data))
					self.allData.append([time.time()-self.startT]+data)
					countE = 0
				else:
					countE += 1
					print('alicat read error',str(tmp))
					if(countE>1):
						self.resetConnection()
					else:
						self.flushSerial()
			except Exception as e:
				print('alicat read error...',e)
		self.ser.close()
	def stringifyData(self,data): # to pretty-print data
		if len(data)==4:
			return '%.2fpsia\t%.2f°C\t%.3fLPM\t%.3fmg/s\n'%tuple(data)
		elif len(data)==5:
			return '%.2fpsia\t%.2f°C\t%.3fLPM\t%.3fmg/s\t%.3fg\n'%tuple(data)
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
		return self.mostRecentData
	def flushSerial(self): # sometimes we need to send some extra lines when Alicat gets confused
		self.serialLock.acquire()
		try:
			self.ser.write(b'\r')
			self.ser.write(b'\r')
		except:
			pass
		self.serialLock.release()

	# sends ID followed by a CR
	def poll(self):
		self.serialLock.acquire()
		try:
			# self.ser.write(b'\r')
			self.ser.write((self.ID+'\r').encode())
			time.sleep(0.001);
		except:
			print('Alicat Poll Error')
		self.serialLock.release()
	# reads bytes until reaches a CR or timeout
	def readLine(self):
		self.serialLock.acquire()
		try:
			startTime = time.time()
			toRet = ""
			thisChar = ""
			while (thisChar != chr(13)) and ((time.time()-startTime)<5*self.timeout):
				thisChar = self.ser.read().decode()
				toRet = toRet+thisChar
		except:
			print("error")
			return ""
		# chop off extra non-vital characters
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
	# legacy code - completely useless but afraid it might break something if i delete it
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
