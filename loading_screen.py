from kivy.clock import Clock
from kivy.animation import Animation
from kivy.uix.screenmanager import Screen
from kivy.config import Config
from Machine import Machine
from time import sleep

import threading

machine = Machine()

class LoadingScreen(Screen):
    SCOOP_LEFT = -1
    SCOOP_RIGHT = -1
    timeout = 20

    def on_enter(self):
        #YOU MIGHT HAVE TO MOVE THIS TO MACHINE.PY
        scoop_thread = threading.Thread(target=machine.scoop_balls, args=(self.SCOOP_LEFT, self.SCOOP_RIGHT),
                                        daemon=False)
        load_thread = threading.Thread(target=self.loading_animation, daemon=True)

        if self.SCOOP_LEFT + self.SCOOP_RIGHT == 5:
            self.timeout = 30

        print(self.timeout)

        #load_thread.start()
        scoop_thread.start()
        Clock.schedule_once(self.switch_screen_main, self.timeout)

    def loading_animation(self):
        load = (Animation(size=(5, 10), duration=0.1) +
                Animation(size=(150, 10), duration=17))
        load.start(self.ids.progressBar)

    def switch_screen_main(self, dt = None):
        self.ids.progressBar.size = (5, 10)
        self.manager.current = 'main'

if __name__ == "__loading__":
    # Makes the window auto full screen
    Config.set('graphics', 'fullscreen', 'auto')
    Config.set('graphics', 'window_state', 'minimized')
    Config.write()
    LoadingScreen().run()
