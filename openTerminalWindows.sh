#!/bin/bash

curdir=`pwd`
osascript -e 'tell app "Terminal"
	set bounds of window 1 to {0, 350, 800, 650}
end tell'
osascript -e 'tell app "Terminal"
	do script "cd '$curdir';tail -f log.txt"
	set bounds of window 1 to {0, 050, 800, 350}
end tell'
osascript -e 'tell app "Terminal"
	do script "cd '$curdir'/data;tail -f H2flow.txt"
	set bounds of window 1 to {800, 050, 1600, 350}
end tell'
osascript -e 'tell app "Terminal"
	do script "cd '$curdir'/data;tail -f powerstats.txt"
	set bounds of window 1 to {800, 350, 1600, 650}
end tell'
osascript -e 'tell app "Terminal"
	do script "cd '$curdir'/data;tail -f controller.txt"
	set bounds of window 1 to {800, 650, 1600, 950}
end tell'
