Software side of Duke Electric Vehicle's H2 system data collection

Currently on v1

Runs on python 3.x

## Mac users:
in terminal, type:

	* ./openTerminalWindows.sh
	* python3 main.py

if the shell script won't run, use chmod to elevate permissions:

```bash
chmod +x openTerminalWindows.sh
```

if the python3 is having issues, make sure you have a version of python 3.x

if python complains of missing dependencies, install them.  notable ones include

	* pyserial
	* numpy
	* scipy

## Windows users:
idk how windows works, but some changes are probably needed in the 'checkUSBnames()' function of main.py.  Specifically, this line:

```python
	for dev in list_ports.grep('usb*'):
```

maybe something like

```python
	for dev in list_ports.grep('COM*'):
```

would work, but not sure.

You'll have to open the relevant log files in the data folder to watch real-time data collection.

## Python code overview
main.py is the main python script - it will scan serial ports and start the threads to collect data.  It will then save and exit when 'q' is typed in the command console.

Data is logged to individual text files:

	* log.txt - general efficiency numbers and useful messages
	* data/H2flow.txt - data from the Alicat flowmeter
	* data/powerstats.txt - data from the BKPrecision DC load
	* data/controller.txt - data from the FC controller (not yet implemented)

and a master matlab file is saved in data/data.mat at program exit.

BK/ folder contains the python files for the BK DC load

_____Interface.py files are for managing the serial devices

arduinoBarebones is the arduino code used for controlling the fuel cell.