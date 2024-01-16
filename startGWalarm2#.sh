#!/bin/bash
#xdotool windowminimize $(xdotool getactivewindow)
echo $(tvservice -s)
state=$(tvservice -s)
state2=${state:6:4}
echo $state2
if [ $state2 == '0x40' ]
	then
	echo HDMI not active
	#export VC_DISPLAY=5
	sed -i -e 's/#//g' ~/.kivy/config.ini
elif [ $state2 == '0x12' ]
	then
	echo HDMI active
	sed -i -e 's/#//g' ~/.kivy/config.ini
	sed -i -e 's/mtdev_%(name)s/#mtdev_%(name)s/g' ~/.kivy/config.ini
	sed -i -e 's/hid_%(name)s/#hid_%(name)s/g' ~/.kivy/config.ini
else
	echo Default configuration settings mouse + keyboard
	sed -i -e 's/#//g' ~/.kivy/config.ini
	sed -i -e 's/mtdev_%(name)s/#mtdev_%(name)s/g' ~/.kivy/config.ini
	sed -i -e 's/hid_%(name)s/#hid_%(name)s/g' ~/.kivy/config.ini
fi
sudo -E python3 /home/pi/Documents/GIT/gwalarm/GWalarm_screens.py