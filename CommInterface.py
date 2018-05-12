'''
Name:					CommInterface.py
Description:	Interface for communication classes
Author:  			Gerry Chen
Created: 			May 11, 2018
Modified:			May 11, 2018

'''

import threading

class CommInterface():

	def __init__(self,logfileName = ''):
		if logfileName=='':
			logfileName = type(self).__name__
		self.dataFile = open('data/'+logfileName+'.txt','w')
	def initialize(self):
		raise NotImplementedError()
	def checkValidSerial(self):
		raise NotImplementedError()
	def start(self,attempt=0):
		try:
			if (attempt==0):
				self.running = True;
			self.runThread = threading.Thread(target=self.run)
			self.runThread.start();
		except:
			print(type(self).__name__+" Start error!!!")
			if attempt<5 and self.running==True:
				print("Attempting to connect again in 3 seconds...")
				t = threading.Timer(3,self.start,kwargs={'attempt':attempt+1})
				t.start()
	def stop(self):
		self.running = False
		try:
			self.runThread.join()
			self.dataFile.close()
		except Exception as e:
			print('error terminating process',type(self).__name__)
			print(e)
		# self.ser.close()

	def log(self,time,text):
		if (time==-1):
			self.dataFile.write(text)
		else:
			self.dataFile.write(str(round(time,4))+'s\t'+text+'\n')
		self.dataFile.flush()