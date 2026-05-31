import logging
import time

import cflib.crtp
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander

URI = 'radio://0/80/2M'

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)


if __name__ == '__main__':
    # Initialize the low-level drivers (don't list the debug drivers)
    cflib.crtp.init_drivers(enable_debug_driver=False)

    with SyncCrazyflie(URI) as scf:
        # Ar    m the Crazyflie
        scf.cf.platform.send_arming_request(True)
        time.sleep(1.0)

        # We take off when the commander is created
        with MotionCommander(scf) as mc:
            print('Taking off!')
            time.sleep(1)

            print('Rolling right 0.2m at 0.73m/s')
            mc.right(2.0, velocity=0.73)
            time.sleep(1)

            print('Moving up 0.8m')
            mc.up(0.8)
            time.sleep(1)

            print('Move forward 2.0m at 0.73m/s')
            mc.forward(2.3, velocity=0.73)
            time.sleep(1)

            print('Moving up 0.8m')
            mc.up(0.8)
            time.sleep(1)

            print('Move forward 2.0m at 0.73m/s')
            mc.forward(1.5, velocity=0.73)
            time.sleep(1)


            print('Move down 1.7m')
            mc.down(1.7)
            time.sleep(1)

            print('Move forward 2.0m at 0.73m/')
            mc.forward(2.0, velocity=0.73)
            time.sleep(1)

            print('Rolling right 1.0m')
            mc.right(1.0, velocity=0.73)
            time.sleep(1)

            print('Turn left')
            mc.turn_left(180)
            time.sleep(1)

            print('Moving up 0.1m')
            mc.up(0.1)
            time.sleep(1)

            print('Move forward 2.0m at 0.73m/')
            mc.forward(5.0, velocity=0.73)
            time.sleep(1)

            # We land when the MotionCommander goes out of scope
            print('Landing!')
