#!/bin/bash
#Arguments:
#	$1 = kiosk registration key

_NAME=$(<kiosk_name.txt)
_NEWKEY=$(< /dev/urandom tr -dc _A-Z-a-z-0-9 | head -c10)
echo $_NEWKEY > secret_key.txt
_WEBROOT=$(<websiteRoot.txt)
_WEBPAGE=$_WEBROOT"kiosks/hardwareRegister/"
_RES=$(curl -s -X POST -H "Content-Type: multipart/form-data" -F "kiosk_name=$_NAME" -F "secret_key=$_NEWKEY" -F "registration_key=$1" $_WEBPAGE)

echo $_RES

