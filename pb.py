#! /usr/bin/env python
# vim: sw=2 ts=2 et
import pygame
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

#adapt to your needs
SCREENW=1680
SCREENH=1050
#adapt to your camera
PREVIEWW=960
PREVIEWH=640
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
  'delete':[pygame.K_DELETE,pygame.K_KP_PERIOD]
}




PICW=SCREENW-PREVIEWW-60
PICH=int(PICW*3/4)


AREA_PREVIEW=1
AREA_PICTURE=2
AREA_INFO=3
AREA_DELAY=4


class Area:
  def __init__(self,left,top,width,height,fontsize=20):
    self.width=width
    self.height=height
    self.top=top
    self.left=left
    self.fontsize=fontsize
  def getRect(self):
    return pygame.Rect(self.left,self.top,self.width,self.height)

AREAS={
  AREA_PREVIEW: Area(10,10,PREVIEWW,PREVIEWH,50),
  AREA_PICTURE: Area(SCREENW-PICW-30,10,PICW,PICH),
  AREA_INFO: Area(20,PREVIEWH+70,PREVIEWW-20,SCREENH-PREVIEWH-70),
  AREA_DELAY: Area(20,PREVIEWH+10,PREVIEWW-20,50)
}

def getKeyFunction(key):
  if key is None:
    return None
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
    self.help="Enter - Photo\n+       - Verzoegert\nEntf   - Loesche Foto\n0       - Freigeben"
  def __str__(self):
    return "Kamera:   %s\nVorschau: %s\nBilder:   %d\nTasten:\n%s"%(self.camera,self.preview,self.numPic,self.help)

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

def showImage(data):
  global info
  imgSurf = pygame.image.load ( data)
  #screen = pygame.display.set_mode ( imgSurf.get_size() )
  info.preview="%d x %d"%(imgSurf.get_width(),imgSurf.get_height())
  screen.blit ( imgSurf, ( AREAS[AREA_PREVIEW].left,AREAS[AREA_PREVIEW].top) )

def showCapture(data,size=None):
  imgSurf = pygame.image.load ( data)
  #screen = pygame.display.set_mode ( imgSurf.get_size() )
  area=AREAS[AREA_PICTURE]
  if size is None:
    size=(PICW,PICH)
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
  if areaid == AREA_PREVIEW:
    label = myfont.render(text, 1, (255,255,255))
    lrect=label.get_rect()
    screen.blit(label, ((area.width-lrect.width)/2,(area.height-lrect.height)/2 ))
  if areaid == AREA_INFO:
    lines=text.splitlines()
    start=0
    offset=int(area.fontsize*1.1)
    for line in lines:
      label = myfont.render(line, 1, (255,255,255))
      screen.blit(label, (area.left,area.top+start))
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

def getPicture(camera,context):
  print('Capturing image')
  showCapture(getClockFile(),(400,400))
  pygame.display.flip()
  current=os.path.join(TMPPATH,getImageName())
  if os.path.exists(current):
    os.unlink(current)
  file_path = gp.check_result(gp.gp_camera_capture(
        camera, gp.GP_CAPTURE_IMAGE, context))
  print('Camera file path: {0}/{1}'.format(file_path.folder, file_path.name))
  if not os.path.exists(TMPPATH):
    os.makedirs(TMPPATH)
  target = os.path.join(TMPPATH, getImageName(False))
  print('Copying image to', target)
  try:
    camera_file = gp.check_result(gp.gp_camera_file_get(
            camera, file_path.folder, file_path.name,
            gp.GP_FILE_TYPE_NORMAL, context))
    gp.check_result(gp.gp_file_save(camera_file, target))
  except:
    pass
  rt=gp.gp_camera_file_delete(camera,file_path.folder,file_path.name,context)
  showCapture(target)
  return target

def checkKey():
  event = pygame.event.poll()
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
      k,v=re.split("\s*:\s*",line,2)
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
  while True:
    err=gp.gp_camera_init(camera, context)
    if (err >= gp.GP_OK):
      break
    if err != gp.GP_ERROR_MODEL_NOT_FOUND:
        # some other error we can't handle here
        raise gp.GPhoto2Error(err)
    key=getKeyFunction(checkKey())
    if key == 'quit':
      print "interrupted"
      sys.exit(1)
    time.sleep(2)
  # required configuration will depend on camera type!
  print('Checking camera config')
  # get configuration tree
  config = gp.check_result(gp.gp_camera_get_config(camera, context))
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
  return camera

def updateInfo():
  pass

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

def main():
  camera=None
  context=None
  httpServer=HTTPServer(8082,PROGDIR,"release")
  httpServerThread=threading.Thread(target=httpServer.run)
  httpServerThread.setDaemon(True)
  httpServerThread.start()
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
      while camera is None:
        camera=waitForCamera(context)
        if camera is not None:
          errors=0
          print('Start capturing preview image')
      try:
        camera_file = gp.check_result(gp.gp_camera_capture_preview(camera, context))
        file_data = gp.check_result(gp.gp_file_get_data_and_size(camera_file))
        # display image
        data = memoryview(file_data)
        showImage(io.BytesIO(file_data))
        key=getKeyFunction(checkKey())
        if key is not None:
          delaystart=None
          print "###keydown"
          if key=='quit':
            doStop=True
          if key=="shoot":
            target=getPicture(camera,context)
          if key=="delay":
            delaystart=nowMs()
          if key =="delete":
            current=os.path.join(TMPPATH,getImageName())
            if os.path.exists(current):
              os.unlink(current)
            current=os.path.join(RELEASEPATH,getImageName())
            if os.path.exists(current):
              os.unlink(current)
            screen.fill(defaultBackground,AREAS[AREA_PICTURE].getRect())
          if key == 'release':
            current=getImageName()
            httpServer.setCurrentPicture(current)
            src=os.path.join(TMPPATH,current)
            dst=os.path.join(RELEASEPATH,current)
            if os.path.exists(src) and not os.path.exists(dst):
              if not os.path.exists(RELEASEPATH):
                os.makedirs(RELEASEPATH)
              shutil.copyfile(src,dst)
            area=AREAS[AREA_PICTURE]
            rect=pygame.Rect(area.left+2.5,area.top+2.5,area.width-5,area.height-5)
            pygame.draw.rect(screen,(0,255,0),rect,5)
        if delaystart is not None:
          if (nowMs()-delaystart) >= DELAY:
            delaystart=None
            target=getPicture(camera,context)
        updateInfo()
        showText(AREA_INFO,str(info))
        updateDelay(delaystart)
        pygame.display.flip()
      except:
        errors=errors+1
        if (errors > 100):
          print "too many errors, retrying"
          camera=None
        key=checkKey()
        if key is not None:
          print "###keydown"
          if key==pygame.K_q:
            doStop=True
      sleep(0.01)
    
    gp.check_result(gp.gp_camera_exit(camera, context))
    pygame.quit()
    return 0
  except:
    if camera is not None and context is not None:
      gp.gp_camera_exit(camera,context)
    raise

if __name__ == "__main__":
    sys.exit(main())

