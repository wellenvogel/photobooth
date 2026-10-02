#! /usr/bin/env python
# vim: sw=2 ts=2 et
import pygame
import traceback
import sys
import logging
import io
import os
import threading
from time import sleep
import gphoto2 as gp
import time
import re
import shutil
from pb_server import *
import signal
hasInterfaces=False
try:
  import netifaces
  hasInterfaces=True
except:
  pass

PORT=8082
#adapt to your needs
SCREENW=1680
SCREENH=1050

#SCREENW=800
#SCREENH=600

DELAY=4000 #delay in ms


PROGDIR=os.path.dirname(os.path.realpath(__file__))
TMPPATH=os.path.join(PROGDIR,"tmp")
RELEASEPATH=os.path.join(PROGDIR,"release")

IMGPREFIX="PB"

keymappings={
  'quit': [pygame.K_q],
  'shoot': [pygame.K_SPACE,pygame.K_KP_ENTER,pygame.K_RETURN],
  'delay':[pygame.K_PLUS,pygame.K_KP_PLUS],
  'release':[pygame.K_0,pygame.K_KP0],
  'delete':[pygame.K_DELETE,pygame.K_KP_PERIOD,pygame.K_COMMA],
  'focus':[pygame.K_f,pygame.K_KP2]
}





AREA_PREVIEW=1
AREA_PICTURE=2
AREA_INFO=3
AREA_DELAY=4
AREA_TITLE_LEFT=5
AREA_TITLE_RIGHT=6
AREA_KEYS_LEFT=7
AREA_KEYS_RIGHT=8


class Area:
  def __init__(self,left,top,width,height,fontsize=20):
    self.width=width
    self.height=height
    self.top=top
    self.left=left
    self.fontsize=fontsize
  def getRect(self):
    return pygame.Rect(self.left,self.top,self.width,self.height)

#the next 2 values are used for the area definitions
#if they differ from the screen definitions, the areas will be recomputed internally
AREA_W=1680
AREA_H=1050
AREAS={
  AREA_PREVIEW: Area(10,10,800,540),
  AREA_PICTURE: Area(820,10,800,540),
  AREA_DELAY: Area(20,580,760,55),
  AREA_TITLE_LEFT: Area(20,680,760,40,40),
  AREA_TITLE_RIGHT: Area(840,680,760,40,40),
  AREA_KEYS_LEFT: Area(20,780,760,34,32),
  AREA_KEYS_RIGHT: Area(840,780,760,34,32),
  AREA_INFO: Area(20,976,1640,26,20)
}

def correctAreas():
  if SCREENH==AREA_H and SCREENW == AREA_W:
    return
  fh =float(SCREENW)/float(AREA_W)
  fw=float(SCREENH)/float(AREA_H)
  f=fh
  if fw < f:
    f=fw
  leftOffset=(SCREENW-AREA_W*f)/2
  topOffset=(SCREENH-AREA_H*f)/2
  for k in AREAS.keys():
    area=AREAS[k]
    area.left=int(area.left*f+leftOffset)
    area.top=int(area.top*f+topOffset)
    area.height=int(area.height*f)
    area.width=int(area.width*f)
    area.fontsize=int(area.fontsize*f)


def getKeyFunction(key):
  if key is None:
    return None
  print("##KeyCode %d" % (key))
  for kf in keymappings.keys():
    klist=keymappings[kf]
    for kv in klist:
      if kv == key:
        return kf
  return None

class Info:
  def __init__(self):
    self.camera="----"
    self.numPic=0
    self.preview=""
    self.interfaces=[]
  def __str__(self):
    ifInfo=""
    if len(self.interfaces) > 0:
      ifInfo="Ip: "
      for i in self.interfaces:
        ifInfo+=i+" "
      ifInfo+="Port: %d"%(PORT)
    return "Cam:%s, %s,%d Bilder,%s"%(self.camera,self.preview,self.numPic,ifInfo)

info=Info()
screen=None
defaultBackground=None
imageNumber=None
numberOfImages=0
def pygameInit():
  global screen,defaultBackground
  pygame.init()
  screen=pygame.display.set_mode((SCREENW,SCREENH))
  pygame.display.set_caption("AV Fotobox")
  defaultBackground=screen.get_at((0,0))

def getScaleWidthHeight(surface,area):
  w=surface.get_width()
  h=surface.get_height()
  if h<=area.height and w<=area.width:
    return (w,h)
  fw=float(area.width)/float(w)
  fh=float(area.height)/float(h)
  f=fw
  if fh < fw:
    f=fh
  nw=float(w)*f
  nh=float(h)*f
  return (int(nw),int(nh))

def showPreview(data):
  global info
  try:
    imgSurf = pygame.image.load ( data)
    #screen = pygame.display.set_mode ( imgSurf.get_size() )
    w=imgSurf.get_width()
    h=imgSurf.get_height()
    info.preview="%d x %d"%(w,h)
    area=AREAS[AREA_PREVIEW]
    if (w != area.width or h != area.height):
      screen.fill(defaultBackground,area.getRect())
      (nw,nh)=getScaleWidthHeight(imgSurf,area)
      screen.blit ( pygame.transform.smoothscale ( imgSurf, (nw,nh) ),  ( area.left+(area.width-nw)/2, area.top+(area.height-nh)/2 ) )
    else:
      screen.blit ( imgSurf, ( area.left,area.top) )
  except Exception as e:
    print("Error showing preview:", e)
def showCapture(data,size=None):
  imgSurf = pygame.image.load ( data)
  #screen = pygame.display.set_mode ( imgSurf.get_size() )
  area=AREAS[AREA_PICTURE]
  if size is not None:
    if size[0] > area.width or size[1] > area.height:
      fh=float(area.height/size[1])
      fw=float(area.width/size[0])
      f=fw
      if fh < f:
        f=fw
      size[0]=int(size[0]*f)
      size[1]=int(size[1]*f)
  if size is None:
    size=getScaleWidthHeight(imgSurf,area)
  screen.fill(defaultBackground,area.getRect())
  screen.blit ( pygame.transform.smoothscale ( imgSurf, size ),  ( area.left+(area.width-size[0])/2, area.top+(area.height-size[1])/2 ) )

def showText(areaid,text,empty=True):
  area=AREAS.get(areaid)
  if area is None:
    return
  myfont = pygame.font.Font(None, area.fontsize)
  # render text
  if empty:
    screen.fill(defaultBackground,area.getRect())
  lines=text.splitlines()
  start=0
  offset=int(area.fontsize*1.1)
  for line in lines:
    label = myfont.render(line, 1, (255,255,255))
    lrect=label.get_rect()
    screen.blit(label, (area.left+(area.width-lrect.width)/2,area.top+start))
    start+=offset

def getClockFile():
  return os.path.join(PROGDIR,"clock.png")
'''
check all released images for the max number
'''
def findLastImage():
  global numberOfImages
  if not os.path.exists(RELEASEPATH):
    return 0
  files=os.listdir(RELEASEPATH)
  lastNum=0
  for file in files:
    pattern="%s-[0-9]+.JPG"%(IMGPREFIX)
    if re.match(pattern,file):
      try:
        num=int(re.sub(IMGPREFIX+"-","",file)[0:-4])
        if num > lastNum:
          lastNum=num
        numberOfImages=numberOfImages+1
      except:
        pass
  return lastNum

def getImageName(current=True):
  global imageNumber
  if imageNumber is None:
    imageNumber=findLastImage()
  if not current:
    imageNumber=imageNumber+1
  return "%s-%05d.JPG"%(IMGPREFIX,imageNumber)


class CameraCfg:
  def __init__(self,camera,context):
    self.camera=camera
    self.context=context
    self.config=None
    self.getConfig()
  def getConfig(self):
    if self.config is None:
      self.config=gp.check_result(gp.gp_camera_get_config(self.camera, self.context))
    return self.config

def focus(cameracfg:CameraCfg,callback=None):
  OK, viewfinder = gp.gp_widget_get_child_by_name(cameracfg.getConfig(), 'viewfinder')
  if OK >= gp.GP_OK:
      gp.check_result(gp.gp_widget_set_value(viewfinder,1))
      gp.check_result(gp.gp_camera_set_config(cameracfg.camera, cameracfg.getConfig(), cameracfg.context))
  OK, autofocus = gp.gp_widget_get_child_by_name(
        cameracfg.getConfig(), 'autofocusdrive') 
  if OK >= gp.GP_OK:
    gp.check_result(gp.gp_widget_set_value(autofocus, 1))
    gp.check_result(gp.gp_camera_set_config(cameracfg.camera, cameracfg.getConfig(), cameracfg.context))
    time.sleep(1)
    if callback is not None:
      callback()
    gp.check_result(gp.gp_widget_set_value(autofocus, 0))
    gp.check_result(gp.gp_camera_set_config(cameracfg.camera, cameracfg.getConfig(), cameracfg.context))


def _getPictureImpl(cameracfg:CameraCfg, target):
  retval, widget = gp.gp_widget_get_child_by_name(cameracfg.getConfig(), 'capturetarget')
  if retval >= gp.GP_OK:
    # "Internal RAM" matches the firmware string for RAM target
    gp.gp_widget_set_value(widget, "Internal RAM")
    gp.gp_camera_set_config(cameracfg.camera, cameracfg.getConfig(), cameracfg.context)
    pass
  print("Triggering shutter...")
  retval = gp.gp_camera_trigger_capture(cameracfg.camera, cameracfg.context)
  if retval < gp.GP_OK:
        print(f"Trigger failed: {gp.gp_result_as_string(retval)}")
        return  
  print("Polling PTP event stream for RAM buffer allocation...")
  timeout_ms = 2000
  start_time = time.time()
  max_wait = 10  # Seconds    
  while True:
          if time.time() - start_time > max_wait:
              print("Timeout waiting for RAM event transfer.")
              break
              
          # Poll for camera events using pointers for the type and data
          retval, event_type, event_data = gp.gp_camera_wait_for_event(cameracfg.camera, timeout_ms, cameracfg.context)
          if retval < gp.GP_OK:
              print(f"Event wait error: {gp.gp_result_as_string(retval)}")
              break
  
          # Check if a file object has been successfully created in the RAM stream
          if event_type == gp.GP_EVENT_FILE_ADDED:
              # event_data contains an object with .folder and .name attributes
              print(f"File found in RAM! Source: {event_data.folder}/{event_data.name}")
              
              # Create a blank camera file object pointer to receive the data
              retval, camera_file = gp.gp_file_new()
              if retval >= gp.GP_OK:
                  # Fetch bytes directly from RAM using GP_FILE_TYPE_NORMAL
                  retval = gp.gp_camera_file_get(
                      cameracfg.camera, 
                      event_data.folder, 
                      event_data.name, 
                      gp.GP_FILE_TYPE_NORMAL, 
                      camera_file, 
                      cameracfg.context
                  )
                  
                  if retval >= gp.GP_OK:
                      print('Copying image to', target)
                      # Save the binary stream to disk
                      retval = gp.gp_file_save(camera_file, target)
                      if retval >= gp.GP_OK:
                          print(f"Successfully downloaded to: {target}")
                  gp.gp_camera_file_delete(cameracfg.camera, event_data.folder, event_data.name, cameracfg.context)
              break
              
          elif event_type == gp.GP_EVENT_CAPTURE_COMPLETE:
              # Shutter cycle completed, continue waiting for data pipeline to clear
              continue
              
          elif event_type == gp.GP_EVENT_TIMEOUT:
              # No event received in this slice, loop again if under max_wait
              continue
          
def getPicture(cameracfg:CameraCfg):
  print('Capturing image')
  showCapture(getClockFile(),(400,400))
  pygame.display.flip()
  if not os.path.exists(TMPPATH):
      os.makedirs(TMPPATH)
  current=os.path.join(TMPPATH,getImageName())
  if os.path.exists(current):
    os.unlink(current)
  next=os.path.join(TMPPATH,getImageName(False))  
  focus(cameracfg,lambda: _getPictureImpl(cameracfg, next))
  showCapture(next)
  pygame.display.flip()
  
def checkKey():
  for event in pygame.event.get():
    if event.type == pygame.KEYDOWN:
      return event.key
  return None
'''
convert a text with lines of the form
a:b
into a dict'''
def txToDict(txt):
  lines=txt.splitlines()
  rt={}
  for line in lines:
    try:
      k,v=re.split(r"\s*:\s*",line,2)
      rt[k]=v
    except:
      pass
  return rt

def nowMs():
  return int(round(time.time() * 1000))

def waitForCamera(context):
  showText(AREA_PREVIEW,"Warte auf Kamera ")
  pygame.display.flip()
  camera = gp.check_result(gp.gp_camera_new())
  err=gp.gp_camera_init(camera, context)
  if (err < gp.GP_OK):
    if err != gp.GP_ERROR_MODEL_NOT_FOUND:
        # some other error we can't handle here
        raise gp.GPhoto2Error(err)
    return None
  camercfg=CameraCfg(camera,context)
  # required configuration will depend on camera type!
  print('Checking camera config')
  # get configuration tree
  config = camercfg.getConfig()
  # find the image format config item
  OK, image_format = gp.gp_widget_get_child_by_name(config, 'imageformat')
  if OK >= gp.GP_OK:
      # get current setting
      value = gp.check_result(gp.gp_widget_get_value(image_format))
      # make sure it's not raw
      if 'raw' in value.lower():
          raise gp.GPhoto2Error('Cannot preview raw images')
  # find the capture size class config item
  # need to set this on my Canon 350d to get preview to work at all
  OK, capture_size_class = gp.gp_widget_get_child_by_name(
      config, 'capturesizeclass')
  if OK >= gp.GP_OK:
      # set value
      value = gp.check_result(gp.gp_widget_get_choice(capture_size_class, 2))
      gp.check_result(gp.gp_widget_set_value(capture_size_class, value))
      # set config
      gp.check_result(gp.gp_camera_set_config(camera, config, context))
  OK,txt=gp.gp_camera_get_summary(camera,context)
  infod=txToDict(txt.text)
  showText(AREA_PREVIEW,infod.get('Model'))
  info.camera=infod.get('Model')
  pygame.display.flip()
  return camercfg

def updateInfo():
  global info
  info.numPic=numberOfImages
  info.interfaces=[]
  if hasInterfaces:
    for i in netifaces.interfaces():
      if i != "lo":
        try:
          info.interfaces.append(netifaces.ifaddresses(i)[netifaces.AF_INET][0]['addr'])
        except:
          pass

class CameraHandler:
  def __init__(self,camera,context):
    self.camera=camera
    self.context=context
    self.picture=None
    self.doStop=False
    self.cameraError=None
    self.condition=threading.Condition()

  def withCondition(self,func):
    self.condition.acquire(timeout=10)
    try:
      func()
    finally:
      self.condition.notify_all()
      self.condition.release()
  def _getPreview(self):
    try:
      camera_file = gp.check_result(gp.gp_camera_capture_preview(self.camera, None,self.context))
      file_data = gp.check_result(gp.gp_file_get_data_and_size(camera_file))
      self.picture=file_data
    except Exception as e:
      self.cameraError=str(e)

  def run(self):
    while not self.doStop:
      if self.picture is None:
        try:
          if self.doStop:
            return
          self.withCondition(self._getPreview)
        except Exception as e:
          self.cameraError=str(e)
          return
      with self.condition:
        self.condition.wait(timeout=0.005)

  def stopPreview(self):
    self.doStop=True
    with self.condition:
      self.condition.notify_all()

  def startPreview(self):
    rt=threading.Thread(target=self.run)
    rt.setDaemon(True)
    rt.start()

  def getPicture(self):
    wt=20
    while self.picture is None and wt > 0:
      time.sleep(0.005)
      wt=-1
    rt=self.picture
    self.picture=None
    return rt



def updateDelay(delaystart):
  area=AREAS[AREA_DELAY]
  if delaystart is None:
    screen.fill(defaultBackground,area.getRect())
  else:
    delay=nowMs()-delaystart
    border=int(area.width*delay/DELAY)
    if border > area.width:
      border=area.width
    fill=pygame.Rect(area.left,area.top,border,area.height)
    bg=pygame.Rect(border,area.top,area.width-border,area.height)
    screen.fill(defaultBackground,bg)
    screen.fill((255,0,0),fill)

def showHelpTexts():
  showText(AREA_TITLE_LEFT,"Vorschau")
  showText(AREA_TITLE_RIGHT,"Aufnahme")
  showText(AREA_KEYS_LEFT,"ENTER  Aufnahme\n+      Verzoegert\n2      Fokus")
  showText(AREA_KEYS_RIGHT,"0    Freigeben\nDEL  Loeschen")

doStop=False
def sighandler(signum, frames):
  global doStop
  doStop=True

def main():
  global imageNumber,numberOfImages,doStop
  signal.signal(signal.SIGTERM, sighandler)
  cameracfg=None
  httpServer=HTTPServer(PORT,PROGDIR,"release")
  httpServerThread=threading.Thread(target=httpServer.run)
  httpServerThread.setDaemon(True)
  httpServerThread.start()
  imageNumber=findLastImage()
  correctAreas()
  cameraHandler=None
  try:
    doStop=False
    pygameInit()
    logging.basicConfig(
        format='%(levelname)s: %(name)s: %(message)s', level=logging.WARNING)
    gp.check_result(gp.use_python_logging())
    context = gp.gp_context_new()
    # capture preview image (not saved to camera memory card)
    errors=0
    delaystart=None
    while not doStop:
      while cameracfg is None:
        if cameraHandler is not None:
          cameraHandler.stopPreview()
        cameracfg=waitForCamera(context)
        if cameracfg is not None:
          errors=0
          print('Start capturing preview image')
          showHelpTexts()
          cameraHandler=CameraHandler(cameracfg.camera,cameracfg.context)
          cameraHandler.startPreview()
        else:
          key=getKeyFunction(checkKey())
          if key == 'quit':
            print("interrupted")
            sys.exit(1)
          updateInfo()
          showText(AREA_INFO,str(info))
          pygame.display.flip()
          time.sleep(0.2)
      try:
        #camera_file = gp.check_result(gp.gp_camera_capture_preview(camera, context))
        #file_data = gp.check_result(gp.gp_file_get_data_and_size(camera_file))
        # display image
        if cameraHandler.cameraError:
          raise Exception("camera error %s"%(cameraHandler.cameraError))
        file_data=cameraHandler.getPicture()
        if file_data is not None:
          showPreview(io.BytesIO(file_data))
        key=getKeyFunction(checkKey())
        if key is not None:
          delaystart=None
          print("###keydown %s" % (key))
          if key=='quit':
            doStop=True
          if key=="shoot":
            cameraHandler.withCondition(lambda: getPicture(cameracfg))
          if key=="delay":
            delaystart=nowMs()
          if key == 'focus':
            cameraHandler.withCondition(lambda:focus(cameracfg))
          if key =="delete":
            current=os.path.join(TMPPATH,getImageName())
            if os.path.exists(current):
              os.unlink(current)
            current=os.path.join(RELEASEPATH,getImageName())
            if os.path.exists(current):
              os.unlink(current)
              numberOfImages=numberOfImages-1
            screen.fill(defaultBackground,AREAS[AREA_PICTURE].getRect())
            httpServer.setCurrentPicture(None)
          if key == 'release':
            current=getImageName()
            httpServer.setCurrentPicture(current)
            src=os.path.join(TMPPATH,current)
            dst=os.path.join(RELEASEPATH,current)
            if os.path.exists(src) and not os.path.exists(dst):
              if not os.path.exists(RELEASEPATH):
                os.makedirs(RELEASEPATH)
              shutil.copyfile(src,dst)
              numberOfImages=numberOfImages+1
            area=AREAS[AREA_PICTURE]
            rect=pygame.Rect(area.left+2.5,area.top+2.5,area.width-5,area.height-5)
            pygame.draw.rect(screen,(0,255,0),rect,5)
        if delaystart is not None:
          if (nowMs()-delaystart) >= DELAY:
            delaystart=None
            cameraHandler.withCondition(lambda: getPicture(cameracfg))
        updateInfo()
        showText(AREA_INFO,str(info))
        updateDelay(delaystart)
        pygame.display.flip()
      except Exception as e:
        print("Error: %s\n%s" % (e,traceback.format_exc()))
        errors=errors+1
        if (errors > 100):
          print("too many errors, retrying")
          try:
            gp.gp_camera_exit(cameracfg.camera, cameracfg.context)
            del cameracfg
          except:
            pass
          cameracfg=None
        key=checkKey()
        if key is not None:
          print("###keydown")
          if key==pygame.K_q:
            doStop=True
      sleep(0.01)
    
    gp.check_result(gp.gp_camera_exit(cameracfg.camera, cameracfg.context))
    pygame.quit()
    return 0
  except:
    if cameracfg is not None and cameracfg.camera is not None and cameracfg.context is not None:
      gp.gp_camera_exit(cameracfg.camera,cameracfg.context)
    raise

#http://stackoverflow.com/questions/39198961/pygame-init-fails-when-run-with-systemd
def handler(signum, frame):
    pass

try:
    signal.signal(signal.SIGHUP, handler)
except AttributeError:
    # Windows compatibility
    pass

if __name__ == "__main__":
    sys.exit(main())

