# bdmc
---
> This lib is especially designed to control the BDMC drivers, which is under the sales of TechStar.

## TODO

- [x] Basic motor serial controller.
- [x] Basic Transmitting channel builder.
- [ ] Fully integrate the standard serial cmds into this lib.
- [ ] More capable controller implementations that support more complicated control strategies.

## Install

Install use pdm

```shell

# install pdm
python -m pip install pdm

# config pdm
pdm config pypi.url https://pypi.tuna.tsinghua.edu.cn/simple

# for stable version
pdm add bdmc 

# for unstable version
pdm add bdmc -pre
```

## QuickStart

The minimal example is as below.

```python
from bdmc import CloseLoopController, MotorInfo, CMD

# Create a MotorInfo Sequence, with 4 motors defined here.
motor_seq = (MotorInfo(code_sign=1, direction=1),
             # code_sign is used as unique identifier, while the direction are used as motor rotate direction adjuster
             MotorInfo(3, 1),
             MotorInfo(4, -1),
             MotorInfo(2, -1))

# Define the name of the serial device that will be used to control the motor
port = "tty0"
# port="COM3"  on windows, device name differ from that in  the linux

# Create the controller obj, with starting the msg sending thread and send a broadcast RESET cmd to init the motors being controlled
con = (CloseLoopController(motor_infos=motor_seq, port=port)
       .start_msg_sending()
       .send_cmd(CMD.RESET))

# Use the set_motors_speed method, to set all 4 motors speed.
# In this case,motor_1 receives 100*direction, motor_3 receive 200*direction,and so on. 
# NOTE1: the speed used here will multiply the motor's direction accordingly.
# NOTE2: the speed sequence MUST have the same length as the motor_seq, a ValueException will be raised otherwise.
con.set_motors_speed([100, 200, 300, 400])

# Supports chain calls
# In this case, these 3 cmds will be sent to the motors at almost the same time, only the [0]*4 will take effect as a result
(con
 .set_motors_speed([100, 200, 300, 400])
 .set_motors_speed([1000] * 4)  # move all 4 motors with the speed of 1000
 .set_motors_speed([0] * 4))

# Chain call with delay
# In this case, these 3 cmds will be sent to motors with the specified interval
(con
 .set_motors_speed([100, 200, 300, 400])
 .delay(1.2)  # delay 1.2 sec
 .set_motors_speed([1000] * 4)
 .delay(3)  # delay 3.0 sec
 .set_motors_speed([0] * 4))

# Chain call with delay_b
# In this case, these 3 cmds will be sent to motors with specified interval,but with a break checker
# NOTE1: you can't set check_interval bigger than delay_sec
from random import random

(con
 .set_motors_speed([100, 200, 300, 400])
 .delay_b(delay_sec=1.2, breaker=lambda: random() > 0.8,
          check_interval=0.01)  # delay 1.2 sec, will skip the 1.2 sec on the breaker returns True, execute the checker every 0.01 sec
 .set_motors_speed([1000] * 4)
 .delay_b(3, breaker=lambda: random() > 0.5,
          check_interval=0.02)  # delay 3.0 sec, will skip the 1.2 sec on the breaker returns True, execute the checker every 0.02 sec
 .set_motors_speed([0] * 4))

# Branched chain call with delay_b_match
# In this case, a switch-case branch has been enforced.
# Once the breaker returns a True during the 1.2 sec delay, a FULL_STOP cmd will be sent.
# if the breaker never return a True, then the 1.2sec delay will be fully waited and the [500]*4 cmd will be sent.

# NOTE1: delay_b_match has same delay logic as delay_b, the only difference is the return value:
# delay_b       returns Self
# delay_b_match returns breaker()


match (con
       .set_motors_speed([100] * 4)
       .delay_b_match(1.2, breaker=lambda: random() > 0.8)):
    case True:
        con.send_cmd(CMD.FULL_STOP)
    case False:
        con.set_motors_speed([500] * 4)
    case _:
        raise ValueError("should never be here")

# A more complex usage of delay_b_match
# Note
from random import choice

match (con
       .set_motors_speed([100] * 4)
       .delay_b_match(1.2, breaker=lambda: choice([0, 0, 1, 2, 3]), check_interval=0.1)):
    case 1:
        con.send_cmd(CMD.FULL_STOP)  # Switch to this case once the breaker returns 1
    case 2:
        con.set_motors_speed([666] * 4)  # Switch to this case once the breaker returns 2
    case 3:
        con.set_motors_speed([777] * 4)  # Switch to this case once the breaker returns 3
    case 0:
        con.set_motors_speed([555] * 4)  # Switch to this case if the breaker has never returned a non-zero value
    case _:
        raise ValueError("should never be here")


```

use `set_log_level` to silent the console to improve the performance in high pressure conditions

```python
from bdmc import set_log_level

"""
Logging DEBUG - Debugging information, used for detailed development phase logs, typically with a value of 10.
Logging INFO - Information message, used to inform the general program running status, with a value of 20.
Logging WARN - A warning message indicating that there may be a problem but the program is still running, with a value of 30.
Logging Error - Error message indicating an issue preventing the program from executing properly, with a value of 40.
Logging CRITICAL - Fatal error message indicating a serious system failure with a value of 50.
"""

set_log_level(50)  # set the log-level to 50, which makes logger only print the msg important than the CRITICAL logging

from logging import CRITICAL

set_log_level(CRITICAL)  # this has the same effect as above
```
