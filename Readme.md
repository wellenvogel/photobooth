Simple Photobooth with libgphoto2 and pygame

Needs libgphoto2-2.10 (Canon autofocus)
Install:

```
sudo apt-get install python-dev libgphoto2-dev python-pip
#install latest libgphoto2
wget https://raw.githubusercontent.com/gonzalo/gphoto2-updater/master/gphoto2-updater.sh && chmod +x gphoto2-updater.sh && sudo ./gphoto2-updater.sh
sudo pip install gphoto2
```
start with ./pb.py

Opens a WebServer at port 8082 with a simple slide show

On the pi in non - x environment:
edit /boot/config.txt
and enable the framebuffer:
```
framebuffer_width=1680
framebuffer_height=1050
```

Adapt this to your screen.
