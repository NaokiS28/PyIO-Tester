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
    sync: int = 0
    numBytes: int = 0
    nodeID: int = 0
    status: int = 0
    sum: int = 0
    data: bytearray = field(default_factory = bytearray)

@dataclass
class JVSIO:
    nodeID: int = 0
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

def insert_point(string):
    index = 1
    return string[:index] + '.' + string[index:]

class JVS():
    def __init__(self, port: Serial, ioBoard: JVSIO):
        self.cuPort = port
        self.ioBoard = ioBoard
        self.connectState = ConnectState.DISCONNECTED # 0= disconnected, 1= failed, 2= connecting, 3= retrying, 4= connected
        self.cuPort.rts = True
        self.ioBoardCount = 0
    
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
        self.cuPort.reset_input_buffer()
        self.cuPort.reset_output_buffer()
        #print(self.cuPort)
        sleep(0.25)
        if not self.cuPort.is_open:
            raise Exception('TTY port couldn\'t connect to given port')
            return
        print('Connecting to JVS IO on given port...')
        try:
            self.sendReset()
            self.sendReset()
            self.sendReset()
            self.assignID()
            self.requestName()
            self.requestAttributes()
            # If no errors up to this point, or atleast one IO was found, call it good.
            self.connectState = ConnectState.CONNECTED
            self.ioBoardCount += 1
        except JVS_Error:
            print('Error whilst trying to connect')
        # Verify the sense line maybe
        
        return
    
    def disconnect(self):
        print('Disconnecting from JVS-IO')
        #self.sendReset()
        #self.cuPort.flush()
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
        name = self.waitForReply(report)
        if not name:
            raise JVS_Error()
        if name.data[0] == 0x01:
            name.data.replace(bytes(0), bytes(9))
            self.ioBoard.name = bytearray.decode(name.data, encoding="ASCII")
            self.ioBoard.name.replace(';', '\n\t')
            print(str(self.ioBoard.nodeID) + ': ' + self.ioBoard.name)
        else:
            print('Name not supported?')
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
        atr = self.waitForReply(report)
        if not atr:
            raise JVS_Error()
        #print(atr.data)
        if int(atr.data.pop()) == JVS_REPORT_NORMAL: self.ioBoard.cmdver = int(atr.data.pop())
        if int(atr.data.pop()) == JVS_REPORT_NORMAL: self.ioBoard.jvsver = int(atr.data.pop())
        if int(atr.data.pop()) == JVS_REPORT_NORMAL: self.ioBoard.comver = int(atr.data.pop())
        print('\tCommand Ver.: \t' + insert_point(str(self.ioBoard.cmdver))    \
            + '\n\tJVS Ver.: \t' + insert_point(str(self.ioBoard.jvsver))      \
            + '\n\tComm. Ver.: \t' + insert_point(str(self.ioBoard.comver)))
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
    
    def readPacket(self):
        packet = JVS_Frame() 
        index = 0
        counter = 0
        mark_received: bool = False
        response = self.cuPort.read_all()
        for byte in response:
            if byte == JVS_SYNC and index != 0:
                return self.readPacket()
            if not byte == JVS_MARK:
                if mark_received == True:
                    byte -= 1
                    mark_received = False
                match index:
                    case 0:
                        packet.sync = byte       # Sync
                        if packet.sync == 0xE0: index += 1
                    case 1:
                        packet.nodeID = byte
                        index += 1
                    case 2:
                        packet.numBytes = byte
                        index += 1
                    case 3:
                        packet.status = byte
                        index += 1
                    case 4:
                        packet.data.append(byte)
                        counter += 1
                        if counter == (packet.numBytes - 2):   # 3 bytes for status, sum
                            index += 1
                    case 5:
                        packet.sum = byte
            else:
                mark_received = True

        #print(packet)
        if not (packet.sync == 0xE0 and self.calculateSum(packet, False) == packet.sum):
            print('Packet was malformed')
            return 0
        else:
            return packet

    def waitForReply(self, frame):
        tcount = 0
        interval = 0.1  # Update interval
        timeout = 1     # Timeout period
        start = time()
        while not (self.cuPort.in_waiting >= 5):
            if (time() - start > timeout):
                if tcount > 0 and tcount < 4:
                    self.write(frame)
                    start = time()
                elif tcount > 3:
                    print('Request timed out')
                    return 0
                tcount += 1
            else: 
                sleep(interval)
        report = self.readPacket()
        if (report == 0) or not (report.status == 0x01):
            print('Bad report')
            return 0
        return report

    def assignID(self, id = 1):
        report = JVS_Frame()
        #report.numBytes = 3
        report.nodeID = JVS_BROADCAST_ADDR
        report.data.append(JVS_SETADDR_CODE)
        report.data.append(id)
        self.write(report)
        if not self.waitForReply(report):
            raise JVS_Error('JVS IO board didn\'t respond to ID')
        self.ioBoard.nodeID = id
        return id

    def write(self, frame: JVS_Frame):
        if not self.cuPort.is_open \
        or self.connectState == ConnectState.FAILED \
        or self.connectState == ConnectState.DISCONNECTED:
            raise Exception(__name__ + ': Not connected to JVS IO.')
        frame.numBytes = (len(frame.data) + 1)
        packet = bytearray()
        packet.append(0xE0)
        packet.append(frame.nodeID)
        packet.append(len(frame.data) + 1)
        for bytes in frame.data:
            packet.append(bytes)
        packet.append(self.calculateSum(frame, True))

        index = 0
        for f in packet:
            if (int(f) == JVS_SYNC or int(f) == JVS_MARK) and index != 0:
                packet[index] = JVS_MARK
                packet.insert(index + 1, int(f) - 1)
            index += 1

        
        self.cuPort.rts = False
        self.cuPort.write(packet)
        self.cuPort.flush()
        self.cuPort.rts = True
        return
    
    def calculateSum(self, _f: JVS_Frame, send: bool = False):
        _s: int[0:255] = 0
        _s = _f.nodeID
        _s += (len(_f.data) + 1) #_f.numBytes
        if send == False:
            _s += (_f.status + 1)   # +1 for Status Byte to numBytes
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
    with Serial(args.port, args.baud, rtscts=True) as port:
        sleep(0.25)

        jvsIO = JVS(port, jvsIOBoard)
        jvsIO.connect()


if __name__ == "__main__":
    main(sys.argv[1:])