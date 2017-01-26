dolphin_ini = """
[General]
LastFilename = SSBM.iso
ShowLag = False
ShowFrameCount = False
ISOPaths = 2
RecursiveISOPaths = False
NANDRootPath =
WirelessMac =
ISOPath0 =
ISOPath1 = ./
[Interface]
ConfirmStop = True
UsePanicHandlers = True
OnScreenDisplayMessages = True
HideCursor = False
AutoHideCursor = False
MainWindowPosX = 100
MainWindowPosY = 156
MainWindowWidth = 400
MainWindowHeight = 328
Language = 0
ShowToolbar = True
ShowStatusbar = True
ShowLogWindow = False
ShowLogConfigWindow = False
ExtendedFPSInfo = False
ThemeName40 = Clean
PauseOnFocusLost = False
[Display]
FullscreenResolution = Auto
Fullscreen = False
RenderToMain = False
RenderWindowXPos = 0
RenderWindowYPos = 0
RenderWindowWidth = 640
RenderWindowHeight = 528
RenderWindowAutoSize = False
KeepWindowOnTop = False
ProgressiveScan = False
PAL60 = True
DisableScreenSaver = True
ForceNTSCJ = False
[GameList]
ListDrives = False
ListWad = True
ListElfDol = True
ListWii = True
ListGC = True
ListJap = True
ListPal = True
ListUsa = True
ListAustralia = True
ListFrance = True
ListGermany = True
ListItaly = True
ListKorea = True
ListNetherlands = True
ListRussia = True
ListSpain = True
ListTaiwan = True
ListWorld = True
ListUnknown = True
ListSort = 3
ListSortSecondary = 0
ColorCompressed = True
ColumnPlatform = True
ColumnBanner = True
ColumnNotes = True
ColumnFileName = False
ColumnID = False
ColumnRegion = True
ColumnSize = True
ColumnState = True
[Core]
HLE_BS2 = True
TimingVariance = 40
CPUCore = 1
Fastmem = True
CPUThread = {cpu_thread}
DSPHLE = True
SkipIdle = True
SyncOnSkipIdle = True
SyncGPU = False
SyncGpuMaxDistance = 200000
SyncGpuMinDistance = -200000
SyncGpuOverclock = 1.00000000
FPRF = False
AccurateNaNs = False
DefaultISO =
DVDRoot =
Apploader =
EnableCheats = True
SelectedLanguage = 0
OverrideGCLang = False
DPL2Decoder = False
Latency = 2
MemcardAPath = {user}/GC/MemoryCardA.USA.raw
MemcardBPath = {user}/GC/MemoryCardB.USA.raw
AgpCartAPath =
AgpCartBPath =
SlotA = 255
SlotB = 255
SerialPort1 = 255
BBA_MAC =
SIDevice0 = 6
AdapterRumble0 = True
SimulateKonga0 = False
SIDevice1 = 6
AdapterRumble1 = True
SimulateKonga1 = False
SIDevice2 = 0
AdapterRumble2 = True
SimulateKonga2 = False
SIDevice3 = 0
AdapterRumble3 = True
SimulateKonga3 = False
WiiSDCard = False
WiiKeyboard = False
WiimoteContinuousScanning = False
WiimoteEnableSpeaker = False
RunCompareServer = False
RunCompareClient = False
EmulationSpeed = {speed}
FrameSkip = 0x00000000
Overclock = 1.00000000
OverclockEnable = False
GFXBackend = {gfx}
GPUDeterminismMode = auto
PerfMapDir =
[Movie]
PauseMovie = False
Author =
DumpFrames = {dump_frames}
DumpFramesSilent = True
ShowInputDisplay = True
[DSP]
EnableJIT = True
DumpAudio = False
DumpUCode = False
Backend = {audio}
Volume = 50
CaptureLog = False
[Input]
BackgroundInput = True
[FifoPlayer]
LoopReplay = True
"""

gale01_ini = """
[Gecko_Enabled]
$Netplay Community Settings
"""

pipeConfig = """
Buttons/A = `Button A`
Buttons/B = `Button B`
Buttons/X = `Button X`
Buttons/Y = `Button Y`
Buttons/Z = `Button Z`
Main Stick/Up = `Axis MAIN Y +`
Main Stick/Down = `Axis MAIN Y -`
Main Stick/Left = `Axis MAIN X -`
Main Stick/Right = `Axis MAIN X +`
Triggers/L = `Button L`
Triggers/R = `Button R`
D-Pad/Up = `Button D_UP`
D-Pad/Down = `Button D_DOWN`
D-Pad/Left = `Button D_LEFT`
D-Pad/Right = `Button D_RIGHT`
Buttons/Start = `Button START`
C-Stick/Up = `Axis C Y +`
C-Stick/Down = `Axis C Y -`
C-Stick/Left = `Axis C X -`
C-Stick/Right = `Axis C X +`
"""
#Triggers/L-Analog = `Axis L -+`
#Triggers/R-Analog = `Axis R -+`

def generatePipeConfig(player, count):
  config = "[GCPad%d]\n" % (player+1)
  config += "Device = Pipe/%d/phillip%d\n" % (count, player)
  config += pipeConfig
  return config

# TODO: make this configurable
def generateGCPadNew(pids=[1]):
  config = ""
  count = 0
  for p in sorted(pids):
    config += generatePipeConfig(p, count)
    count += 1
  return config

import tempfile
import shutil
import os
from . import util
from .default import *

class SetupUser(Default):
  _options = [
    Option('gfx', type=str, default="Null", help="graphics backend"),
    Option('cpu_thread', action="store_true", default=False, help="Use separate gpu and cpu threads."),
    Option('cpus', type=int, nargs='+', default=[1], help="Which players are cpu-controlled."),
    Option('audio', type=str, default="No audio backend", help="audio backend"),
    Option('speed', type=int, default=0, help='framerate - 100=normal, 0=unlimited'),
    Option('dump_frames', action="store_true", default=False, help="dump frames from dolphin to disk"),
  ]
  
  def __call__(self, user, ):
    configDir = user + 'Config/'
    util.makedirs(configDir)

    with open(configDir + 'GCPadNew.ini', 'w') as f:
      f.write(generateGCPadNew(self.cpus))

    with open(configDir + 'Dolphin.ini', 'w') as f:
      config_args = dict(
        user=user,
        gfx=self.gfx,
        cpu_thread=self.cpu_thread,
        dump_frames=self.dump_frames,
        audio=self.audio,
        speed=self.speed
      )
      f.write(dolphin_ini.format(**config_args))

    gameSettings = user + "GameSettings/"
    util.makedirs(gameSettings)
    
    with open(gameSettings+'GALE01.ini', 'w') as f:
      f.write(gale01_ini)

    util.makedirs(user + 'Dump/Frames/')

import subprocess

class DolphinRunner(Default):
  _options = [
    Option('exe', type=str, default='dolphin-emu-headless', help="dolphin executable"),
    Option('user', type=str, help="path to dolphin user directory"),
    Option('iso', type=str, default="SSBM.iso", help="path to SSBM iso"),
    Option('movie', type=str, help="path to dolphin movie file to play at startup"),
    Option('setup', type=int, default=1, help="setup custom dolphin directory"),
    Option('gui', action="store_true", default=False, help="run with graphics and sound at normal speed"),
    Option('mute', action="store_true", default=False, help="mute game audio"),
  ]
  
  _members = [
    ('setupUser', SetupUser)
  ]
  
  def __init__(self, **kwargs):
    Default.__init__(self, init_members=False, **kwargs)
    
    if self.user is None:
      self.user = tempfile.mkdtemp() + '/'
  
    if self.gui:
      self.exe = 'dolphin-emu-nogui'
      
      if 'speed' not in kwargs:
        kwargs['speed'] = 1
      
      if 'gfx' not in kwargs:
        kwargs['gfx'] = 'OGL'
      
      if self.mute:
        kwargs.update(audio = 'No audio backend')
      else:
        kwargs.update(audio = 'ALSA')
      
    if self.setup:
      self._init_members(**kwargs)
      self.setupUser(self.user)
  
  def __call__(self):
    args = [self.exe, "--user", self.user, "--exec", self.iso]
    if self.movie is not None:
      args += ["--movie", self.movie]
    
    return subprocess.Popen(args)

