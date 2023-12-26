#!/usr/bin/env python3

from argparse import ArgumentParser
from serial import Serial
from time import sleep, time
import sys
from jvsmacros import *
from dataclasses import dataclass, field
from enum import IntEnum

class ConnectState(IntEnum):
    DISCONNECTED = 0
    FAILED = 1
    CONNECTING = 2
    RETRYING = 3
    CONNECTED = 4

@dataclass
class JVS_Frame:
    numBytes: int = 0
    nodeID: int = 0
    statusCode: int = 0
    data: bytearray = field(default_factory = bytearray)

@dataclass
class JVSIO:
    nodeID: int = 0
    statusCode: int = 0
    name: str = "SEGA CORPORATION;837-14506 I/O CNTL BD2;Ver1.01;2005/08"
    cmdver: int = 11
    jvsver: int = 20
    comver: int = 10
    playerCount: int = 2
    switchCount: int = 32
    coinCount: int = 2
    analogCount: int = 8
    rotaryCount: int = 4
    gpoCount: int = 22

class JVS_Error(Exception):
    pass

class JVS():
    def __init__(self, port: Serial, ioBoard: JVSIO):
        self.cuPort = port
        self.ioBoard = ioBoard
        self.connectState = ConnectState.DISCONNECTED # 0= disconnected, 1= failed, 2= connecting, 3= retrying, 4= connected
    
    def __del__(self):
        self.disconnect()

    def wait_until(self, condition, interval=0.1, timeout=1):
        start = time()
        while not condition and (time() - start < timeout):
            sleep(interval)
        return condition

    def setGPO(port, state):
        # Uses GPO 0 command which is most compatible
        
        return state
    
    def connect(self):
        """Connects to the first IO board on the JVS line"""
        self.connectState = ConnectState.CONNECTING
        print(self.cuPort)
        sleep(0.25)
        if not self.cuPort.is_open:
            raise Exception('TTY port couldn\'t connect to given port')
            return
        print('Connecting to JVS IO on given port...')
        print(self.cuPort)
        try:
            self.sendReset()
            self.sendReset()
            self.sendReset()
            self.assignID()
            self.requestName()
            self.requestAttributes()
        except JVS_Error:
            print('Error whilst trying to connect')
        # Verify the sense line maybe
        
        return
    
    def disconnect(self):
        print('Disconnecting from JVS-IO')
        self.cuPort.close()
        return
    
    def update(self):
        pass

    def requestName(self):
        #jvsIO.senseIn = 1
        report = JVS_Frame()
        #report.numBytes = 2
        report.nodeID = self.ioBoard.nodeID
        report.data.append(JVS_IOIDENT_CODE)
        self.write(report)
        return
    
    def requestAttributes(self):
        #jvsIO.senseIn = 1
        report = JVS_Frame()
        #report.numBytes = 5
        report.nodeID = self.ioBoard.nodeID
        report.data.append(JVS_CMDREV_CODE)
        report.data.append(JVS_JVSREV_CODE)
        report.data.append(JVS_COMVER_CODE)
        report.data.append(JVS_FEATCHK_CODE)
        self.write(report)
        return

    def sendReset(self):
        #jvsIO.senseIn = 1
        report = JVS_Frame()
        #report.numBytes = 3
        report.nodeID = JVS_BROADCAST_ADDR
        report.data.append(JVS_RESET_CODE)
        report.data.append(0xD9)
        self.write(report)
        return
    
    def assignID(self, id = 1):
        report = JVS_Frame()
        #report.numBytes = 3
        report.nodeID = JVS_BROADCAST_ADDR
        report.data.append(JVS_SETADDR_CODE)
        report.data.append(id)
        self.write(report)
        #if not (self.wait_until((1 if (self.cuPort.in_waiting > 0) else 0), 0.05, 1)):
        #    raise JVS_Error('JVS IO board didn\'t respond to ID')
        self.ioBoard.nodeID = id
        return

    def write(self, frame: JVS_Frame):
        if not self.cuPort.is_open \
        or self.connectState == ConnectState.FAILED \
        or self.connectState == ConnectState.DISCONNECTED:
            raise Exception(__name__ + ': Not connected to JVS IO.')
            return
        packet = bytearray()
        packet.append(0xE0)
        packet.append(frame.nodeID)
        packet.append(len(frame.data) + 1)
        for bytes in frame.data:
            packet.append(bytes)
        packet.append(self.calculateSum(frame, True))
        self.cuPort.write(packet)
        return
    
    def calculateSum(self, _f: JVS_Frame, send: bool):
        _s: int[0:255] = 0
        _s += _f.nodeID
        _s += (len(_f.data) + 1) #_f.numBytes
        if send == False:
            _s += _f.statusCode
        #for bytes in _f.data:
        #    _s += bytes
        _s += sum(_f.data)
        _s = _s % 256
        return _s

    

def main(args = None):
    parser = ArgumentParser(description = "JVS handler script.")
    parser.add_argument(
		"-p", "--port",
		type = str,
		help = "serial port to use",
		metavar = "port"
	)
    parser.add_argument(
		"-b", "--baud",
		type = int,
		default = 115200,
		help = "override default baud rate (115200)",
		metavar = "value"
	)
	# the -h/--help option is added automatically by default

    args = parser.parse_args(args)
    print("Serial port is", args.port)
    jvsIOBoard = JVSIO()
    with Serial(args.port, args.baud) as port:
        sleep(0.25)

        print("Connecting to JVS IO")
        jvsIO = JVS(port, jvsIOBoard)
        jvsIO.connect()


if __name__ == "__main__":
    main(sys.argv[1:])