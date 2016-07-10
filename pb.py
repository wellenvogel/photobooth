#! /usr/bin/env python
# vim: sw=2 ts=2 et
import pygame
import sys
import logging
import io
import os
from time import sleep
import gphoto2 as gp
import threading

screen=None
def pygameInit():
  global screen
  pygame.display.init()
  screen=pygame.display.set_mode()

def showImage(data):
  imgSurf = pygame.image.load ( data)
  #screen = pygame.display.set_mode ( imgSurf.get_size() )
  screen.blit ( imgSurf, ( 0, 0 ) )
  pygame.display.flip()

def showCapture(data):
  imgSurf = pygame.image.load ( data)
  #screen = pygame.display.set_mode ( imgSurf.get_size() )
  screen.blit ( pygame.transform.smoothscale ( imgSurf, (640,480) ),  ( 1024, 0 ) )
  pygame.display.flip()

def getPicture(camera,context):
  print('Capturing image')
  file_path = gp.check_result(gp.gp_camera_capture(
        camera, gp.GP_CAPTURE_IMAGE, context))
  print('Camera file path: {0}/{1}'.format(file_path.folder, file_path.name))
  target = os.path.join('.', file_path.name)
  print('Copying image to', target)
  camera_file = gp.check_result(gp.gp_camera_file_get(
            camera, file_path.folder, file_path.name,
            gp.GP_FILE_TYPE_NORMAL, context))
  gp.check_result(gp.gp_file_save(camera_file, target))
  return target

def main():
    doStop=False
    pygameInit()
    logging.basicConfig(
        format='%(levelname)s: %(name)s: %(message)s', level=logging.WARNING)
    gp.check_result(gp.use_python_logging())
    context = gp.gp_context_new()
    camera = gp.check_result(gp.gp_camera_new())
    gp.check_result(gp.gp_camera_init(camera, context))
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
            print('Cannot preview raw images')
            return 1
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
    # capture preview image (not saved to camera memory card)
    print('Capturing preview image')
    while not doStop:
      try:
        camera_file = gp.check_result(gp.gp_camera_capture_preview(camera, context))
        file_data = gp.check_result(gp.gp_file_get_data_and_size(camera_file))
        # display image
        data = memoryview(file_data)
        print(type(data), len(data))
        print(data[:10].tolist())
        showImage(io.BytesIO(file_data))
        event = pygame.event.poll()
        if event.type == pygame.KEYDOWN:
          print "###keydown"
          if event.key==pygame.K_q:
            doStop=True
          if event.key==pygame.K_SPACE:
            target=getPicture(camera,context)
            showCapture(target)
      except:
        pass
      sleep(0.01)
    
    gp.check_result(gp.gp_camera_exit(camera, context))
    pygame.quit()
    return 0

if __name__ == "__main__":
    sys.exit(main())

