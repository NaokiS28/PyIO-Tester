import tkinter as tk
from enum import Enum
import glob
from itertools import count
from multiprocessing import Process

cuList = glob.glob("/dev/cu.*")
senseList = [
    "None",
    "DSR",
    "DCD"
]

ConnectStates = [
    "Disconnected.",
    "Connection Failed.",
    "Connecting...",
    "Retrying...",
    "Connected."
]
ConnectState = ConnectStates[0]
ConnectColour = "red"

class jvsIO:
    name = "SEGA CORPORATION;837-14506 I/O CNTL BD2;Ver1.01;2005/08"
    cmdver = 11
    jvsver = 20
    comver = 10
    playerCount = 2
    switchCount = 32
    coinCount = 2
    analogCount = 8
    rotaryCount = 4
    gpoCount = 22

    connectState = 0 # 0= disconnected, 1= failed, 2= connecting, 3= retrying, 4= connected

    def setGPO(port, state):
        
        return state
    
    def connect():
        connectState = 1
        
        return
    
    def update():
        return

        
def plotPlayerBtn(parent, x, y, p, s):
    state = ""
    if s == 1:
        state = "red"
    else:
        state = "dark grey"
    parent.create_oval((25 * x) + 5, (25 * y) + 5, (25 * (x + 1)), (25 * (y + 1)), fill=state)
    parent.create_text((25 * x) + 15, (25 * y) + 15, text=str(p))


def insert_point(string):
    index = 1
    return string[:index] + '.' + string[index:]

class Applciation(tk.Frame):
    def __init__(self, master=None):
        tk.Frame.__init__(self,master)
        
        self.grid(sticky=tk.N + tk.S + tk.E + tk.W)
        self.createWidgets()

    def createWidgets(self):
        # Setup window
        top = self.winfo_toplevel()
        #top.minsize(800,530)
        top.rowconfigure(0, weight=1)
        top.columnconfigure(0, weight=1)
        self.rowconfigure(0, pad=5, weight=1)
        #self.columnconfigure(1, minsize=150, weight=1)
        #self.columnconfigure(0, minsize=430, weight=1)
        self.drawConection()
    
    def drawConection(self):
        ttyport = tk.StringVar()
        ttyport.set(cuList[0])
        senseport = tk.StringVar()
        senseport.set(senseList[0])

        connSettings = tk.LabelFrame(self, text="Connection Info")

        cb = tk.Button(connSettings, text="Connect", command=jvsIO.connect)
        pl = tk.Label(connSettings, text="TTY Port:", anchor=tk.E, justify=tk.RIGHT)
        p = tk.OptionMenu(connSettings, ttyport, *cuList)
        sl = tk.Label(connSettings, text="JVS Sense In:", anchor=tk.E, justify=tk.RIGHT)
        s = tk.OptionMenu(connSettings, senseport, *senseList)
        cl = tk.Label(connSettings, text=ConnectState, anchor=tk.E, justify=tk.RIGHT, fg=ConnectColour)
        pl.grid(row=0, column=0)
        p.grid(row=0, column=1)
        sl.grid(row=1, column=0)
        s.grid(row=1, column=1)
        cl.grid(row=2, column=1)
        cb.grid(row=2, column=0)

        OutputLog = tk.StringVar(self)
        OutputLog.set("Idle...");
        stdout = tk.Entry(connSettings, textvariable=OutputLog, state="readonly", bg="black", fg="white" ,width=32, justify=tk.LEFT)
        stdout.grid(row=2, column=4, rowspan=2)
        connSettings.grid(row=0,column=0,  padx=5, pady=5, sticky=tk.NW + tk.NE)

    def drawJVSinfo(self):
        jvsInfo = tk.LabelFrame(self, text="JVS I/O Info.")
        jnl = tk.Label(jvsInfo, text="Device Name:", anchor=tk.NE, justify=tk.RIGHT)
        jcl = tk.Label(jvsInfo, text="Command Ver.:", anchor=tk.NE, justify=tk.RIGHT)
        jjl = tk.Label(jvsInfo, text="JVS Ver.:", anchor=tk.NE, justify=tk.RIGHT)
        jml = tk.Label(jvsInfo, text="Comms. Ver.:", anchor=tk.NE, justify=tk.RIGHT)
        jn = tk.Label(jvsInfo, text=jvsIO.name.replace(';', '\n'), bg="white", fg="black", width=32, height = 4, anchor=tk.W, justify=tk.LEFT)
        jc = tk.Label(jvsInfo, text=insert_point(str(jvsIO.cmdver)), bg="white", fg="black", width=32, anchor=tk.W, justify=tk.LEFT)
        jj = tk.Label(jvsInfo, text=insert_point(str(jvsIO.jvsver)), bg="white", fg="black", width=32, anchor=tk.W, justify=tk.LEFT)
        jm = tk.Label(jvsInfo, text=insert_point(str(jvsIO.comver)), bg="white", fg="black", width=32, anchor=tk.W, justify=tk.LEFT)
        jnl.grid(row=0, column=0)
        jn.grid(row=0, column=1)
        jcl.grid(row=1, column=0)
        jc.grid(row=1, column=1)
        jjl.grid(row=2, column=0)
        jj.grid(row=2, column=1)
        jml.grid(row=3, column=0)
        jm.grid(row=3, column=1)
        jvsInfo.grid(row=1,column=0, padx=5, pady=5, sticky=tk.NW + tk.NE)

    def redrawInputs(self):
        switchesIn = tk.LabelFrame(self, text="Inputs")

        if jvsIO.playerCount == 0:
            npl = tk.Label(switchesIn, text="No players reported", fg="red")
            npl.grid(row=0, column=0)
            return
        elif jvsIO.switchCount == 0:
            npl = tk.Label(switchesIn, text="No player switch support.", fg="red")
            npl.grid(row=0, column=0)
            return
        else:
            br = 0
            bc = 0
            pr = 0
            canvasr = 1
            canvasHeight = (25 * (jvsIO.switchCount / 8))
            for p in range(jvsIO.playerCount):
                pl = tk.Label(switchesIn, text='Player ' + str(p + 1) + ': ')
                pl.grid(row=pr,column=0)
                pbc = tk.Canvas(switchesIn, width=225, height=canvasHeight)
                for x in range(jvsIO.switchCount):
                    plotPlayerBtn(pbc, bc, br, x, 0)
                    #bt = tk.Checkbutton(switchesIn, text=str(x))
                    if bc == 7:
                        bc = 0
                        br += 1
                        pr += 1
                    #bt.grid(row=br, column=bc)
                    else:
                        bc += 1
                bc = 0
                br = 0
                pbc.grid(row=canvasr, column=1)
                canvasr = pr + 1
        switchesIn.grid(row=1,column=1, rowspan=4, padx=5, pady=5, sticky=tk.NW + tk.NE)

    def redrawGPOButtons(self):    
        gpoButtons = tk.LabelFrame(self, text="GP Output Control")
        if jvsIO.gpoCount == 0:
            npl = tk.Label(gpoButtons, text="No output support.", fg="red")
            npl.grid(row=0, column=0)
            return
        else:
            bx = 0
            by = 0
            for x in range(jvsIO.gpoCount):
                bt = tk.Button(gpoButtons, state=tk.NORMAL, text='GP Output ' + str(x))
                #bt.grid(row=bx, column=by)
                if bx > 7:
                    bx = 0
                    by = by + 1
                bt.grid(row=bx, column=by)
                bx = bx + 1
        gpoButtons.grid(row=2,column=0, rowspan=4, padx=5, pady=5, sticky=tk.NW + tk.NE)


app = Applciation()
app.master.title("JVS Test Utility")

while 1:
    ConnectState = ConnectStates[jvsIO.connectState]
    if jvsIO.connectState == 0 or jvsIO.connectState == 1:
        ConnectColour = "red"
    elif jvsIO.connectState == 2 or jvsIO.connectState == 3:
        ConnectColour = "yellow"
    else:
        ConnectColour = "green"
    app.update_idletasks()
    app.update()