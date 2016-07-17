#! /usr/bin/env python
# vim: sw=2 ts=2 et
import pygame
import sys
import logging
import io
import os
from time import sleep
import gphoto2 as gp
import time
import re

SCREENW=1680
SCREENH=1050
#adapt to your camera
PREVIEWW=960
PREVIEWH=640

PICW=SCREENW-PREVIEWW-40
PICH=int(PICW*3/4)

DELAY=4000 #delay in ms

AREA_PREVIEW=1
AREA_PICTURE=2
AREA_INFO=3
AREA_DELAY=4

keymappings={
  'quit': [pygame.K_q],
  'shoot': [pygame.K_SPACE,pygame.K_KP_ENTER,pygame.K_RETURN],
  'delay':[pygame.K_PLUS,pygame.K_KP_PLUS],
  'release':[pygame.K_0,pygame.K_KP0],
  'delete':[pygame.K_DELETE,pygame.K_KP_PERIOD]
}

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
  AREA_PREVIEW: Area(0,0,PREVIEWW,PREVIEWH,50),
  AREA_PICTURE: Area(SCREENW-PICW-20,10,PICW,PICH),
  AREA_INFO: Area(0,PREVIEWH+70,PREVIEWW,SCREENH-PREVIEWH-20),
  AREA_DELAY: Area(0,PREVIEWH+10,PREVIEWW,50)
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
    self.help="Enter - Photo\n+       - Verzoegert\nEntf   - Loesche Foto\n0       - Freigeben"
  def __str__(self):
    return "Kamera: %s\nBilder: %d\nTasten:\n%s"%(self.camera,self.numPic,self.help)

info=Info()


screen=None
defaultBackground=None
def pygameInit():
  global screen,defaultBackground
  pygame.init()
  screen=pygame.display.set_mode((SCREENW,SCREENH))
  defaultBackground=screen.get_at((0,0))

def showImage(data):
  imgSurf = pygame.image.load ( data)
  #screen = pygame.display.set_mode ( imgSurf.get_size() )
  print "Preview, width=%d, height=%d"%(imgSurf.get_width(),imgSurf.get_height())
  screen.blit ( imgSurf, ( AREAS[AREA_PREVIEW].left,AREAS[AREA_PREVIEW].top) )

def showCapture(data):
  imgSurf = pygame.image.load ( data)
  #screen = pygame.display.set_mode ( imgSurf.get_size() )
  area=AREAS[AREA_PICTURE]
  screen.blit ( pygame.transform.smoothscale ( imgSurf, (PICW,PICH) ),  ( area.left, area.top ) )

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


def getPicture(camera,context):
  print('Capturing image')
  file_path = gp.check_result(gp.gp_camera_capture(
        camera, gp.GP_CAPTURE_IMAGE, context))
  print('Camera file path: {0}/{1}'.format(file_path.folder, file_path.name))
  target = os.path.join('.', file_path.name)
  print('Copying image to', target)
  try:
    camera_file = gp.check_result(gp.gp_camera_file_get(
            camera, file_path.folder, file_path.name,
            gp.GP_FILE_TYPE_NORMAL, context))
    gp.check_result(gp.gp_file_save(camera_file, target))
  except:
    pass
  rt=gp.gp_camera_file_delete(camera,file_path.folder,file_path.name,context)
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
    doStop=False
    pygameInit()
    logging.basicConfig(
        format='%(levelname)s: %(name)s: %(message)s', level=logging.WARNING)
    gp.check_result(gp.use_python_logging())
    context = gp.gp_context_new()
    # capture preview image (not saved to camera memory card)
    camera=None
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
            showCapture(target)
          if key=="delay":
            delaystart=nowMs()
        if delaystart is not None:
          if (nowMs()-delaystart) >= DELAY:
            delaystart=None
            target=getPicture(camera,context)
            showCapture(target)
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

if __name__ == "__main__":
    sys.exit(main())

