#!/bin/bash

#Setup script for the M-Pulse Kiosk on a Raspberry Pi
#	Installs required dependencies
#	Moves kiosk files to correct location
#	Sets up certain cron jobs for auto-update and remote kiosk management

#Arguments:
#	$1 = managing user's username on the Raspberry Pi
#	$2 = kiosk name
#	$3 = kiosk registration key

echo "Starting install..."

if [ $1 == "kiosk" ]
then
	echo "You cannot have the username kiosk, as this is reserved for the auto-login kiosk user. Please change your account name and rerun the script"
	exit 2
fi

#Install and configure SSH
echo "Installing and starting SSH..."
apt-get install ssh
update-rc.d ssh defaults
/etc/init.d/ssh start

#Install chromium
#echo "Installing chromium web browser..."
#apt-get install chromium-browser

#Install midori
echo "Installing midori web browser..."
apt-get install midori

#Install pip
echo "Installing pip..."
apt-get install python-pip

#Install pySerial
echo "Installing pySerial..."
pip install pyserial

#Install web.py
echo "Installing web.py..."
pip install web.py

#Get RPi.GPIO libraries
echo "Installing python-dev and RPi.GPIO libraries..."
apt-get install python-dev
apt-get install python-rpi.gpio


#Install python SPI
echo "Installing python SPI and I2C libraries..."
#Comment out disable lines
sudo sed -e "s%^blacklist spi-bcm2708$%#&%" -e  "s%^blacklist i2c-bcm2708$%#&%"  -i /etc/modprobe.d/raspi-blacklist.conf

#Add i2c lines to config file
sh -c '(echo "i2c-bcm2708"; echo "i2c-dev") >> /etc/modules'

#Install i2c
apt-get install python-smbus
apt-get install i2c-tools

#Install python-spi
cd python-spi
python setup.py install
cd ../

#Install arduino
#echo "Installing Arduino IDE..."
#apt-get install arduino

#Install alamode libraries
#echo "Installing Alamode Libraries..."
#tar -xvzf alamode-setup.tar.gz
#cd alamode-setup
#./setup
#cd ../

#Make and give user RW permissions
echo "Making kiosk code directory with $1 as the owner and granting permissions..."
mkdir /usr/local/kiosk
chown -R $1 /usr/local/kiosk
chmod -R u+rwx /usr/local/kiosk

#Move files to the directory 
echo "Installing kiosk code files..."
unzip -o kioskCode.zip
cp -r kiosk/* /usr/local/kiosk/
cp kiosk.desktop /usr/share/xsessions/

#Make kiosk_name.txt file, secret_key.txt, and logt.txt file
# Attempt to register the kiosk
echo "Attempting to put kiosk online. Registering kiosk..."

cd /usr/local/kiosk
echo "$2" > kiosk_name.txt
echo '' > secret_key.txt
echo '' > log.txt

#Get kiosk online and update code
chmod +x registerKiosk.sh
$_RES=$(./registerKiosk.sh "$3")
if [ "$_RES" = "Kiosk does not exist. Make sure to register your kiosk on the website." ]
then
	echo "The server returned: $_RES"
	echo "This could be due to a name misspelling. Please re-enter the kiosk name as it was registered on the website:"
	read name
	echo "$name" > kiosk_name.txt
	$_RES=$(./registerKiosk.sh "$3")
	echo "The server returned: $_RES"
	if [ "$_RES" != "Kiosk successfully registered" ]
	then
		echo "Continuing install. If kiosk did not register, please try again later using the registerKiosk.sh script. Make sure the kiosk name is spelled correctly in kiosk_name.txt and then call it with ./registerKiosk.sh $3"
	fi
	
	
elif [ "$_RES" = "Registration key incorrect" ]
then
	echo "The server returned: $_RES"
	echo "Please re-enter your registration key as it was given to you from the website."
	read registration_key
	_RES=$(./registerKiosk.sh "$registration_key")
	echo "The server returned: $_RES"
	if [ "$_RES" != "Kiosk successfully registered" ]
	then
		echo "Continuing install. If kiosk did not register, please try again later using the registerKiosk.sh script. Make sure the kiosk name is spelled correctly in kiosk_name.txt and then call it with ./registerKiosk.sh $registration_key"
	fi
	
else
	echo "The server returned: $_RES"
fi
echo "Posting IP address..."
./postIP.sh
chmod +x updateCode.sh
./updateCode.sh

#Add kiosk user
echo "Adding anonymous kiosk user..."
useradd kiosk
echo -e "kiosk\nkiosk" | passwd kiosk
mkdir /home/kiosk
chown kiosk:users /home/kiosk

#Add cron jobs
echo "Configuring cron jobs for remote management and starting cron..."
cron 
lines=( "0 0-23/2 * * * cd /usr/local/kiosk  && ./postIP.sh >> /usr/local/kiosk/cronLog.txt  2>&1" "@daily cd /usr/local/kiosk && chmod +x updateCode.sh  && ./updateCode.sh >> /usr/local/kiosk/cronLog.txt  2>&1" )
for line in "${lines[@]}"
do
	:
	
	(crontab -l; echo "$line" ) | crontab -
done


#Add server auto-start
echo "Adding kiosk auto-start functionality..."
#Installing matchbox
echo "Installing matchbox..."
apt-get install matchbox

echo "Allowing kiosk user to start the server, post IP, and reboot..."
echo "kiosk ALL=(ALL:ALL) NOPASSWD: /usr/local/kiosk/startServer.sh, /usr/local/kiosk/postIP.sh" >> /etc/sudoers.d/sudoStartServer
groupadd kioskFileAccess
usermod -a -G kioskFileAccess kiosk
usermod -a -G kioskFileAccess $1
chgrp kioskFileAccess /usr/local/kiosk/log.txt
chmod g+rwx /usr/local/kiosk/log.txt
chgrp kioskFileAccess /usr/local/kiosk/secret_key.txt
chmod g+rwx /usr/local/kiosk/secret_key.txt
chgrp kioskFileAccess /usr/local/kiosk/webpy/log.txt
chmod g+rwx /usr/local/kiosk/webpy/log.txt

echo "Setting GUI to start automatically... "
update-rc.d lightdm enable 2

echo "Setting ctrl+alt+backspace to quit x server..."
if grep -q "terminate:ctrl_alt_bksp" /etc/default/keyboard
then
    : #already found
else
    #fine line number
    LINE_NUM=$(awk '$0 ~ str{print NR}' str="XKBOPTIONS" /etc/default/keyboard)
    LINE=$(awk '$0 ~ str{print}' str="XKBOPTIONS" /etc/default/keyboard)
    if [ "$LINE" == "XKBOPTIONS=\"\"" ]
    then
    	LINE="XKBOPTIONS=\"terminate:ctrl_alt_bksp\""
    else
    	LINE="${LINE%?},terminate:ctrl_alt_bksp\""
    fi
    sed -i "$LINE_NUM s/.*/$LINE/" /etc/default/keyboard
fi
#Find line XKBOPTIONS in /etc/default/keyboard and add terminate:ctrl_alt_bksp

echo "Attempting to download most recent version of kiosk code..."
cd /usr/local/kiosk
chmod +x updateCode.sh
./updateCode.sh

echo "To set kiosk user to login automatically, open /etc/lightdm/lightdm.conf and uncomment or add/modify the lines autologin-user=kiosk, autologin-user-timeout=0, autologin-session=kiosk"
echo "Kiosk user's username is kiosk, password is kiosk"

#Finished
echo "Install finished. Please navigate to /usr/local/kiosk/webpy/settings.py after reboot to modify custom settings."
echo "System will reboot in 5 seconds..."
sleep 5
reboot


