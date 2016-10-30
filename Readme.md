#Simple Photobooth with libgphoto2 and pygame

GUI for taking photos with an USB enabled camera and providing them for a slide show.

You need:


1. A Camera that supports preview and image capturing via USB. For compatible models refer to http://gphoto.org/proj/libgphoto2/support.php. Tested with Canon EOS70D.
   Typically you would need some power supply for your camera.
2. A RaspberryPi (preferrable model3) - see e.g. https://www.reichelt.de/?ARTICLE=164977
3. Some USB power supply for the raspberry
4. A wireless num-keypad  - e.g. https://www.amazon.de/gp/product/B00KYPJAMK (or some other keys for shooting)
5. A HDMI Monitor attached to the PI
6. a SD image for the raspi that supports a Wifi access point (I use my own images from http://www.wellenvogel.net/software/avnav/downloads/index.php#Images)
7. libgphoto2 (see below)
8. this software

##Installation

Set up your raspberry using the SD image and try if the wireless LAN is working (for instructions for my image see http://www.wellenvogel.net/software/avnav/index.php) 

Connect the pi with an ethernet cable to the internet (or use a WLAN USB adapter and connect using the avnav app).

Install the LATEST libgphoto2- (used: 2.5.10) - this solves e.g.  Canon autofocus issues. Therefore login to the pi (ssh or console), user pi, pw: raspberry 

```
sudo apt-get install python-dev libgphoto2-dev python-pip python-pygame python-netifaces
#install latest libgphoto2
wget https://raw.githubusercontent.com/gonzalo/gphoto2-updater/master/gphoto2-updater.sh && chmod +x gphoto2-updater.sh && sudo ./gphoto2-updater.sh
#select "LATEST" for the libgphoto version. The compilation afterwards will take some time
sudo pip install gphoto2
sudo pip install zeroconf
```
Potentially you must set a correct date before running pip install - otherwise you could run into cert issues

Copy the software to the pi:
```
cd
git clone https://github.com/wellenvogel/photobooth.git

```
Alternatively download the zip archive and unpack it to /home/pi/photobooth.


##Install the startup service

```
cd
cd photobooth
sudo cp avpb.service /usr/lib/systemd/system
sudo systemctl enable avpb
```

##Setup the screen
On the pi in non - x environment:
edit (as root) /boot/config.txt
and enable the framebuffer:
```
framebuffer_width=1680
framebuffer_height=1050
```

Adapt this to your screen. If you have another screen size, just change this in pb.py too.

Afterwards you need to reboot.

The box should start up.

##Testing

To try a start from the commandline you can use ssh to login to the pi and run the software directly
```
sudo /home/pi/photobooth/pb.py
```


##Functions

You can use the keys as described for immediate shoot, delayed shoot (ENTER and +). After a picture has been taken it is shown at the right side. By clicking 0 it will get a green border and will be available for the slide show.

The software opens a WebServer at port 8082 with a simple slide show. So just use your browser to navigate to http://yourip:8082., yourip will be 192.168.20.10 when using the avnav image.
You can add ?time=6000 to change the slideshow time (in ms).
The photos will be found at /home/pi/photobooth/release afterwards.



