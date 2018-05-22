'''
Name:					main.py
Description:	main script for DEV's H2 FC efficiency characterization
Author:  			Gerry Chen
Created: 			May 10, 2018
Modified:			May 11, 2018

'''

import os, serial, time, sys
from serial.tools import list_ports
from AlicatInterface import AlicatInterface
from BKInterface import BKInterface
from ControllerInterface import ControllerInterface
import copy
import threading
import numpy as np
from scipy.io import savemat
import traceback

with open('log.txt', 'wb') as outf:
    # os.dup2(inf.fileno(), 0)
    os.dup2(outf.fileno(), 1)
    # os.dup2(outf.fileno(), 2)

class MainManager():
	def __init__(self, dcload, alicat, controller):
		self.dcload = dcload
		self.alicat = alicat
		self.controller = controller
		self.running = True
		self.startT = time.time()

	def startAll(self):
		startT = self.startT
		if self.dcload is not None:
			self.dcload.start(startT=startT)
		if self.alicat is not None:
			self.alicat.start(startT=startT)
		if self.controller is not None:
			self.controller.start(startT=startT)

	def saveAll(self):
		toSave = {}
		for comm in [self.dcload,self.alicat,self.controller]:
			if comm is not None:
				toSave[comm.saveName] = comm.allData
				# comm.save()
		savemat('data/data',toSave)

	def stopAll(self):
		if self.dcload is not None:
			self.dcload.stop()
		if self.alicat is not None:
			self.alicat.stop()
		if self.controller is not None:
			self.controller.stop()

	def checkInputs(self): # blocking
		command = ' '
		print('starting input checking')
		def doNothing(t,dcload):
			return
		self.setPower = 0
		while command!='q':
			print(command)
			if command=='q':
				break
			try:
				if command=='>':
					self.dcload.SetMode('cw')
					self.dcload.SetCWPower(0)
					self.dcload.loadFunc = powerStepLoad
				if command[-1]=='W':
					self.dcload.SetMode('cw')
					self.dcload.SetCWPower(float(command[0:-1]))
					self.setPower = float(command[0:-1])
					self.dcload.loadFunc = doNothing # don't change after set
					print('set to constant power mode:',float(command[0:-1]))
				elif command[-1]=='V':
					self.dcload.SetMode('cv')
					self.dcload.SetCVVoltage(float(command[0:-1]))
					self.dcload.loadFunc = doNothing
				elif command[-1]=='A':
					self.dcload.SetMode('cc')
					self.dcload.SetCCCurrent(float(command[0:-1]))
					self.dcload.loadFunc = doNothing
			except:
				traceback.print_exc()
				pass
			command = input('')
		self.running = False
		print('Q PRESSED')

	def run(self):
		avgTime = 10
		deltaT = 0.1
		numInds = int(avgTime/deltaT)
		self.running = True
		prevTot = 0;
		prevT = time.time()
		currents = np.zeros(numInds)
		powers = np.zeros(numInds)
		H2vals = np.zeros(numInds)
		ind = 0
		eff = 0
		leak = 0
		timeToReset = time.time()+999999999999

		if (self.dcload is None or self.alicat is None):
			return
		while(self.running):
			try:
				if (self.dcload.mostRecentData[0]<1 and self.dcload.mostRecentData[1]>3): # dc load needs to be reset
					self.dcload.SetMode('cw')
					self.dcload.SetCWPower(0)
					timeToReset = time.time()+.25
				if time.time()>timeToReset:
					if not (self.dcload.mostRecentData[0]<1 and self.dcload.mostRecentData[1]>3):
						self.dcload.SetMode('cw')
						self.dcload.SetCWPower(self.setPower)
						timeToReset = time.time()+999999999999
					else:
						timeToReset = time.time()+.25
			except IndexError:
				print('no recent data yet')
				pass
			except:
				print("error with resetting DC load")
				traceback.print_exc()
			try:
				while(time.time()-prevT<deltaT):
					time.sleep(0.001)
				H2vals[ind] = self.alicat.mostRecentData[4]
				powers[ind] = self.dcload.mostRecentData[2]
				currents[ind] = self.dcload.mostRecentData[1]
				H2cons = H2vals[ind]-H2vals[ind-numInds+1]
				energy = np.sum(powers)*deltaT
				charge = np.sum(currents)*deltaT
				eff = 0.95*(eff) + 0.05*(energy / (H2cons*119.93e3))
				h2charge = (2*1.60217662e-19*6.022e23*(H2cons/2.01588)) / 20 # 20 stacks in series
				leak = 0.95*(leak) + 0.05*((h2charge-charge)/h2charge)
				print('%.2fs\tEff: %.5f\tleak: %.5f'%(time.time()-self.startT,eff,leak))
				prevTot = H2cons
				prevT = time.time()
				ind = (ind+1)%(numInds)
			except:
				# traceback.print_exc()
				pass

def checkUSBnames():
	print('Identifying serial ports...')
	goodPorts = []
	toRet = {'alicat':None,'BK':None,'Controller':None}
	for dev in list_ports.grep('usb*'):
		port, desc, misc = dev
		goodPorts.append(port)
	toRet['alicat'] = scanForComm(goodPorts,'alicat')
	toRet['Controller'] = scanForComm(goodPorts,'Controller')
	toRet['BK'] = scanForComm(goodPorts,'BK')
	for port in goodPorts:
		print('\tport '+port+' was not recognized')
	# rescan - comment these lines out if you don't want to rescan
	# for device in ['alicat','BK','Controller']:
	# 	while(toRet[device] is None):
	# 		print(device,' not found - try again?')
	# 		repeat = input()
	# 		if not (repeat[0]=='y' or repeat[0]=='Y'):
	# 			break;
	# 		toRet[device] = scanForComm(goodPorts, device)
	# end rescan section
	print('Finished identifying serial ports')
	return toRet

def scanForComm(goodPorts,name):
	info = {'alicat':[AlicatInterface,'Alicat flowmeter'],
					'Controller':[ControllerInterface,'FC Controller'],
					'BK':[BKInterface,'BK DC load']}
	commClass = info[name][0]
	text = info[name][1]
	for port in goodPorts:
		comm = commClass(port)
		isComm = comm.checkValidSerial()
		if (isComm):
			print('\tport '+port+' is a',text)
			goodPorts.remove(port)
			return comm
	return None

def powerStepLoad(t,dcload):
	if (t%15 < 0.2):
		dcload.SetCWPower(int((t%150)/3))

def main():
	comms = checkUSBnames()
	dcload = comms['BK'] if comms['BK'] is not None else None
	alicat = comms['alicat'] if comms['alicat'] is not None else None
	controller = comms['Controller'] if comms['Controller'] is not None else None
	mainP = MainManager(dcload,alicat,controller)
	mainP.startAll()
	time.sleep(1)
	threading.Thread(target=mainP.run).start()
	usrThread = threading.Thread(target=mainP.checkInputs)
	usrThread.start()
	usrThread.join()
	mainP.saveAll()
	mainP.stopAll()

if __name__ == '__main__':
	main()
	print('finished - exiting')
	exit(0)