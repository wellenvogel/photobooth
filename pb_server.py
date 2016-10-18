import BaseHTTPServer
import SimpleHTTPServer
import SocketServer
import json
import os
import posixpath
import urllib
import urlparse
import random

import re


class HTTPServer(SocketServer.ThreadingMixIn,BaseHTTPServer.HTTPServer):
  instances=0

  def __init__(self,port,basedir,picturedir):
    self.port=port
    self.basedir=basedir
    self.pictures=picturedir
    self.currentPicture=None
    self.handlers={}
    BaseHTTPServer.HTTPServer.__init__(self, ('0.0.0.0',port), HTTPHandler, True)

  def run(self):
    self.serve_forever()

  def setCurrentPicture(self,current):
    self.currentPicture=current

  def log_message(self,msg):
    pass
  def getNextPicture(self,current,newest,lastCurrent):
    pdir=os.path.join(self.basedir,self.pictures)
    rt=None
    if current is not None:
      current=re.sub(".*/","",current)
    if newest is not None:
      newest=re.sub(".*/","",newest)
    if lastCurrent is not None:
      lastCurrent=re.sub(".*/","",lastCurrent)
    if self.currentPicture is not None and current != self.currentPicture and newest != self.currentPicture and lastCurrent != self.currentPicture:
      #if we return the current picture this is always the newest one
      return (self.currentPicture,self.currentPicture)
    picfiles=sorted(os.listdir(pdir))
    allNames=[]
    for file in picfiles:
      if file[-4:] != ".JPG":
        continue
      fname=os.path.basename(file)
      allNames.append(fname)
    for i in range(0,len(allNames)):
      if allNames[i] == newest and i < (len(allNames)-1):
        #if there are still entries behind the newest - just send them
        return (allNames[i+1],allNames[i+1])
    for i in range(0,3):
      rnd=random.randint(0,len(allNames)-1)
      rt=allNames[rnd]
      if rt != current:
        break
    #if we return an arbitrary one - dont' change the newest
    if newest is None:
      newest=rt
    return (rt,newest)

  def nameToPath(self,name):
    return os.path.join(self.basedir,self.pictures,name)

class HTTPHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
  def __init__(self,request,client_address,server):
    #allow write buffering
    #see https://lautaportti.wordpress.com/2011/04/01/basehttprequesthandler-wastes-tcp-packets/
    self.wbufsize=-1
    self.id=None
    #print("receiver thread started",client_address)
    SimpleHTTPServer.SimpleHTTPRequestHandler.__init__(self, request, client_address, server)
  def log_message(self,format, *args):
    pass
  #overwrite this from SimpleHTTPRequestHandler
  def send_head(self):
    path=self.translate_path(self.path)
    if path is None:
      return
    """Common code for GET and HEAD commands.

    This sends the response code and MIME headers.

    Return value is either a file object (which has to be copied
    to the outputfile by the caller unless the command was HEAD,
    and must be closed by the caller under all circumstances), or
    None, in which case the caller has nothing further to do.

    """

    f = None
    if os.path.isdir(path):
        if not self.path.endswith('/'):
            # redirect browser - doing basically what apache does
            self.send_response(301)
            self.send_header("Location", self.path + "/")
            self.end_headers()
            return None
        for index in "index.html", "index.htm":
            index = os.path.join(path, index)
            if os.path.exists(index):
                path = index
                break
        else:
            return self.list_directory(path)
    base, ext = posixpath.splitext(path)
    ctype = self.guess_type(path)
    try:
        # Always read in binary mode. Opening files in text mode may cause
        # newline translations, making the actual size of the content
        # transmitted *less* than the content-length!
        f = open(path, 'rb')
    except IOError:
        self.send_error(404, "File not found")
        return None
    self.send_response(200)
    self.send_header("Content-type", ctype)
    fs = os.fstat(f.fileno())
    self.send_header("Content-Length", str(fs[6]))
    if path.endswith(".js") or path.endswith(".less"):
      self.send_header("cache-control","private, max-age=0, no-cache")
    self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
    self.end_headers()
    return f

  #overwrite this from SimpleHTTPRequestHandler
  def translate_path(self, path):
      """Translate a /-separated PATH to the local filename syntax.

      Components that mean special things to the local file system
      (e.g. drive or directory names) are ignored.  (XXX They should
      probably be diagnosed.)

      """
      # abandon query parameters
      (path,sep,query) = path.partition('?')
      path = path.split('#',1)[0]
      path = posixpath.normpath(urllib.unquote(path).decode('utf-8'))
      if path.startswith("/getNext"):
        requestParam=urlparse.parse_qs(query,True)
        self.handleNextRequest(path,requestParam)
        return None
      if path=="" or path=="/":
        return self.server.basedir+"/pb.html"
      words = path.split('/')
      words = filter(None, words)
      path = ""
      for word in words:
          drive, word = os.path.splitdrive(word)
          head, word = os.path.split(word)
          if word in (".",".."): continue
          path = os.path.join(path, word)
      return os.path.join(self.server.basedir,path)



  #return the first element of a request param if set
  @classmethod
  def getRequestParam(cls,param,name):
    pa=param.get(name)
    if pa is None:
      return None
    if len(pa) > 0:
      rt=pa[0].decode('utf-8')
      if rt is not None:
        return rt
    return None

  def handleNextRequest(self,path,requestParam):
    current=self.getRequestParam(requestParam,'current')
    newest=self.getRequestParam(requestParam,'newest')
    lastCurrent=self.getRequestParam(requestParam,'lastCurrent')
    (name,newest)=self.server.getNextPicture(current,newest,lastCurrent)
    rt={'url':self.server.pictures+"/"+name,'newest':self.server.pictures+"/"+newest}
    if (name == self.server.currentPicture):
      rt['current']=True
    rtj=json.dumps(rt)
    self.send_response(200)
    if not requestParam.get('callback') is None:
        rtj="%s(%s);"%(requestParam.get('callback'),rtj)
        self.send_header("Content-type", "text/javascript")
    else:
        self.send_header("Content-type", "application/json")
    self.send_header("Content-Length", str(len(rtj)))
    self.send_header("Last-Modified", self.date_time_string())
    self.end_headers()
    self.wfile.write(rtj)