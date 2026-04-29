import kivy
from kivy.app import App
from kivy.uix.label import Label

kivy.require('1.11.1')


class MyFirstKivyApp(App):

    def build(self):
        return Label(text="Hello World!")

MyFirstKivyApp().run()