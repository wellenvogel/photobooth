from airplay import AirPlay
import threading
import time

class AirPlaySender:
  def __init__(self,server):
    self.running=False
    self.devices=[]
    self.doStop=False
    self.timeout=5
    self.thread=None
    self.lastStatus="OK"
    self.server=server
    self.newest=None
    self.lastNewest=None
    self.lastCurrent=None
    self.errors=0

  def start(self,timeout=5):
    self.timeout=timeout
    self.doStop=False
    self.lastStatus="OK"
    self.newest=None
    self.current=None
    self.lastCurrent=None
    self.errors=0
    self.thread=threading.Thread(target=self._run)
    self.thread.setDaemon(True)
    self.thread.start()

  def stop(self):
    self.doStop=True

  def isRunning(self):
    return self.running

  def _getDevice(self):
    if not self.isRunning():
      return None

    if self.devices is None or len(self.devices) < 1:
      return None
    return self.devices[0]

  def usedDevice(self):
    dev=self._getDevice()
    if dev is None:
      return ""
    return dev.name

  def getLastStatus(self):
    return self.lastStatus

  def _run(self):
    self.running=True
    while not self.doStop:
      try:
        self.lastStatus="discovering"
        self.errors=0
        self.devices=AirPlay.find(5,True)
        if self.devices is not None and len(self.devices) > 0:
          while not self.doStop and self.errors < 3:
            self._showSlide()
            time.sleep(self.timeout)
          self._getDevice().close()
        else:
          time.sleep(2)
      except Exception as e:
        time.sleep(2)
    self.running=False

  def _showSlide(self):
    if not self.isRunning():
      self.lastStatus="Stopped"
      return
    dev =self._getDevice()
    if dev is None:
      self.lastStatus="No airplay device"
      return
    (current,newest)=self.server.getNextPicture(self.current,self.newest,self.lastCurrent)
    isCurrentPicture=(current == self.server.currentPicture)
    self.current=current
    if isCurrentPicture:
      self.lastCurrent=current
    self.newest=newest
    fname=self.server.nameToPath(current)
    try:
      dev.sendPictureFile(fname)
      self.lastStatus="OK"
    except Exception as e:
      self.lastStatus="Exception: %s"%(str(e))
      self.errors+=1
