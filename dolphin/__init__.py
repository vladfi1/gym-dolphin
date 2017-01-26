from gym.envs.registration import register
from gym.scoreboard.registration import add_task, add_group

from .ssbm_env import SSBMEnv, simpleSSBMEnv

register(
    id='vladfi1/SSBM-v0',
    entry_point='dolphin:simpleSSBMEnv',
    reward_threshold=1,
    timestep_limit=9999999,
    kwargs=dict(
      cpu=9,
      gui=True,
      stage='battlefield',
      mute=True,
      speed=0,
    ),
    nondeterministic=True,
)

register(
    id='vladfi1/SSBM-headless-v0',
    entry_point='dolphin:simpleSSBMEnv',
    reward_threshold=1,
    timestep_limit=9999999,
    kwargs=dict(
      cpu=9,
      stage='battlefield',
    ),
    nondeterministic=True,
)

# Scoreboard registration
# ==========================
add_group(
    id= 'ssbm',
    name= 'Super Smash Bros. Melee',
    description= 'Beat the in-game AIs at SSBM.'
)

"""
add_task(
    id='{}/meta-SuperMarioBros-v0'.format(USERNAME),
    group='ssbm',
    summary='Compilation of all 32 levels of Super Mario Bros. on Nintendo platform - Screen version.',
)
"""

