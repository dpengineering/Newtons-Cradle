from kivy.clock import Clock
from kivy.animation import Animation
from kivy.uix.screenmanager import Screen
from kivy.config import Config
from Machine import Machine
from time import sleep
from functools import partial

import threading

machine = Machine()

class LoadingScreen(Screen):
    # SCOOP_LEFT = -1
    # SCOOP_RIGHT = -1

    def on_enter(self):
        #YOU MIGHT HAVE TO MOVE THIS TO MACHINE.PY
        SCOOP_LEFT = self.manager.get_screen('main').get_left_scoop()
        SCOOP_RIGHT = self.manager.get_screen('main').get_right_scoop()
        timeout = 25

        if SCOOP_LEFT == -1 or SCOOP_RIGHT == -1:
            print("oopsies")
            print("left:" + str(self.SCOOP_LEFT))
            print("right:" + str(self.SCOOP_RIGHT))
            return

        scoop_thread = threading.Thread(target=machine.scoop_balls, args=(SCOOP_LEFT, SCOOP_RIGHT),
                                        daemon=False)
        load_thread = threading.Thread(target=self.loading_animation, daemon=True)

        if SCOOP_LEFT + SCOOP_RIGHT == 5:
            timeout = 40

        print(timeout)

        #load_thread.start()
        #Clock.schedule_once(partial(machine.scoop_balls, SCOOP_LEFT, SCOOP_RIGHT), 5)
        machine.enable_motors()
        machine.double_Home()
        scoop_thread.start()
        self.loading_animation(timeout)
        Clock.schedule_once(self.switch_screen_main, timeout)

    def loading_animation(self, timeout):
        load = (Animation(size=(5, 10), duration=0.1) +
                Animation(size=(150, 10), duration=timeout))
        load.start(self.ids.progressBar)

    def switch_screen_main(self, dt = None):
        self.ids.progressBar.size = (5, 10)
        machine.double_Home()
        machine.disable_motors()
        sleep(1)
        self.manager.current = 'main'

if __name__ == "__loading__":
    # Makes the window auto full screen
    Config.set('graphics', 'fullscreen', 'auto')
    Config.set('graphics', 'window_state', 'minimized')
    Config.write()
    LoadingScreen().run()
