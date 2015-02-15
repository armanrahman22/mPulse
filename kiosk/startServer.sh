#!/bin/bash
cd /usr/local/kiosk/webpy
python code.py
_DATE=$(date +%F@%H:%M:%S)
echo "$_DATE: Auto-started webpy server..." >> log.txt

#matchbox-window-manager &
#midori -e Fullscreen -a http://dev.mobilitylab.org/TransitScreen/screen/index/11

#echo "$_DATE: Auto-started Midori..." >> log.txt