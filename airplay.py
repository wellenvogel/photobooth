
#based on https://raw.githubusercontent.com/cnelson/python-airplay/master/airplay/airplay.py
import atexit
import email
import os
import sys
import socket
import time
import warnings
import threading
from httplib import HTTPResponse

from multiprocessing import Process, Queue



try:
    from StringIO import StringIO
except ImportError:
    from io import BytesIO as StringIO

try:
    from urllib import urlencode
    from urllib import pathname2url
except ImportError:
    from urllib.parse import urlencode
    from urllib.request import pathname2url

try:
    from zeroconf import ServiceBrowser, ServiceStateChange, Zeroconf
except ImportError:
    pass

class FakeSocket():
    """Use StringIO to pretend to be a socket like object that supports makefile()"""
    def __init__(self, data):
        self._str = StringIO(data)

    def makefile(self, *args, **kwargs):
        """Returns the StringIO object.  Ignores all arguments"""
        return self._str

class AirPlay(object):
    """Locate and control devices supporting the AirPlay server protocol for video
    This implementation is based on section 4 of https://nto.github.io/AirPlay.html

    For detailed information on most methods and responses, please see the specification.

    """
    RECV_SIZE = 8192

    def __init__(self, host, port=7000, name=None, timeout=10):
        """Connect to an AirPlay device on `host`:`port` optionally named `name`

        Args:
            host(string):   Hostname or IP address of the device to connect to
            port(int):      Port to use when connectiong
            name(string):   Optional. The name of the device.
            timeout(int):   Optional. A timeout for socket operations

        Raises:
            ValueError:     Unable to connect to the specified host/port
        """

        self.host = host
        self.port = port
        self.name = name
        self.timeout=timeout
        self.airplaySocket=None

        # connect the control socket

    def _sendAliveData(self,socket):
        while True:
            try:
                socket.sendAll("0")
                time.sleep(1)
            except:
                #print "alive finished"
                break

    def _command(self, uri, method='GET', body='', **kwargs):
        """Makes an HTTP request through to an AirPlay server

        Args:
            uri(string):    The URI to request
            method(string): The HTTP verb to use when requesting `uri`, defaults to GET
            body(string):   If provided, will be sent witout alteration as the request body.
                            Content-Length header will be set to len(`body`)
            **kwargs:       If provided, Will be converted to a query string and appended to `uri`

        Returns:
            True: Request returned 200 OK, with no response body
            False: Request returned something other than 200 OK, with no response body

            Mixed: The body of the HTTP response
        """

        # generate the request
        if len(kwargs):
            uri = uri + '?' + urlencode(kwargs)

        request = method + " " + uri + " HTTP/1.1\r\nContent-Length: " + str(len(body)) + "\r\n"
        request+="Host: %s:%s\r\n" % (self.host,self.port)
        request+="User-Agent: MediaControl/1.0\r\n"
        request+="X-Apple-Session-ID: c6c0033e-96f9-11e6-b0a4-a45e60c9debb\r\n"
        request+="Connection: close\r\n"
        request+="\r\n"
        request+=body


        try:
            if self.airplaySocket is None:
                self.airplaySocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.airplaySocket.settimeout(self.timeout)
                self.airplaySocket.connect((self.host, self.port))
        except socket.error as exc:
            self.airplaySocket=None
            raise ValueError("Unable to connect to {0}:{1}: {2}".format(self.host, self.port, exc))
        # send it
        rs=self.airplaySocket.sendall(request)

        # parse our response
        result = self.airplaySocket.recv(self.RECV_SIZE)
        resp = HTTPResponse(FakeSocket(result))
        resp.begin()

        # if our content length is zero, then return bool based on result code
        if int(resp.getheader('content-length', 0)) == 0:
            if resp.status == 200:
                return True
            else:
                return False

        # else, parse based on provided content-type
        # and return the response body
        content_type = resp.getheader('content-type')

        if content_type is None:
            raise RuntimeError('Response returned without a content type!')

        return resp.read()
    def close(self):
        if not self.airplaySocket is None:
            try:
                self.airplaySocket.close()
            except:
                pass
            self.airplaySocket=None
    def __str__(self):
        return "Airplay host=%s,port=%s,name=%s"%(self.host,self.port,self.name)

    def server_info(self):
        """Fetch general informations about the AirPlay server.

        Returns:
            dict: key/value pairs that describe the server.
        """
        return self._command('/server-info')

    def sendPictureFile(self,filename):
        f=open(filename,"rb")
        data=f.read()
        f.close()
        self.sendPicture(data)

    def sendPicture(self,jpegData):
        self.close()
        self._command("/photo",'PUT',jpegData)
        t=threading.Thread(target=self._sendAliveData,args=[self.airplaySocket])
        t.setDaemon(True)
        t.start()

    @classmethod
    def find(cls, timeout=10, fast=False):
        """Use Zeroconf/Bonjour to locate AirPlay servers on the local network

        Args:
            timeout(int):   The number of seconds to wait for responses.
                            If fast is false, then this function will always block for this number of seconds.
            fast(bool):     If true, do not wait for timeout to expire,
                            return as soon as we've found at least one AirPlay server

        Returns:
            list:   A list of AirPlay() objects; one for each AirPlay server found

        """

        # this will be our list of devices
        devices = []

        # zeroconf will call this method when a device is found
        def on_service_state_change(zeroconf, service_type, name, state_change):
            if state_change is ServiceStateChange.Added:
                info = zeroconf.get_service_info(service_type, name)
                if info is None:
                    return

                try:
                    name, _ = name.split('.', 1)
                except ValueError:
                    pass

                devices.append(
                    cls(socket.inet_ntoa(info.address), info.port, name)
                )

        # search for AirPlay devices
        try:
            zeroconf = Zeroconf()
            browser = ServiceBrowser(zeroconf, "_airplay._tcp.local.", handlers=[on_service_state_change])  # NOQA
        except NameError:
            warnings.warn(
                'AirPlay.find() requires the zeroconf package but it could not be imported. '
                'Install it if you wish to use this method. https://pypi.python.org/pypi/zeroconf',
                stacklevel=2
            )
            return None

        # enforce the timeout
        timeout = time.time() + timeout
        try:
            while time.time() < timeout:
                # if they asked us to be quick, bounce as soon as we have one AirPlay
                if fast and len(devices):
                    break
                time.sleep(0.05)
        except Exception:  # pragma: no cover
            pass
        zeroconf.close()

        return devices

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print "searching..."
        dev=AirPlay.find(5)
        if dev is not None:
            for d in dev:
                print "dev=",d
        sys.exit(0)

    ap=AirPlay(sys.argv[2],int(sys.argv[3]) if len(sys.argv) > 3 else None)
    ap.sendPictureFile(sys.argv[1])
    x=raw_input("Press Enter")
