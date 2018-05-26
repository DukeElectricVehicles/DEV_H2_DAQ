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
from scipy.io import savemat, loadmat
import traceback
from functools import partial

class MainManager():
	def __init__(self, dcload, alicat, controller):
		self.dcload = dcload
		self.alicat = alicat
		self.controller = controller
		self.running = True
		self.startT = time.time()

	def startAll(self):
		startT = self.startT
		for comm in [self.dcload,self.alicat,self.controller]:
			if comm is not None:
				comm.resetData()
				comm.start(startT=startT)

	def saveAll(self):
		toSave = {}
		for comm in [self.dcload,self.alicat,self.controller]:
			if comm is not None:
				toSave[comm.saveName] = comm.allData
				# comm.save()
		savemat('data/data',toSave)
	def clearAllData(self):
		for comm in [self.dcload,self.alicat,self.controller]:
			if comm is not None:
				comm.resetData(startT=self.startT)

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
				if command=='b':
					self.dcload.SetMode('cv')
					self.dcload.SetCVVoltage(0)
					self.dcload.loadFunc = simStepLoad
					print('registered sim command')
				if command=='matlab':
					self.startT = time.time()
					self.clearAllData()
					Ts,Vs,Is,Ps = importMatlabCurve('simulationProfiles/Galot_basic2_noisy.mat')
					self.dcload.loadFunc = partial(simStepData,Ts=Ts,Vs=Vs,Is=Is,Ps=Ps)
					print('registered matlab simulation command')
				if command=='s':
					self.saveAll()
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
		instEff = 0
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
				eff = 0.95*(eff if eff<100 else 0.5) + 0.05*(energy / (H2cons*119.93e3))
				h2charge = (2*1.60217662e-19*6.022e23*(H2cons/2.01588)) / 20 # 20 stacks in series
				leak = 0.95*(leak if leak<100 else 0.1) + 0.05*((h2charge-charge)/h2charge)
				instEff = 0.99*(instEff if instEff<100 else 0.5) + 0.01*(self.dcload.mostRecentData[2]/(self.alicat.mostRecentData[3]*1e-3*119.93e3))
				print('%7.2fs\tEff: %.5f\t%.5f\tleak: %.5f'%(time.time()-self.startT,instEff,eff,leak))
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
	if (t%20 < 0.2):
		dcload.SetCWPower(int((t%160)/3))

tSim = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50,
	51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100,
	101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150,
	151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200,
	201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250,
	251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300
	])
vSim = np.array([16.48, 16.45, 16.42, 16.40, 16.37, 16.34, 16.31, 16.29, 16.26, 16.23, 16.21, 16.18, 16.15, 16.13, 16.10, 16.07, 16.05, 16.02, 16.00, 15.97, 15.95, 15.92, 15.90, 15.87, 15.85, 15.82, 15.80, 15.77, 15.75, 15.73, 15.70, 15.68, 15.65, 15.63, 15.61, 15.58, 15.56, 15.54, 15.52, 15.49, 15.47, 15.45, 15.43, 15.40, 15.38, 15.36, 15.34, 15.32, 15.30, 15.27, 15.25, 15.23, 15.21, 15.19, 15.17, 15.15, 15.13, 15.11, 15.09, 15.07, 15.05, 15.03, 15.01, 14.99, 14.97, 14.95, 14.93, 14.91, 14.89, 14.88, 14.87, 14.87, 14.87, 14.88, 14.90, 14.91, 14.93, 14.94, 14.96, 14.97, 14.99, 15.00, 15.01, 15.03, 15.04, 15.05, 15.07, 15.08, 15.09, 15.11, 15.12, 15.13, 15.14, 15.16, 15.17, 15.18, 15.19, 15.21, 15.22, 15.23, 15.24, 15.25, 15.27, 15.28, 15.29, 15.30, 15.31, 15.32, 15.33, 15.34, 15.36, 15.37, 15.38, 15.39, 15.40, 15.41, 15.42, 15.43, 15.44, 15.45, 15.46, 15.47, 15.48, 15.49, 15.50, 15.51, 15.52, 15.53, 15.54, 15.55, 15.56, 15.56, 15.57, 15.58, 15.59, 15.60, 15.61, 15.62, 15.63, 15.64, 15.64, 15.65, 15.66, 15.67, 15.68, 15.69, 15.69, 15.70, 15.71, 15.72, 15.73, 15.73, 15.74, 15.75, 15.76, 15.76, 15.77, 15.78, 15.79, 15.79, 15.80, 15.81, 15.82, 15.82, 15.83, 15.84, 15.84, 15.85, 15.86, 15.86, 15.87, 15.88, 15.88, 15.89, 15.90, 15.90, 15.91, 15.92, 15.92, 15.93, 15.94, 15.94, 15.95, 15.95, 15.96, 15.97, 15.97, 15.98, 15.98, 15.99, 16.00, 16.00, 16.01, 16.01, 16.02, 16.02, 16.03, 16.04, 16.04, 16.05, 16.05, 16.06, 16.06, 16.07, 16.07, 16.08, 16.08, 16.09, 16.09, 16.10, 16.10, 16.11, 16.11, 16.12, 16.12, 16.13, 16.13, 16.14, 16.14, 16.15, 16.15, 16.16, 16.16, 16.17, 16.17, 16.17, 16.18, 16.18, 16.19, 16.19, 16.20, 16.20, 16.20, 16.21, 16.21, 16.22, 16.22, 16.23, 16.23, 16.23, 16.24, 16.24, 16.25, 16.25, 16.25, 16.26, 16.26, 16.26, 16.27, 16.27, 16.28, 16.28, 16.28, 16.29, 16.29, 16.29, 16.30, 16.30, 16.30, 16.31, 16.31, 16.31, 16.32, 16.32, 16.32, 16.33, 16.33, 16.33, 16.34, 16.34, 16.34, 16.35, 16.35, 16.35, 16.36, 16.36, 16.36, 16.37, 16.37, 16.37, 16.38, 16.38, 16.38, 16.38, 16.39, 16.39, 16.39, 16.40, 16.40, 16.40, 16.40, 16.41, 16.41, 16.41, 16.41, 16.42, 16.42, 16.42, 16.43, 16.43, 16.43
	])

def simStepLoad(t,dcload):
	if (t%1 < 0.1):
		print('simStepLoad:',vSim[int(t%300)])
		dcload.SetCVVoltage(vSim[int(t%300)])
def simStepData(t,dcload,index=0,Ts=[],Vs=[],Is=[],Ps=[]):
	# define what to send to BK
	if (len(Vs)>0):
		def sendCom(i):
			print('setting V to:',Vs[i])
			dcload.SetMode('cv')
			dcload.SetCVVoltage(Vs[i])
	elif (len(Is)>0):
		def sendCom(i):
			print('setting I to:',Is[i])
			dcload.SetMode('cc')
			dcload.SetCCCurrent(Is[i])
	elif (len(Ps)>0):
		def sendCom(i):
			print('setting P to:',Ps[i])
			dcload.SetMode('cw')
			dcload.SetCWPower(Ps[i])
	else:
		print('invalid sim data - doing nothing')
		return 0

	# print(index,(t%Ts[-1]),Ts[index])
	if ((t%Ts[-1])>Ts[index] and (t%Ts[-1]<Ts[(index+1)%len(Ts)])):
		sendCom(index)
		return (index+1)%(len(Ts)-1) # don't do the last one
	else:
		return index
def importMatlabCurve(filename):
	data = loadmat(filename)
	tRet = []
	VRet = []
	IRet = []
	PRet = []
	if ('V' in data.keys() or 'Vs' in data.keys()):
		VRet = data['V']
		VRet = VRet.reshape(VRet.size)
	elif ('I' in data.keys() or 'Is' in data.keys()):
		IRet = data['I']
		IRet = IRet.reshape(IRet.size)
	elif('P' in data.keys() or 'Ps' in data.keys()):
		PRet = data['P']
		PRet = PRet.reshape(PRet.size)
	else:
		print('import error - no load variable found in matlab file: ',data.keys())
		print('cannot continue with import - returning default load profile')
		return tSim,vSim,Iret,Pret
	if ('t' in data.keys()):
		tRet = data['t']
		tRet = tRet.reshape(tRet.size)
	else:
		print('import error - matlab file has no t column, using 1s steps')
		tRet = np.array(range(max(len(VRet),len(IRet),len(PRet))))
	return tRet,VRet,IRet,PRet

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
	with open('log.txt', 'wb') as outf:
		# os.dup2(inf.fileno(), 0)
	  os.dup2(outf.fileno(), 1)
	  # os.dup2(outf.fileno(), 2)
	main()
	print('finished - exiting')
	exit(0)