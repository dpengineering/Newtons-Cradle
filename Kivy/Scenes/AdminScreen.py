from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen

PASSWORD = '7266'


class AdminScreen(Screen):
    entered = StringProperty('')

    def add_digit(self, digit):
        self.entered += str(digit)

    def remove_digit(self):
        self.entered = self.entered[:-1]

    def submit(self):
        if self.entered == PASSWORD:
            self.entered = ''
            self.manager.current = 'adminFunctionsScreen'

    def back_action(self):
        self.entered = ''
        self.manager.current = 'main'
