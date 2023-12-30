#!/usr/bin/env python3

from argparse import ArgumentParser
from serial import Serial
from time import sleep, time
import sys, os
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
    tcount: int = 0

@dataclass
class JVSIO:
    nodeID: int = 0
    name: str = ""
    cmdver: int = 0
    jvsver: int = 0
    comver: int = 0
    # Input devices
    playerCount: int = 0
    switchCount: int = 0
    coinCount: int = 0
    analogCount: int = 0
    analogPrecision: int = 0
    rotaryCount: int = 0
    screen_x: int = 0
    screen_y: int = 0
    screen_c: int = 0
    extraSwitchCount: int = 0
    # Ouput devices
    cardCount: int = 0
    medalCount: int = 0
    gpoCount: int = 0
    analogOutCount: int = 0
    character_w: int = 0
    character_h: int = 0
    character_type: JVS_CharaOutputTypes = JVS_CharaOutputTypes.JVS_CHARACTER_NONE
    backupSupport: bool = False

class JVS_Error(Exception):
    pass

def insert_point(string):
    index = 1
    return string[:index] + '.' + string[index:]

class JVS():
    def __init__(self, port: Serial, ioBoard: JVSIO, master: bool = True):
        """JVS handler library. Requires a PySerial Serial object and a JVSIO object (This is the first IO board in the chain)"""
        self.cuPort = port
        self.ioBoard = ioBoard
        self.connectState = ConnectState.DISCONNECTED # 0= disconnected, 1= failed, 2= connecting, 3= retrying, 4= connected
        self.cuPort.rts = True
        self.ioBoardCount = 0
        self.lastSentFrame = JVS_Frame()
        self.isMaster = master
    
    def __del__(self):
        self.cuPort.close() 

    def setGPO(self, state):
        """Set IO board's GP outputs. Only tested on IO boards with 8 or less outputs"""
        # Uses GPO 1 command which is most compatible
        if self.ioBoard.gpoCount == 0:
            return 0
        report = JVS_Frame()
        report.nodeID = self.ioBoard.nodeID
        byteCount = int((1 * (self.ioBoard.gpoCount / 8) + 1))
        
        report.data.append(JVS_GENERICOUT1_CODE)
        report.data.append(byteCount)
        for b in range(0, byteCount):
            report.data.append((state & 0xFF))
            state = state >> 8
        self.write(report)
        state = self.waitForReply(report)
        return state
    
    def getInputs(self, player: int = 0):
        """Requests switch data from IO board. If player=0, will get all players, else you can specify how many players to read from (Starting from P1)"""
        report = JVS_Frame()
        report.nodeID = self.ioBoard.nodeID
        report.data.append(JVS_READSWITCH_CODE)
        if player == 0:
            report.data.append(self.ioBoard.playerCount)
        btnBytes = 0
        for x in range(0, (int((1 * (self.ioBoard.switchCount / 8))) + 1)):
            btnBytes += 1
        report.data.append(btnBytes)
        self.write(report)
        state = self.waitForReply(report)
        if state and state.data[0] == JVS_ReportCodes.JVS_REPORT_NORMAL:
            switches = bytearray(state.data[1:])
            return switches
        return 0
    
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
            self.assignID()
            self.requestName()
            self.requestVersions()
            self.requestFeatures()
            # If no errors up to this point, or atleast one IO was found, call it good.
            self.connectState = ConnectState.CONNECTED
            self.ioBoardCount += 1
            self.printFeatures()
        except JVS_Error:
            print('Error whilst trying to connect')
        # Verify the sense line maybe
        
        return self.connectState
    
    def disconnect(self):
        """Tell IO board to reset and then disconnect from UART port."""
        print('Disconnecting from JVS-IO')
        self.sendReset()
        self.cuPort.flush()
        self.cuPort.close()
        return
    
    def update(self):
        """Current not used."""
        pass

    def requestName(self):
        """Request IO board identity name. IO board will return a string with up to 99 characters and deliminated with semicolons (\';\')."""
        report = JVS_Frame()
        report.nodeID = self.ioBoard.nodeID
        report.data.append(JVS_IOIDENT_CODE)

        self.write(report)
        name = self.waitForReply(report)

        if not name:
            raise JVS_Error()
        if name.data[0] == JVS_ReportCodes.JVS_REPORT_NORMAL:
            name.data.replace(bytes(0), bytes(9))
            self.ioBoard.name = bytearray.decode(name.data, encoding="ASCII")
        else:
            raise JVS_Error("IO Board does not support name command.")

    
    def printName(self):
        print(str('\t' + self.ioBoard.name.replace(';', '\n\t')))
            
    
    def requestFeatures(self):
        """Request IO board feature list. Each feature is then processed and added to the IO Board object (JVSIO)."""
        report = JVS_Frame()
        #report.numBytes = 5
        report.nodeID = self.ioBoard.nodeID
        report.data.append(JVS_FEATCHK_CODE)
        self.write(report)
        atr = self.waitForReply(report)
        if not atr:
            raise JVS_Error()
        if int(atr.data.pop(0)) == JVS_ReportCodes.JVS_REPORT_NORMAL:    # Report
            index = 0
            data = 0
            done = False
            while not done:
                data = atr.data.pop(0)
                match bcd2dec(data):
                    case JVS_FeatureCodes.JVS_FEATURE_END:
                        done = True
                    # INPUTS
                    case JVS_FeatureCodes.JVS_FEATURE_SWITCH:
                        self.ioBoard.playerCount = atr.data.pop(0)
                        self.ioBoard.switchCount = atr.data.pop(0)
                        atr.data.pop(0)   # Dump unused byte
                    case JVS_FeatureCodes.JVS_FEATURE_COIN:
                        self.ioBoard.coinCount = atr.data.pop(0)
                        atr.data.pop(0)   # Dump unused byte
                        atr.data.pop(0)   # Dump unused byte
                    case JVS_FeatureCodes.JVS_FEATURE_ANALOG:
                        self.ioBoard.analogCount = atr.data.pop(0)
                        self.ioBoard.analogPrecision = atr.data.pop(0)
                        atr.data.pop(0)   # Dump unused byte
                    case JVS_FeatureCodes.JVS_FEATURE_ROTARY:
                        self.ioBoard.rotaryCount = atr.data.pop(0)
                        atr.data.pop(0)   # Dump unused byte
                        atr.data.pop(0)   # Dump unused byte
                    case JVS_FeatureCodes.JVS_FEATURE_KEYCODE:
                        # Document doesn't cover this and I don't know how to either
                        atr.data.pop(0)   # Dump unused byte
                        atr.data.pop(0)   # Dump unused byte
                        atr.data.pop(0)   # Dump unused byte
                    case JVS_FeatureCodes.JVS_FEATURE_SCREEN:
                        self.ioBoard.screen_x = atr.data.pop(0)
                        self.ioBoard.screen_y = atr.data.pop(0)
                        self.ioBoard.screen_c = atr.data.pop(0)
                    case JVS_FeatureCodes.JVS_FEATURE_MISC:
                        msb = atr.data.pop(0)
                        lsb = atr.data.pop(0)
                        self.ioBoard.extraSwitchCount = (lsb + (msb << 8))
                    # OUTPUTS
                    case JVS_FeatureCodes.JVS_FEATURE_CARD:
                        self.ioBoard.cardCount = atr.data.pop(0)
                        atr.data.pop(0)   # Dump unused byte
                        atr.data.pop(0)   # Dump unused byte
                    case JVS_FeatureCodes.JVS_FEATURE_MEDAL:
                        self.ioBoard.medalCount = atr.data.pop(0)
                        atr.data.pop(0)   # Dump unused byte
                        atr.data.pop(0)   # Dump unused byte
                    case JVS_FeatureCodes.JVS_FEATURE_GPO:
                        self.ioBoard.gpoCount = atr.data.pop(0)
                        atr.data.pop(0)   # Dump unused byte
                        atr.data.pop(0)   # Dump unused byte
                    case JVS_FeatureCodes.JVS_FEATURE_ANALOG_OUT:
                        self.ioBoard.analogOutCount = atr.data.pop(0)
                        atr.data.pop(0)   # Dump unused byte
                        atr.data.pop(0)   # Dump unused byte
                    case JVS_FeatureCodes.JVS_FEATURE_CHARACTER:
                        self.ioBoard.character_w = atr.data.pop(0)
                        self.ioBoard.character_h = atr.data.pop(0)
                        self.ioBoard.character_type = atr.data.pop(0)
                    case JVS_FeatureCodes.JVS_FEATURE_BACKUP:
                        self.ioBoard.backupSupport = True
                        atr.data.pop(0)   # Dump unused byte
                        atr.data.pop(0)   # Dump unused byte
                        atr.data.pop(0)   # Dump unused byte
        return
    
    def printFeatures(self):
        """Prints the full feature support list of the IO Board object (JVSIO)."""
        hasSupportedFeatures = False
        print("Feature support:")
        # INPUTS
        if self.ioBoard.playerCount:
            hasSupportedFeatures = True
            print ('\t' + str(self.ioBoard.playerCount) + ' Players with ' + str(self.ioBoard.switchCount) + ' buttons')
        if self.ioBoard.coinCount:
            hasSupportedFeatures = True
            print ('\t' + str(self.ioBoard.coinCount) + ' Coin slot support')
        if self.ioBoard.analogCount:
            hasSupportedFeatures = True
            print ('\t' + str(self.ioBoard.analogCount) + ' Analog inputs')
        if self.ioBoard.rotaryCount:
            hasSupportedFeatures = True
            print ('\t' + str(self.ioBoard.rotaryCount) + ' Rotary inputs')
        if self.ioBoard.screen_c:
            hasSupportedFeatures = True
            print ('\t' + str(self.ioBoard.screen_c) + ' Screen position inputs')
        if self.ioBoard.extraSwitchCount:
            hasSupportedFeatures = True
            print ('\t' + str(self.ioBoard.extraSwitchCount) + ' Misc. inputs')
        # OUTPUTS
        if self.ioBoard.cardCount:
            hasSupportedFeatures = True
            print ('\t' + str(self.ioBoard.cardCount) + ' Card reader slots')
        if self.ioBoard.medalCount:
            hasSupportedFeatures = True
            print ('\t' + str(self.ioBoard.medalCount) + ' Medal hopper outputs')
        if self.ioBoard.gpoCount:
            hasSupportedFeatures = True
            print ('\t' + str(self.ioBoard.gpoCount) + ' GPO outputs')
        if self.ioBoard.analogOutCount:
            hasSupportedFeatures = True
            print ('\t' + str(self.ioBoard.analogOutCount) + ' Analog outputs')
        if self.ioBoard.character_w:
            hasSupportedFeatures = True
            print ('\t' + str(self.ioBoard.character_w) + 'x' + str(self.ioBoard.character_h) + ' Character display output')
        if self.ioBoard.backupSupport:
            hasSupportedFeatures = True
            print ('\tBackup data support')
        if not hasSupportedFeatures:
            print ('\tNo supported features')

    def requestVersions(self):
        """Request the IO board\'s command, JVS and communications versions and is added to the IO Board object (JVSIO)."""
        report = JVS_Frame()
        report.nodeID = self.ioBoard.nodeID
        report.data.append(JVS_CMDREV_CODE)
        report.data.append(JVS_JVSREV_CODE)
        report.data.append(JVS_COMVER_CODE)

        self.write(report)
        atr = self.waitForReply(report)
        if not atr:
            raise JVS_Error()

        if int(atr.data.pop(0)) == JVS_ReportCodes.JVS_REPORT_NORMAL: self.ioBoard.cmdver = bcd2dec(atr.data.pop(0))
        if int(atr.data.pop(0)) == JVS_ReportCodes.JVS_REPORT_NORMAL: self.ioBoard.jvsver = bcd2dec(atr.data.pop(0))
        if int(atr.data.pop(0)) == JVS_ReportCodes.JVS_REPORT_NORMAL: self.ioBoard.comver = bcd2dec(atr.data.pop(0))

    def printVersions(self):
        """Prints the software versions of the IO Board object (JVSIO)."""
        print('\tCommand Ver.: \t' + insert_point(str(self.ioBoard.cmdver))    \
            + '\n\tJVS Ver.: \t' + insert_point(str(self.ioBoard.jvsver))      \
            + '\n\tComm. Ver.: \t' + insert_point(str(self.ioBoard.comver)))

    def sendReset(self):
        """Tells all IO boards in the chain to reset. Command is sent three times to be sure all IO boards are reset."""
        report = JVS_Frame()
        report.nodeID = JVS_BROADCAST_ADDR
        report.data.append(JVS_RESET_CODE)
        report.data.append(0xD9)

        self.write(report)
        sleep(0.01)
        self.write(report)
        sleep(0.01)
        self.write(report)
        return
    
    def _sendRetry(self):
        """Requests that the IO Board resend the last transmitted packet (i.e. in-case of a checksum error)."""
        report = JVS_Frame()
        report.nodeID = self.ioBoard.nodeID
        report.data.append(JVS_DATARETRY_CODE)
        self.write(report)
        return

    def readPacket(self, doRetry: bool = True, force_read: bool = False, index: int = 0):
        """Reads and returns a JVS_Frame object if one is available. Set doRetry to False if you don't want to ask the IO board to resend the packet in case of read failure."""
        packet = JVS_Frame() 
        #index = fIndex
        counter = 0
        tcount = 0
        mark_received: bool = False

        # A JVS frame cannot be less than 5 bytes (6 if master) (Sync, Node, #Bytes, (Status), Data, sum.)
        if self.cuPort.in_waiting < 5 and not force_read:
            return None
        
        #response = self.cuPort.read_all()
        while index < 6:
            byte = self.cuPort.read()[0]
            if byte == JVS_SYNC and index != 0:
                return self.readPacket(fIndex=1)
            if not byte == JVS_MARK:
                if mark_received == True:
                    byte -= 1
                    mark_received = False
                match index:
                    case 0:
                        packet.sync = byte       # Sync
                        if packet.sync == JVS_SYNC: index += 1
                    case 1:
                        packet.nodeID = byte
                        if (packet.nodeID == 0x00 and self.isMaster) \
                            or ((packet.nodeID == self.ioBoard.nodeID or packet.nodeID == JVS_BROADCAST_ADDR) and not self.isMaster):
                            index += 1
                        else:
                            return -1
                    case 2:
                        packet.numBytes = byte
                        inBuffer = self.cuPort.in_waiting 
                        if (inBuffer < packet.numBytes): 
                            if not self._waitForBytes(packet.numBytes):
                                break
                        index += 1
                    case 3:
                        if(self.isMaster): packet.status = byte
                        else: 
                            packet.data.append(byte)
                            counter += 1
                        if packet.status != JVS_StatusCodes.JVS_STATUS_NORMAL:
                            index += 1
                        index += 1
                    case 4:
                        packet.data.append(byte)
                        counter += 1
                        if counter >= (packet.numBytes - 2):   # 2 bytes for status, sum
                            index += 1
                    case 5:
                        packet.sum = byte
                        index += 1
            else:
                mark_received = True

        #print(packet)
        if (packet.sync == JVS_SYNC) and (self._calculateSum(packet, False) == packet.sum):
            if self.isMaster:
                match packet.status:
                    case JVS_StatusCodes.JVS_STATUS_NORMAL:
                        return packet
                    case JVS_StatusCodes.JVS_STATUS_CHECKSUMERROR:
                        self.write(self.lastSentFrame)
                        return self.waitForReply(self.lastSentFrame)
                    case JVS_StatusCodes.JVS_STATUS_UNKNOWNCMD:
                        print('IO reported unknown commmand')
                        return None
                    case JVS_StatusCodes.JVS_STATUS_OVERFLOW:
                        print('IO reported overflow')
                        return None
        else:
            print('Packet was malformed')
            if doRetry and self.isMaster:
                report = None
                tcount = 0
                while tcount < 3:
                    tcount += 1
                    self._sendRetry()
                    self._waitForBytes(4)
                    report = self.readPacket(doRetry=False)
                    if report:
                        return report
                if not report:
                    print('Too many malformed packets')
                    return None
            else:
                return None

    def _waitForBytes(self, totalBytes: int, timeout: int = 1):
        interval = 0.01  # Update interval
        timeout = 1     # Timeout period
        start = time()
        while not (self.cuPort.in_waiting >= totalBytes):
            if ((time() - start) > timeout):
                    print('Request timed out')
                    return 0
            else: 
                sleep(interval)
        return self.cuPort.in_waiting

    def waitForReply(self, frame):
        """Wait for the IO board to reply after sending a packet with write(Frame). If IO board does not reply within 1 second, this will return None"""
        tcount = 0
        interval = 0.01  # Update interval
        timeout = 1     # Timeout period
        start = time()
        report = None
        while not report:
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
        return report

    def assignID(self, id = 1):
        """Assign an ID number to an IO board. Note, this works on a first come first serve basis down the IO board chain."""
        report = JVS_Frame()
        #report.numBytes = 3
        report.nodeID = JVS_BROADCAST_ADDR
        report.data.append(JVS_SETADDR_CODE)
        report.data.append(id)
        self.write(report)
        reply = self.waitForReply(report) 
        if not reply:
            raise JVS_Error('JVS IO board didn\'t respond to Set ID command')
        elif reply.data[0] != JVS_ReportCodes.JVS_REPORT_NORMAL:
            raise JVS_Error('JVS IO board didn\t accept Set ID command')
        else:
            self.ioBoard.nodeID = id
            return id

    def write(self, frame: JVS_Frame):
        """Write a frame to the IO board."""
        if not self.cuPort.is_open \
        or self.connectState == ConnectState.FAILED \
        or self.connectState == ConnectState.DISCONNECTED:
            raise Exception(__name__ + ': Not connected to JVS IO.')
        frame.numBytes = (len(frame.data) + 1)
        packet = bytearray()
        packet.append(0xE0)
        packet.append(frame.nodeID)
        packet.append(len(frame.data) + 1)
        if not self.isMaster: packet.append(frame.status)
        for bytes in frame.data:
            packet.append(bytes)
        packet.append(self._calculateSum(frame, True))

        index = 0
        for f in packet:
            if (int(f) == JVS_SYNC or int(f) == JVS_MARK) and index != 0:
                packet[index] = JVS_MARK
                packet.insert(index + 1, int(f) - 1)
            index += 1

        self.lastSentFrame = frame

        # Write packet
        self.cuPort.rts = False
        self.cuPort.write(packet)
        self.cuPort.flush()
        self.cuPort.rts = True
        return
    
    def _calculateSum(self, _f: JVS_Frame, send: bool = False):
        """Calculates a sum value for a given frame. You must specify send=True if acting as an IO Board."""
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

def cls():
    os.system('cls' if os.name=='nt' else 'clear')

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

    # now, to clear the screen
    cls()

    args = parser.parse_args(args)
    print("Serial port is", args.port)
    jvsIOBoard = JVSIO()
    with Serial(args.port, args.baud) as port:
        sleep(0.25)

        jvsIO = JVS(port, jvsIOBoard)
        ioState = jvsIO.connect()
        if ioState == ConnectState.CONNECTED:
            print("Connected to:")
            jvsIO.printName()
            jvsIO.printVersions()
            jvsIO.printFeatures()
            gpo = 0x00
            switchRead = 0
            gpoWrite = 0
            endConnection = False
            print("\033[s")
            while not endConnection:
                if (time() - switchRead >= 0.005):
                    switchRead = time()
                    switches = jvsIO.getInputs()
                    if(switches):
                        print("\033[u")
                        btnBytes = 0
                        byteMax = int((1 * (jvsIO.ioBoard.switchCount / 8) + 1))
                        for x in range(0, byteMax):
                            btnBytes += 1

                        print('Switches:')
                        print('\t\tT123xxxx (Test, Tilt 123)')
                        print(str('\t Cab:\t' + format(int(switches[0]), '08b')))
                        print('\t\tS$UDLR12 345678+')
                        for p in range(1, jvsIO.ioBoard.playerCount + 1):
                            print(str('\t P' + str(p) + ':\t'), end='')
                            for x in range(0, btnBytes):
                                i = (x + (btnBytes * (p - 1))) + 1
                                print(format(int(switches[i]), '08b') + ' ', end='')
                            print()
                if (time() - gpoWrite >= 0.25) and jvsIO.ioBoard.gpoCount > 0:
                    gpoWrite = time()
                    if gpo == 0:
                        gpo = 0x01
                    elif gpo > 0 and gpo < 0x10000 :
                        gpo = gpo << 1
                    else:
                        gpo = 0
                    jvsIO.setGPO(gpo)
                    print('GPO: ' + format((gpo >> 16 & 0xFF), '08b') \
                            + ' ' + format((gpo >> 8 & 0xFF), '08b') \
                            + ' ' + format((gpo & 0xFF), '08b') \
                            + ' 0x' + format(gpo, '05x') )
        jvsIO.sendReset()


if __name__ == "__main__":
    main(sys.argv[1:])