#!/usr/bin/python3

from http.server import BaseHTTPRequestHandler,HTTPServer
import serial
import re
import sys
from time import sleep,time
from threading import Thread, Event
from queue import Queue
from voltserial import deviceInit, deviceCommand, deviceClose

MAXLONG=4294967295
MAXADC=1023

comm='/dev/ttyACM0'
speed=115200

sleeplength=0.01
host="localhost"
port=8080
ser=None
datalog=None

for arg in sys.argv:
    if arg.find('host=') == 0:
        host=arg.replace('host=','')
    if arg.find('port=') == 0:
        port=arg.replace('port=','')
    if arg.find('comm=') == 0:
        comm=arg.replace('com=','')
    if arg.find('speed=') == 0:
        speed=arg.replace('speed=','')
    if arg.find('datalog=') == 0:
        try:
            datalog=open(arg.replace('datalog=',''), 'w')
        except:
            print('failed to create data log file: ',datalog)
            exit(-1)

busy=False

class OtherApiHandler(BaseHTTPRequestHandler):
   
    def header(self,mime):
        self.send_response(200)
        self.send_header('Content-type',mime)
        self.end_headers()
    
    def do_GET(self):
        acmd=self.requestline.split()
        print('Get request received',acmd)
        
        if len(acmd) < 1:
            self.send_response(400,"invalid response")

        htfile=acmd[1].replace('/',' ').strip()

        if htfile == '' or htfile=='app':
            self.header('text/html')
            jsfile=open('yrapp.html',mode='r')
            htcontent=jsfile.read()
            jsfile.close()
            self.wfile.write(bytes(htcontent,'utf-8'))
            print('sent app.html')
            
        elif htfile == 'favicon.ico':
            self.header('image/x-icon')
            icofile=open('favicon.ico',mode='rb')
            ico=icofile.read()
            icofile.close()
            self.wfile.write(ico)
            
        elif htfile.rfind('.js',len(htfile)-3)>0:
            # we may limit only to specific javascripts
            self.header('text/plain')
            try:
                jsfile=open(htfile,mode='r')
                htcontent=jsfile.read()
                jsfile.close()
                self.wfile.write(bytes(htcontent,'utf-8'))
                print('sent script: {}'.format(htfile))
            except:
                self.wfile.write(bytes("/* file not found {} */".format(htfile),'ascii'))
        elif htfile == "isbusy":
            # FIXME!
            self.header('text/plain')
            if busy:
                print("device busy")
                self.wfile.write(b'{"name":"check","status":"busy"}')
            else:
                self.wfile.write(b'{"name":"check","status":"ready"}')                

        else:
            s=None
            if htfile.find("msr") == 0:
                msrtime,vals,cmask=deviceCommand(htfile)
                nch=0;
                
                for m in (1,2,4,8,16,32):
                    if cmask & m:
                        nch+=1
                
                s ='{'+'"name":"voltage", "status":"ready","lenght":"{}",'.format(len(vals))
                s+='"msrtime":"{}","channels":"{}",'.format(msrtime,nch)
                s+='"x":{},"timestamp":"{}"'.format(vals,time())+'}'
                
                if datalog:
                    datalog.write(s+'\n')

            else:
                sline=deviceCommand(htfile)
                s='{"name":"command","status":"ready","lenght":"0","msg":"'+sline+'"}'

            self.header('text/plain')
            self.wfile.write(bytes(s,'utf-8'))

################ MAIN PROGRAM ###############

try:
    deviceInit(comm,speed)
except:
    print('server failed to run')
    print('bye...')
    exit(-1) 

print("serving on %s:%s"%(host,port))

try:
    with HTTPServer((host,int(port)), OtherApiHandler) as server:
        server.serve_forever()
        
except KeyboardInterrupt:
    print("\nterminating server")
    deviceClose()
    if datalog:
        datalog.close()
    print("bye...")
