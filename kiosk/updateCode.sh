#!/bin/bash
_NAME=$(<kiosk_name.txt)
_SECRETKEY=$(<secret_key.txt)
_DATE=$(date +%F@%H:%M:%S)
_WEBROOT=$(<websiteRoot.txt)
_WEBPAGE=$_WEBROOT"updateCode/"
curl -s -o newCode.zip --data "kiosk_name=$_NAME&secret_key=$_SECRETKEY" $_WEBPAGE
echo "$_DATE: Auto-updating kiosk code" >> log.txt
{
	unzip -q -o newCode.zip -x kiosk/kiosk_name.txt kiosk/secret_key.txt kiosk/webpy/settings.py kiosk/webpy/IOinterruptHandlers.py -d ../ > /dev/null 2>&1 
} || {
	_ERROR=$(cat newCode.zip)
	if [ "$_ERROR" = "" ]
	then
		_ERROR=$(echo 'Likely not connected to the internet')
	fi
	echo "$_DATE: Auto-Update Error: $_ERROR" >> log.txt
	echo "$_ERROR"
}
rm newCode.zip