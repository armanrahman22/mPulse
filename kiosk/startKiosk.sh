#!/bin/bash
cd /usr/local/kiosk && ./postIP.sh
sudo /usr/local/kiosk/startServer.sh & #Start server
#Disable screensaver
xset s off
xset -dpms
xset s noblank
#Start browser
matchbox-window-manager & midori -e Fullscreen -a http://0.0.0.0:8080 --block-uris='^([^h]|h($|[^t]|t($|[^t]|t($|[^p]|p($|[^:]|:($|[^/]|/($|[^/]|/($|[^0]|0($|[^\.]|\.($|[^0]|0($|[^\.]|\.($|[^0]|0($|[^\.]|\.($|[^0]|0($|[^:]|:($|[^8]|8($|[^0]|0($|[^8]|8($|[^0])))))))))))))))))))'
