'''
Name:					CommInterface.py
Description:	Interface for communication classes
Author:  			Gerry Chen
Created: 			May 11, 2018
Modified:			May 11, 2018

'''

import threading
import numpy as np
from scipy.io import savemat
import time

class CommInterface():

	def __init__(self,logfileName = ''):
		if logfileName=='':
			logfileName = type(self).__name__
		self.saveName = logfileName
		self.dataFile = open('data/'+logfileName+'.txt','w')
		self.allData = []
	def initialize(self):
		raise NotImplementedError()
	def checkValidSerial(self):
		raise NotImplementedError()
	def start(self, attempt=0, startT=None):
		try:
			if (attempt==0):
				self.running = True;
			self.runThread = threading.Thread(target=self.run,kwargs=({'startT':startT}))
			self.runThread.start();
		except:
			print(type(self).__name__+" Start error!!!")
			if attempt<5 and self.running==True:
				print("Attempting to connect again in 3 seconds...")
				t = threading.Timer(3,self.start,kwargs={'attempt':attempt+1})
				t.start()
	def stop(self):
		self.running = False
		for i in range(3):
			try:
				self.runThread.join(timeout=3)
				self.dataFile.close()
				if (self.runThread.is_alive()):
					print("couldn't join thread from",type(self).__name__)
					print("\tTrying again...")
				else:
					print("successfully ended",type(self).__name__)
					return
			except Exception as e:
				print('error terminating process',type(self).__name__)
				print(e)
		# self.ser.close()
	def save(self):
		savemat('data/'+self.saveName,{'data':self.allData})
	def resetData(self,startT = None):
		if startT is None:
			startT = time.time()
		self.allData = []
		self.startT = startT
		self.thisT = 0
	def log(self,time,text):
		if (time==-1):
			self.dataFile.write(text)
		else:
			self.dataFile.write('%.3fs\t%s\n'%(time,text))
		self.dataFile.flush()
