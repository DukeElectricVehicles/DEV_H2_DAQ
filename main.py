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

	def startAll(self):
		if self.dcload is not None:
			self.dcload.start()
		if self.alicat is not None:
			self.alicat.start()
		if self.controller is not None:
			self.controller.start()

	def stopAll(self):
		if self.dcload is not None:
			self.dcload.stop()
		if self.alicat is not None:
			self.alicat.stop()
		if self.controller is not None:
			self.controller.stop()

	def checkInputs(self): # blocking
		command = ''
		print('starting input checking')
		def doNothing(t,dcload):
			return
		while command!='q':
			print(command)
			if command=='q':
				break
			try:
				if command[-1]=='W':
					self.dcload.SetMode('cw')
					self.dcload.SetCWPower(float(command[0:-1]))
					self.dcload.loadFunc = doNothing # don't change after set
				elif command[-1]=='V':
					self.dcload.SetMode('cv')
					self.dcload.SetCVVoltage(float(command[0:-1]))
					self.dcload.loadFunc = doNothing
				elif command[-1]=='A':
					self.dcload.SetMode('cc')
					self.dcload.SetCCCurrent(float(command[0:-1]))
					self.dcload.loadFunc = doNothing
			except:
				pass
			command = input('')
		self.running = False
		print('Q PRESSED')
		self.stopAll()

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

		if (self.dcload is None or self.alicat is None):
			return
		while(self.running):
			while(time.time()-prevT<deltaT):
				time.sleep(0.001)
			H2vals[ind] = float(self.alicat.mostRecentData[5])
			powers[ind] = self.dcload.mostRecentData[2]
			currents[ind] = float(self.dcload.mostRecentData[1])
			H2cons = H2vals[ind]-H2vals[ind-numInds+1]
			energy = np.sum(powers)*deltaT
			charge = np.sum(currents)*deltaT
			eff = 0.95*(eff) + 0.05*(energy / (H2cons*0.08235*119.93e3))
			h2charge = (2*1.60217662e-19*6.022e23*(H2cons*0.08235/2.01588)) / 20 # 20 stacks in series
			leak = 0.95*(leak) + 0.05*((h2charge-charge)/h2charge)
			print('Efficiency:',round(eff,5),'\testimated leakage percent',round(leak,5),'\t',charge)
			prevTot = H2cons
			prevT = time.time()
			ind = (ind+1)%(numInds)

def checkUSBnames():
	print('Identifying serial ports...')
	goodPorts = []
	toRet = {'alicat':None,'BK':None,'Controller':None}
	for dev in list_ports.grep('usbserial*'):
		port, desc, misc = dev
		goodPorts.append(port)
	for port in goodPorts:
		alicat = AlicatInterface(port)
		isAlicat = alicat.checkValidSerial()
		load = BKInterface(port)
		isBK = load.checkValidSerial()
		controller = ControllerInterface(port)
		isController = controller.checkValidSerial()

		if (isAlicat and (not isBK) and (not isController)):
			print('\tport '+port+' is an Alicat flowmeter')
			toRet['alicat'] = port
		elif ((not isAlicat) and isBK and (not isController)):
			print('\tport '+port+' is a BK DC load')
			toRet['BK'] = port
		elif((not isAlicat) and (not isBK) and isController):
			print('\tport '+port+' is a FC Controller')
			toRet['Controller'] = port
		elif((not isAlicat) and (not isBK) and (not isController)):
			print('\tport '+port+' cannot be recognized')
		else:
			print('\tport '+port+' was identified as multiple devices...')
			print('\t\t',isAlicat,isBK,isController)
	print('Finished identifying serial ports')
	return toRet

def main():
	ports = checkUSBnames()
	dcload = BKInterface(port=ports['BK']) if ports['BK'] is not None else None
	alicat = AlicatInterface(port=ports['alicat']) if ports['alicat'] is not None else None
	controller = ControllerInterface(port=ports['Controller']) if ports['Controller'] is not None else None
	mainP = MainManager(dcload,alicat,controller)
	mainP.startAll()
	time.sleep(1)
	threading.Thread(target=mainP.run).start()
	usrThread = threading.Thread(target=mainP.checkInputs)
	usrThread.start()
	usrThread.join()
	mainP.stopAll()

if __name__ == '__main__':
	main()
	print('finished - exiting')
	exit(0)