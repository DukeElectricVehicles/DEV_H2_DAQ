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

with open('log.txt', 'wb') as outf:
    # os.dup2(inf.fileno(), 0)
    os.dup2(outf.fileno(), 1)
    # os.dup2(outf.fileno(), 2)

class MainManager():
	def __init__(self, dcload, alicat, controller):
		self.dcload = dcload
		self.alicat = alicat
		self.controller = controller

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
	return toRet

def main():
	ports = checkUSBnames()
	dcload = BKInterface(port=ports['BK']) if ports['BK'] is not None else None
	alicat = AlicatInterface(port=ports['alicat']) if ports['alicat'] is not None else None
	controller = ControllerInterface(port=ports['Controller']) if ports['Controller'] is not None else None
	mainP = MainManager(dcload,alicat,controller)
	mainP.startAll()
	time.sleep(1)
	command = ''
	setConst = False
	def doNothing(t,dcload):
		return
	while command!='q':
		if command=='q':
			break
		try:
			if command[-1]=='W':
				dcload.SetMode('cw')
				dcload.SetCWPower(float(command[0:-1]))
				dcload.loadFunc = doNothing # don't change after set
			elif command[-1]=='V':
				dcload.SetMode('cv')
				dcload.SetCVVoltage(float(command[0:-1]))
				dcload.loadFunc = doNothing
			elif command[-1]=='A':
				setConst = True
				dcload.SetMode('cc')
				dcload.SetCCCurrent(float(command[0:-1]))
				dcload.loadFunc = doNothing
		except:
			pass
		command = input('')
	mainP.stopAll()

if __name__ == '__main__':
	main()
	print('finished - exiting')