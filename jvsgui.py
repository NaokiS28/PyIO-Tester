#!/usr/bin/env python3

from tkinter import *
import tkinter as tk
from tkinter import ttk
import glob
from jvs import JVS, JVSIO, ConnectState
from serial import Serial
from functools import partial
from bitstring import BitArray

#tk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
#tk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

lastSwitch = bytearray(0)

class ConnectionState:
    ConnectStatesText = [
        "Disconnected.",
        "Connection Failed.",
        "Connection Lost.",
        "Connecting...",
        "Retrying...",
        "Connected."
    ]
    ConnectStatesColor = [
        "red",
        "yellow",
        "green"
    ]

    def __init__(self):
        self.status = ConnectState.DISCONNECTED
        self.statusText = self.ConnectStatesText[self.status]
        self.statusColor = self.ConnectStatesColor[self.status]
    
    def setState(self, state: int):
        self.status = state
        self.statusText = self.ConnectStatesText[self.status]
        if state < ConnectState.CONNECTING:
            self.statusColor = self.ConnectStatesColor[0]
        elif state > ConnectState.FAILED and state < ConnectState.CONNECTED:
            self.statusColor = self.ConnectStatesColor[1]
        else:
            self.statusColor = self.ConnectStatesColor[2]
        return state


class jvsApp(tk.Tk):
    def __init__(self, portList):
        super().__init__()

        self.senseList = [
            "None",
            "DSR",
            "DCD"
        ]

        self.uartList = portList
        self.jvsPort = Serial()
        self.jvsInfo = JVSIO
        self.jvs: JVS = None

        self.connection = ConnectionState()

        self.ttyport = tk.StringVar()
        self.ttyport.set("")
        self.senseport = tk.StringVar()
        self.senseport.set(self.senseList[0])

        self.title("JVS Test Utility")
        #self.geometry(f"{1100}x{500}")

        self.dynamic_GPO = []
        self.gpo_States = BitArray(32)
        self.dynamic_InputC = []
        self.dynamic_InputT = []
        self.dynamic_Coin = []

        self.connTryCount = 0

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        portCheck = self.register(self.checkBeforeConnect)

        self.connectionFrame = tk.Frame(master=self, width=600, height=400)
        self.portlabel = tk.Label(self.connectionFrame, text="TTY Port:", anchor='e', justify="right")
        self.portlabel.grid(row=0, column=0, padx=5, pady=5)
        self.port = ttk.Combobox(self.connectionFrame, textvariable=self.ttyport, values=self.uartList, validate='all' ,validatecommand=(portCheck, '%P'))
        self.port.grid(row=0, column=1, padx=5, pady=5)
        self.senseLabel = tk.Label(self.connectionFrame, text="JVS Sense In:", anchor='e', justify="right")
        self.senseLabel.grid(row=1, column=0, padx=5, pady=5)
        self.sensePin = ttk.Combobox(self.connectionFrame, textvariable=self.senseport, values=self.senseList)
        self.sensePin.grid(row=1, column=1, padx=5, pady=5)
        self.connlabel = tk.Label(self.connectionFrame, text=self.connection.statusText, fg=self.connection.statusColor)
        self.connlabel.grid(row=2, column=1, padx=5, pady=5)
        self.connBtn = tk.Button(self.connectionFrame, text="Connect", command=self.connect, state="disable")
        self.connBtn.grid(row=2, column=0, padx=5, pady=5)
        self.connectionFrame.grid(row=0, column=0, padx=10, pady=10)

        self.jvsInfoBox = tk.Frame(master=self)
        self.jvsNameLabel = tk.Label(self.jvsInfoBox, text="Device Name:", justify='right', anchor='e')
        self.jvsCMDVerL = tk.Label(self.jvsInfoBox, text="Command Ver.:", justify='right', anchor='e')
        self.jvsJVSVerL = tk.Label(self.jvsInfoBox, text="JVS Ver.:", justify='right', anchor='e')
        self.jvsComVerL = tk.Label(self.jvsInfoBox, text="Comms. Ver.:", justify='right', anchor='e')
        self.jvsName = tk.Text(self.jvsInfoBox, fg="white", bg='black', width=32, height=4)
        self.jvsCmd = tk.Text(self.jvsInfoBox, fg="white", bg="black", width=32, height=1)
        self.jvsJVS = tk.Text(self.jvsInfoBox, fg="white", bg="black", width=32, height=1)
        self.jvsCom = tk.Text(self.jvsInfoBox, fg="white", bg="black", width=32, height=1)
        self.jvsName.insert('end', self.jvsInfo.name.replace(';', '\n'))
        self.jvsCmd.insert('end', self._insert_point(str(self.jvsInfo.cmdver)))
        self.jvsJVS.insert('end', self._insert_point(str(self.jvsInfo.jvsver)))
        self.jvsCom.insert('end', self._insert_point(str(self.jvsInfo.comver)))
        self.jvsName.configure(state='disabled')
        self.jvsCmd.configure(state='disabled')
        self.jvsJVS.configure(state='disabled')
        self.jvsCom.configure(state='disabled')
        self.jvsNameLabel.grid(row=0, column=0)
        self.jvsName.grid(row=0, column=1)
        self.jvsCMDVerL.grid(row=1, column=0)
        self.jvsCmd.grid(row=1, column=1)
        self.jvsJVSVerL.grid(row=2, column=0)
        self.jvsJVS.grid(row=2, column=1)
        self.jvsComVerL.grid(row=3, column=0)
        self.jvsCom.grid(row=3, column=1)
        self.jvsInfoBox.grid(row=0,column=1, padx=10, pady=10)
        

    def checkBeforeConnect(self, string):
        if self.ttyport == "":
            self.connBtn.configure(state="disable")
            return False
        else:
            self.ttyport.set(string)
            self.connBtn.configure(state="normal")
            return True
    
    def connect(self):
        self.connTryCount += 1
        if self.connection.status != ConnectState.RETRYING:
            self.connection.setState(ConnectState.CONNECTING)
            self.connlabel.configure(text=self.connection.statusText, fg=self.connection.statusColor)
        self.connBtn.configure(state="disabled")
        self.port.configure(state="disabled")
        self.sensePin.configure(state="disabled")
        self.update()
        self.jvsPort = Serial(port=self.ttyport.get(), baudrate=115200)
        self.jvs = JVS(self.jvsPort, self.jvsInfo)
        result = self.jvs.connect()
        if result == ConnectState.CONNECTED:
            self.connTryCount = 0
            self.connection.setState(ConnectState.CONNECTED)
            self.connBtn.configure(state='normal', text="Disconnect", command=self.disconnect)
            self.port.configure(state='disabled')
            self.sensePin.configure(state='disabled')
            self.connlabel.configure(text=self.connection.statusText, fg=self.connection.statusColor)
            self.updateIOInfo()
            if self.jvsInfo.gpoCount > 0:
                self.drawGPOFrame()
            if self.jvsInfo.switchCount > 0:
                self.drawInputsFrame()
        else:
            if self.connection.status != ConnectState.RETRYING: 
                self.connection.setState(ConnectState.FAILED)
                self.disconnect()

    def drawGPOFrame(self):
        byteCount = int((1 * (self.jvsInfo.gpoCount / 8)) + 1)
        self.gpo_States = BitArray(8 * byteCount)
        self.gpoFrame = tk.Frame(master=self)
        self.btnSetGPO = tk.Button(self.gpoFrame, text='All outputs ON', fg='green', command=self.setAllGPO)
        self.btnClrGPO = tk.Button(self.gpoFrame, text='All outputs OFF', fg='red', command=self.clearAllGPO)
        self.btnSetGPO.grid(row=0,column=0, columnspan=2)
        self.btnClrGPO.grid(row=0,column=2, columnspan=2)
        gx = 0
        gy = 1
        for x in range(0, self.jvsInfo.gpoCount):   # is 17 in my case
            gpoBtn = tk.Button(self.gpoFrame, text=str('GPO' + str(x)), fg='red', command=partial(self.toggleGPO, x), width=5)
            self.dynamic_GPO.append(gpoBtn)    
            gpoBtn.grid(row=gy, column=gx)
            if gx > 2:
                gx = 0
                gy += 1
            else:
                gx += 1
        self.gpoLabel = tk.Label(self.gpoFrame, text=str('Output in hex: 0x') + format(BitArray(self.gpo_States).int, '0X'))
        self.gpoLabel.grid(row=gy+1, columnspan=4)
        self.gpoFrame.grid(row=1,column=0, pady=[0,10])
    
    def drawInputsFrame(self):
        self.inputFrame = tk.Frame(master=self)
        gx = 0
        gy = 0
        rI = 0

        for cn in range(0, self.jvsInfo.coinCount):
            self.coinLabel = tk.Label(self.inputFrame, text=str('Coin ' + str(cn+1) + ':'))
            self.coinLabel.grid(row=rI,column=0)
            coinC = tk.Text(self.inputFrame, height=1, width=28)
            coinC.insert('end', str(0))
            self.dynamic_Coin.append(coinC)
            self.dynamic_Coin[cn].grid(row=rI,column=1)
            rI += 1

        self.machineLabel = tk.Label(self.inputFrame, text='Service: ')
        self.machineLabel.grid(row=rI,column=0)
        self.machineCanvas = tk.Canvas(self.inputFrame, height=20)
        self.btnTestO = self.machineCanvas.create_oval(3, 3, 20, 20, fill='red4')
        self.btnTestT = self.machineCanvas.create_text(12, 12, text='T', fill='white')
        #self.btnTiltO = self.machineCanvas.create_oval(3 + (25), 3, 20 + (25), 20, fill='red4')
        #self.btnTiltT = self.machineCanvas.create_text(12 + (25), 12, text='Tl', fill='white')
        self.machineCanvas.grid(row=rI, column=1)
        rI += 1

        self.playerCanvas = []
        for x in range(0, self.jvsInfo.playerCount):
            gx = 0
            gy = 0
            self.playerLabel = tk.Label(self.inputFrame, text=str('Player ' + str(x + 1) + ':'))
            self.playerLabel.grid(row=rI,column=0)
            self.playerCanvas.append(tk.Canvas(self.inputFrame, height=20 * (1 + (self.jvsInfo.switchCount / 8))))
            for b in range(0, self.jvsInfo.switchCount):
                btnInC = self.playerCanvas[x].create_oval(3 + (25 * gx), 3 + (25 * gy), 20 + (25 * gx), 20 + (25 * gy), fill='red4')
                btnInT = self.playerCanvas[x].create_text(12 + (25 * gx), 12 + (25 * gy), text=str(b + 1), fill='white')
                self.dynamic_InputC.append(btnInC)
                self.dynamic_InputT.append(btnInT) 
                if gx < 7:
                    gx += 1
                else:
                    gx = 0
                    gy += 1
            self.playerCanvas[x].grid(row=rI, column=1)
            rI += 1
        self.inputFrame.grid(row=1,column=1, pady=[0,10])

    def setAllGPO(self):
        self.gpo_States.set(True)
        status = self.jvs.setGPO(self.gpo_States.tobytes())
        if not status:
            self.reconnect()
            return
        for o in range(0, self.jvsInfo.gpoCount):
            self.dynamic_GPO[o].configure(fg='green')

    def clearAllGPO(self):
        self.gpo_States.set(False)
        status = self.jvs.setGPO(self.gpo_States.tobytes())
        if not status:
            self.reconnect()
            return
        for o in range(0, self.jvsInfo.gpoCount):
            self.dynamic_GPO[o].configure(fg='red')

    def toggleGPO(self, slot):
        bit = ((len(self.gpo_States)-1) - slot)
        self.gpo_States.invert(bit)
        status = self.jvs.setGPO(self.gpo_States.tobytes())
        if not status:
            self.reconnect()
            return
        state = bool((self.gpo_States._getint()) & (1 << slot))
        #print(self.gpo_States)
        #print(state)
        self.gpoLabel.configure(text=str('Output in hex: 0x') + format(BitArray(self.gpo_States).int, '0X'))
        if state:
            self.dynamic_GPO[slot].configure(fg='green')
        else: 
            self.dynamic_GPO[slot].configure(fg='red')
        
    def getSwitchStates(self):
        switches = self.jvs.getInputs()
        if not switches:
            return False
        idx = 0
        btnInt = int(switches[0])
        if switches and (switches != lastSwitch):
            if (bool((btnInt) & 1)): 
                self.machineCanvas.itemconfigure(0, fill='red')
            else: 
                self.machineCanvas.itemconfigure(0, fill='red4')

            for p in range(0, self.jvsInfo.playerCount):
                idx += 1
                btnInt = int(switches[idx])
                slot = 0
                for s in range(0, self.jvsInfo.switchCount):
                    pOval = 1 + (2 * s)
                    if (bool((btnInt) & (0x80 >> (s - (8 * slot))))): 
                        self.playerCanvas[p].itemconfigure(pOval, fill='red')
                    else:
                        self.playerCanvas[p].itemconfigure(pOval, fill='red4')
                    if s == 7:
                        idx += 1
                        btnInt = int(switches[idx])
                        slot += 1
            lastSwitch[:] = switches
        return True
    
    def reconnect(self):
        self.connection.setState(ConnectState.RETRYING)
        if self.gpoFrame:
            self.btnClrGPO.configure(state='disabled')
            self.btnSetGPO.configure(state='disabled')
            for o in range(0, len(self.dynamic_GPO)):
                self.dynamic_GPO[o].configure(state='disabled')

        while self.connTryCount < 3:
            if self.connection.status != ConnectState.CONNECTED:
                self.connlabel.configure(text=str(self.connection.statusText + str(self.connTryCount + 1)), fg=self.connection.statusColor)
                self.update()
                self.connect()
            else:
                break
        if self.connection.status != ConnectState.CONNECTED:
            self.connection.setState(ConnectState.LOST)
            self.connBtn.configure(state='normal', text="Connect", command=self.connect)
            self.port.configure(state='normal')
            self.sensePin.configure(state='normal')
            self.connlabel.configure(text=self.connection.statusText, fg=self.connection.statusColor)
            self.disconnect()

    def disconnect(self):
        if self.gpoFrame: 
            for g in range(0, len(self.dynamic_GPO)):
                self.dynamic_GPO[g].destroy()
            self.dynamic_GPO.clear()
            self.gpoFrame.destroy()

        if self.inputFrame: 
            self.machineCanvas.destroy()
            if self.jvsInfo.playerCount > 0 and self.jvsInfo.switchCount > 0:
                self.dynamic_InputC.clear()
                self.dynamic_InputT.clear()

            if self.jvsInfo.coinCount > 0:
                self.dynamic_Coin.clear()

            self.inputFrame.destroy()

        self.jvs.disconnect()
        if self.connection.status != ConnectState.LOST:
            self.connection.setState(ConnectState.DISCONNECTED)
        self.connBtn.configure(state="normal", text="Connect", command=self.connect)
        self.port.configure(state="normal")
        self.sensePin.configure(state="normal")
        self.connlabel.configure(text=self.connection.statusText, fg=self.connection.statusColor)

    def updateIOInfo(self):
        self.jvsName.configure(state='normal')
        self.jvsCmd.configure(state='normal')
        self.jvsJVS.configure(state='normal')
        self.jvsCom.configure(state='normal')
        self.jvsName.delete('1.0', END)
        self.jvsCmd.delete('1.0', END)
        self.jvsJVS.delete('1.0', END)
        self.jvsCom.delete('1.0', END)
        self.jvsName.insert('end', self.jvsInfo.name.replace(';', '\n'))
        self.jvsCmd.insert('end', self._insert_point(str(self.jvsInfo.cmdver)))
        self.jvsJVS.insert('end', self._insert_point(str(self.jvsInfo.jvsver)))
        self.jvsCom.insert('end', self._insert_point(str(self.jvsInfo.comver)))
        self.jvsName.configure(state='disabled')
        self.jvsCmd.configure(state='disabled')
        self.jvsJVS.configure(state='disabled')
        self.jvsCom.configure(state='disabled')


    def _insert_point(self, string):
        index = 1
        if string == "0":
            return "0.0"
        else:
            return string[:index] + '.' + string[index:]

if __name__ == "__main__":
    cuList = glob.glob("/dev/cu.*")
    app = jvsApp(cuList)
    while app:
        app.update()
        if app.connection.status == ConnectState.CONNECTED and app.jvsInfo.switchCount > 0:
            if not app.getSwitchStates():
                app.reconnect()
            