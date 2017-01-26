import gym
from gym import spaces

import numpy as np
import random

import os
import time
from warnings import warn

from .default import *
from . import ssbm, state_manager, memory_watcher, movie, util
from .menu_manager import *
from .state import *
from .pad import Pad
from .dolphin import DolphinRunner
from . import ctype_util as ctutil
from .reward import computeRewards

buttons = ['A', 'B', 'Y', 'L', 'Z']

button_space = spaces.Discrete(len(buttons) + 1)
main_stick_space = spaces.Box(0, 1, [2]) # X and Y axes

c_directions = [(0.5, 0.5), (0.5, 1), (0.5, 0), (0, 0.5), (1, 0.5)]
c_stick_space = spaces.Discrete(len(c_directions))

controller_space = spaces.Tuple((button_space, main_stick_space, c_stick_space))

def realController(control):
  button, main, c = control
  
  controller = ssbm.RealControllerState()

  if button < len(buttons):
    setattr(controller, 'button_' + buttons[button], True)
  
  controller.stick_MAIN = tuple(main)
  controller.stick_C = c_directions[c]
  
  return controller

class BoolConv:
  def __init__(self):
    self.space = spaces.Discrete(2)
  def __call__(self, cbool, name=None):
    #assert(type(cbool) is bool, "")
    return int(cbool)

boolConv = BoolConv()

def clip(x, min_x, max_x):
  return min(max(x, min_x), max_x)

class RealConv:
  def __init__(self, low, high, verbose=True):
    self.low = low
    self.high = high
    self.space = spaces.Box(low, high, [1])
    self.verbose = verbose
  
  def __call__(self, x, name=None):
    if self.low > x or x > self.high:
      if self.verbose:
        warn("%f out of bounds in real space \"%s\"" % (x, name))
      x = clip(x, self.low, self.high)
    return np.array([x])

class DiscreteConv:
  def __init__(self, size):
    self.space = spaces.Discrete(size)
  
  def __call__(self, x, name=None, verbose=True):
    if 0 > x or x >= self.space.n:
      if verbose:
        warn("%d out of bounds in discrete space \"%s\"" % (x, name))
      x = 0
    return x

class StructConv:
  def __init__(self, spec):
    self.spec = spec
    
    self.space = spaces.Tuple([conv.space for _, conv in spec])
  
  def __call__(self, struct, **kwargs):
    return [conv(getattr(struct, name), name=name) for name, conv in self.spec]

class ArrayConv:
  def __init__(self, conv, permutation):
    self.conv = conv
    self.permutation = permutation
    
    self.space = spaces.Tuple([conv.space for _ in permutation])
  
  def __call__(self, array, **kwargs):
    return [self.conv(array[i]) for i in self.permutation]

maxCharacter = 32 # should be large enough?

maxAction = 0x017E
numActions = 1 + maxAction

frameConv = RealConv(0, 100, 'frame')
speedConv = RealConv(-20, 20, 'speed') # generally less than 1 in magnitude

player_spec = [
  ('percent', RealConv(0, 200)),
  ('facing', RealConv(-1, 1)),
  ('x', RealConv(-200, 200)),
  ('y', RealConv(-200, 200)),
  ('action_state', DiscreteConv(numActions)),
  ('action_frame', frameConv),
  ('character', DiscreteConv(maxCharacter)),
  ('invulnerable', boolConv),
  ('hitlag_frames_left', frameConv),
  ('hitstun_frames_left', frameConv),
  ('jumps_used', DiscreteConv(8)),
  ('charging_smash', boolConv),
  ('in_air', boolConv),
  ('speed_air_x_self', speedConv),
  ('speed_ground_x_self', speedConv),
  ('speed_y_self', speedConv),
  ('speed_x_attack', speedConv),
  ('speed_y_attack', speedConv),
  ('shield_size', RealConv(0, 100)),
]

playerConv = StructConv(player_spec)

def gameSpec(self=0, enemy=1, swap=False):
  players = [self, enemy]
  if swap:
    players.reverse()
  
  return [
    ('players', ArrayConv(playerConv, players)),
    ('stage', DiscreteConv(32)),
  ]

game_spec = gameSpec()
gameConv = StructConv(game_spec)

gameConv1 = StructConv(gameSpec(swap=True))

class SSBMEnv(gym.Env, Default):
  _options = [
    #Option('user', type=str, help="dolphin user directory"),
    Option('zmq', type=bool, default=True, help="use zmq for memory watcher"),
    Option('stage', type=str, default="final_destination", choices=movie.stages.keys(), help="which stage to play on"),
    #Option('enemy', type=str, help="load enemy agent from file"),
    #Option('enemy_reload', type=int, default=0, help="enemy reload interval"),
    Option('cpu', type=int, default=1, help="enemy cpu level"),
  ] + [Option('p%d' % i, type=str, choices=characters.keys(), default="falcon", help="character for player %d" % i) for i in [1, 2]]
  
  _members = [
    ('dolphinRunner', DolphinRunner)
  ]

  def __init__(self, **kwargs):
    Default.__init__(self, init_members=False, **kwargs)
    
    self.observation_space = gameConv.space
    self.action_space = controller_space
    self.realController = realController
    
    self.first_frame = True
    self.toggle = False
    
    self.prev_state = ssbm.GameMemory()
    self.state = ssbm.GameMemory()
    # track players 1 and 2 (pids 0 and 1)
    self.sm = state_manager.StateManager([0, 1])

    self.pids = [1]
    self.cpus = {1: None}
    self.characters = {1: self.p2}
    
    if self.cpu:
      self.pids.append(0)
      self.cpus[0] = self.cpu
      self.characters[0] = self.p1
    
    self._init_members(cpus=self.pids, **kwargs)
    self.user = self.dolphinRunner.user

    self.write_locations()
    print('Creating MemoryWatcher.')
    mwType = memory_watcher.MemoryWatcher
    if self.zmq:
      mwType = memory_watcher.MemoryWatcherZMQ
    self.mw = mwType(self.user + '/MemoryWatcher/MemoryWatcher')
    
    pipe_dir = self.user + '/Pipes/'
    print('Creating Pads at %s.' % pipe_dir)
    os.makedirs(self.user + '/Pipes/', exist_ok=True)

    paths = [pipe_dir + 'phillip%d' % i for i in self.pids]
    self.get_pads = util.async_map(Pad, paths)
    
    time.sleep(2) # give pads time to set up
    
    self.dolphin_process = self.dolphinRunner()
    
    time.sleep(2) # let dolphin connect to the memory watcher
    
    try:
      self.pads = self.get_pads()
    except KeyboardInterrupt:
      print("Pipes not initialized!")
      return
    
    self.setup()

  def write_locations(self):
    path = self.user + '/MemoryWatcher/'
    os.makedirs(path, exist_ok=True)
    print('Writing locations to:', path)
    with open(path + 'Locations.txt', 'w') as f:
      f.write('\n'.join(self.sm.locations()))
  
  def _close(self):
    self.dolphin_process.terminate()
    import shutil
    shutil.rmtree(self.user)
  
  def update_state(self):
    ctutil.copy(self.state, self.prev_state)
    messages = self.mw.get_messages()
    for message in messages:
      self.sm.handle(self.state, *message)

  def setup(self):
    self.update_state()
    
    pick_chars = []
    
    tapA = [
      (0, movie.pushButton(Button.A)),
      (0, movie.releaseButton(Button.A)),
    ]
    
    for pid, pad in zip(self.pids, self.pads):
      actions = []
      
      cpu = self.cpus[pid]
      
      if cpu:
        actions.append(MoveTo([0, 20], pid, pad, True))
        actions.append(movie.Movie(tapA, pad))
        actions.append(movie.Movie(tapA, pad))
        actions.append(MoveTo([0, -14], pid, pad, True))
        actions.append(movie.Movie(tapA, pad))
        actions.append(MoveTo([cpu * 1.1, 0], pid, pad, True))
        actions.append(movie.Movie(tapA, pad))
        #actions.append(Wait(10000))
      
      actions.append(MoveTo(characters[self.characters[pid]], pid, pad))
      actions.append(movie.Movie(tapA, pad))
      
      pick_chars.append(Sequential(*actions))
    
    pick_chars = Parallel(*pick_chars)
    
    enter_settings = Sequential(
        MoveTo(settings, self.pids[0], self.pads[0]),
        movie.Movie(tapA, self.pads[0])
    )
    
    # sets the game mode and picks the stage
    start_game = movie.Movie(movie.endless_netplay + movie.stages[self.stage], self.pads[0])
    
    self.navigate_menus = Sequential(pick_chars, enter_settings, start_game)
    
    char_stages = [menu.value for menu in [Menu.Characters, Menu.Stages]]
    
    print("Navigating menus.")
    while self.state.menu in char_stages:
      self.mw.advance()
      last_frame = self.state.frame
      self.update_state()
      
      if self.state.frame > last_frame:
        print("nav")
        self.navigate_menus.move(self.state)
        
        if self.navigate_menus.done():
          for pid, pad in zip(self.pids, self.pads):
            if self.characters[pid] == 'sheik':
              pad.press_button(Button.A)
    
    print("setup finished")
    assert(self.state.menu == Menu.Game.value)
    
    # get rid of weird initial conditions
    for _ in range(10):
      self.mw.advance()
      self.update_state()

  def _seed(self, seed=None):
    from gym.utils import seeding
    self.np_random, seed = seeding.np_random(seed)
    return [seed]

  def _step(self, action):
    assert self.action_space.contains(action), "%r (%s) invalid" % (action, type(action))
    
    self.pads[0].send_controller(self.realController(action))
    
    self.mw.advance()
    self.update_state()
    
    observation = gameConv(self.state)
    reward = computeRewards([self.prev_state, self.state])[0]

    return observation, reward, False, {}

  def _reset(self):
    return gameConv(self.state)

def simpleSSBMEnv(act_every=3, **kwargs):
  env = SSBMEnv(**kwargs)
  env.action_space = spaces.Discrete(len(ssbm.simpleControllerStates))
  env.realController = lambda action: ssbm.simpleControllerStates[action].realController()
  
  from gym.wrappers import SkipWrapper
  return SkipWrapper(3)(env)

