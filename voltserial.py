#!/usr/bin/python3
#############################################################
# serial volt-meter
# this module is an interface to the serial based measurement
# instrument. 
# 
# rosandi,2020
#

import serial
import sys
from time import sleep,time
from threading import Thread,Event
from queue import Queue

MAXLONG=4294967295
MAXADC=1023

sleeplength=0.01
verbose=False
busy=False

qsera = Queue()
ev=Event()

ser=None
serthr=None
raw=False
    
def readstream(qui):
    print('listening to port')
    sln=''
    while True:
        c=ser.read()
        if c == b'\n' or c == b'\r':
            sln=sln.replace('\r','').replace('\n','')
            if sln != '':
                qui.put(sln)
            sln=''
        else:
            sln+=c.decode()
            
        if ev.is_set():
            break

def savesend(scmd,ntry=10):
    while not qsera.empty():
        qsera.get()
    
    tout=0
    
    while True:
        if verbose:
            print("sending command: %s try %d"%(scmd,tout))
            
        ser.write(bytes('$'+scmd+';','ascii'))

        # dynamic sleep upto 2 seconds
        for t in range(0,200):
            if qsera.empty():
                sleep(sleeplength/10.0)
            else:
                break
        
        if not qsera.empty():
            s=qsera.get()
            if s == 'OK':
                return True
            else:
                print('strange response: ',s)

        tout+=1
        if tout>ntry:
            print('*** timeout ***')
            break

    return False


allowed_cmd=['msr', 'head', 'dt', 'avg', 'ping', 'chn', 'vref', 'pick']

def checkcmd(scmd):
    cmdval=scmd.split()

    if len(cmdval) != 2:
        return False
    
    for c in allowed_cmd:
        if cmdval[0] == c:
            return True

    return False

def deviceCommand(scmd):
    global busy
    
    busy=True
    if not checkcmd(scmd):
        return 'wrong command: {}'.format(scmd)
    
    rets=""
    cmdval=scmd.split()
    
    if cmdval[0] == 'msr':
        vals=[]
        savesend(scmd)
        ntry=0
        ndat=int(cmdval[1])
        sline=""
        vref=1.1
        cmask=1
        msrtime=0
        
        while True:
            if not qsera.empty():
                sline=qsera.get()
                if sline.find('CONFIRMED:') == 0:
                    break
                
                if sline.find('BEGIN-BLOCK') == 0:
                    sinfo=sline.split()
                    ndat=int(sinfo[1])
                    vref=float(sinfo[2])
                    cmask=int(sinfo[3])
                    msrtime=int(sinfo[4])
                    continue
                    
                if sline.find('END-BLOCK') == 0:
                    tend=int(sline.split()[1])
                    
                    # in uSec
                    if tend<msrtime:
                        msrtime=(MAXLONG-msrtime)+tend
                    else:
                        msrtime=tend-msrtime
                        
                    if verbose:
                        print("measure time: ",msrtime)
                    
                    continue

                try:
                    if raw:
                        vals.append(sline)
                    else:
                        a=float(sline)*vref/MAXADC - vref/2.0
                        vals.append(a)
                except:
                    print('skipping bad number formats ',sline)

            else:
                sleep(sleeplength)
            
            ntry+=1   
            if ntry>100*ndat:
                print("*** timeout: measure %d tries from %d ***"%(ntry,100*ndat))
                break
                      
        busy=False
        return msrtime, vals, cmask

    else:
        savesend(scmd)
        sline=''
        tout=0
 
        while sline.find('CONFIRMED:') < 0:

            if not qsera.empty():
                sline+=qsera.get()
            else:
                sleep(sleeplength)

            tout+=1
            if tout>200:
                print("*** timeout: command ***")
                break
        
        busy=False
        
        # returns: whatever the device replies as string
        return sline

def deviceInit(port,speed):
    global ser, serthr
    
    print('wait.... initializing') 
    try:
        ser = serial.Serial(port, speed)
        sleep(3)
        serthr=Thread(target=readstream, args=(qsera,))
        serthr.start()

    except:
        print('can not open device {}'.format(port))
        raise
    
    if savesend('ping 0'):
        print('ready.')
    else:
        print('something wrong with serial device')
        
def deviceClose():
    print("closing device.");
    ev.set()
    ser.write(b'$ping 191013;')
    sleep(1)
    serthr.join()
    ser.close()

if __name__ == "__main__":
    
    comm=None
    speed=None
    datalog=None
    dostream=False
    every=5
    avg=50
    dt=1
    ndata=50
    nrepeat=0
    
    for arg in sys.argv:
        if arg.find('comm=') == 0:
            comm=arg.replace('comm=','')
        if arg.find('speed=') == 0:
            speed=int(arg.replace('speed=',''))
        if arg.find('every=') == 0:
            every=float(arg.replace('every=',''))
        if arg.find('avg=') == 0:
            avg=int(arg.replace('avg=',''))
        if arg.find('dt=') == 0:
            dt=int(arg.replace('dt=',''))
        if arg.find('ndata=') == 0:
            ndata=int(arg.replace('ndata=',''))
        if arg.find('N=') == 0:
            nrepeat=int(arg.replace('N=',''))
        if arg.find('stream') == 0:
            dostream=True
        if arg.find('verbose') == 0:
            verbose=True
        if arg.find('datalog=') == 0:
            try:
                datalog=open(arg.replace('datalog=',''), 'w')
            except:
                print('failed to create data log file: ',datalog)
                exit(-1)

    if not comm or not speed:
        print("arguments required: comm=[comm-port] speed=[transmision-speed]")
        exit(-1)

    print("device initialization...")
    deviceInit(comm, speed)
    nlog=1
    
    if datalog:
        print(deviceCommand('avg '+str(avg)))
        print(deviceCommand('dt '+str(dt)))
        
        if dostream:
            ev.set()
            ser.write(bytes('$pick '+str(avg)+';','ascii'))
            sleep(1)
            serthr.join()
            ser.reset_input_buffer()
            
        raw=True
        
        try:
            while True:
                if dostream:
                    t=0 
                    datalog.write('#{} {}\n'.format(time(),ndata))

                    while t<ndata:  
                        sln=''
                        ser.write(b'a')
                        while True:
                            c=ser.read()
                            if c == b'\n' or c == b'\r':
                                break
                            else:
                                sln+=c.decode()

                        sln=sln.replace('\r','').replace('\n','')

                        if sln == '':
                            continue
                            
                        datalog.write('{}\n'.format(sln))
                        t+=1
                        sleep(every)
                        
                    if verbose:
                        print('stream log ',nlog)
                        nlog+=1
                        
                    datalog.flush()
                    
                else:
                    msrtime,vals,cmask=deviceCommand('msr '+str(ndata))
                    # timestamp block_measure_time_uSec data_length channel_mask
                    datalog.write('# {} {} {} {}\n'.format(time(),msrtime,len(vals),cmask))
                    for v in vals:
                        datalog.write('{}\n'.format(v))
                    datalog.flush()
                    print("data writen ",nlog)
                    nlog+=1
                    sleep(every)
                    
                if nrepeat:
                    if nlog >= nrepeat:
                        break
                        
        except KeyboardInterrupt:
            print('terminating')
            datalog.close()
            
        except:
            print('unknown error')
            datalog.close()
            raise

    deviceClose()
