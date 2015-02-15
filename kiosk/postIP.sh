#!/bin/bash
_NAME=$(<kiosk_name.txt)
_IP=$(hostname -I)
_OLDKEY=$(<secret_key.txt)
_NEWKEY=$(< /dev/urandom tr -dc _A-Z-a-z-0-9 | head -c10)
_WEBROOT=$(<websiteRoot.txt)
_WEBPAGE=$_WEBROOT"manage/"

#-H "Content-Type: multipart/form-data"
_RES=$(curl -s -X POST -H "Content-Type: multipart/form-data" -F "kiosk_name=$_NAME" -F "ip=$_IP" -F "old_secret_key=$_OLDKEY" -F "new_secret_key=$_NEWKEY" -F "logfile=@log.txt" $_WEBPAGE)
_DATE=$(date +%F@%H:%M:%S)
if [ "$_RES" = "success" ]
then
	echo $_NEWKEY > secret_key.txt
	echo "" > log.txt
	echo "$_DATE: Posted IP and Log File Successfully" >> log.txt
elif [ "$_RES" = "no log file uploaded" ]
then
	echo $_NEWKEY > secret_key.txt
	echo "$_DATE: IP Post Error: $_RES" >> log.txt
elif [ "$_RES" = "" ]
then
	echo "$_DATE: IP Post Error: likely not connected to the internet" >> log.txt
else
	echo "$_DATE: IP Post Error: $_RES" >> log.txt
fi
echo "$_RES"