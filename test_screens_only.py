import os
os.environ["KIVY_NO_CONSOLELOG"] = "1" #Disables log in messaging on the console when booting up the project

import json
import logging
from kivy.app import App
from kivy.lang import Builder
from Kivy.Scenes import AdminScreen
from kivy.core.window import Window
from kivy.properties import AliasProperty, ObjectProperty, NumericProperty
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import *
from kivy.uix.popup import Popup
from kivy.vector import Vector
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.slider import Slider
from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.clock import Clock
from kivy.animation import Animation
from functools import partial
from kivy.config import Config
from kivy.core.window import Window
from pidev.MixPanel import MixPanel
from time import sleep

sm = ScreenManager()

from loading_screen import LoadingScreen
from main import MainScreen

class NewtonsCradleGUI(App):
    def build(self):
        """
        Called upon launching application
        :return: Screen Manager
        """
        Builder.load_file('Kivy/Scenes/main.kv')
        Builder.load_file('Kivy/Libraries/DPEAButton.kv')
        Builder.load_file('Kivy/Scenes/PauseScene.kv')
        Builder.load_file('Kivy/Scenes/AdminScreen.kv')
        Builder.load_file('loading_screen.kv')

        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(LoadingScreen(name='loading'))
        sm.add_widget(AdminScreen.AdminScreen(name='admin'))
        sm.add_widget(adminFunctionsScreen(name='adminFunctionsScreen'))

        return sm
