import kivy
kivy.require('1.0.6') # replace with your current kivy version !

from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.slider import Slider
from kivy.clock import Clock
from kivy.uix.pagelayout import PageLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.spinner import Spinner
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.properties import StringProperty
from kivy.graphics.instructions import Callback
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition, SlideTransition
import RPi.GPIO as GPIO

#GPIO
redledPin=23
grnledPin=22
switchPin=27
buttonPin=4
buzzerPin=17

GPIO.setmode(GPIO.BCM)
GPIO.setup(redledPin,GPIO.OUT)
GPIO.output(redledPin,GPIO.LOW)
GPIO.setup(grnledPin,GPIO.OUT)
GPIO.output(grnledPin,GPIO.LOW)
GPIO.setup(switchPin,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(buttonPin,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(buzzerPin,GPIO.OUT)
GPIO.output(buzzerPin,GPIO.LOW)

def press_callback(obj):
	if obj.state == "down":
		#print("button on")
		GPIO.output(redledPin,GPIO.HIGH)
		GPIO.output(grnledPin,GPIO.LOW)
	else:
		#print("button off")
		GPIO.output(redledPin,GPIO.LOW)
		GPIO.output(grnledPin,GPIO.HIGH)

def end_app(obj):
	GPIO.cleanup()
	print("clean")
	App.get_running_app().stop()

def detectorUpdate(obj,text):
	if text=='on':
		GPIO.output(grnledPin,GPIO.HIGH)
		GPIO.output(redledPin,GPIO.LOW)
	elif text == 'no data':
		GPIO.output(grnledPin,GPIO.LOW)
		GPIO.output(redledPin,GPIO.HIGH)
	elif text == 'off':
		GPIO.output(grnledPin,GPIO.LOW)
		GPIO.output(redledPin,GPIO.LOW)

class switchLabel(Label):
	def start(self):
		with self.canvas.before:
			self.col=Color(0,0,1,1)
			self.rec=Rectangle(pos=(400,300))
		Clock.schedule_interval(self.switch_callback,0.1)

	def switch_callback(self,dt):
		if GPIO.input(switchPin):
			#print("lever off")
			#self.canvas.remove(Color)
			#self.canvas.remove(Rectangle)
			self.canvas.clear()
			with self.canvas:
				self.col=Color(0,1,0,1)
				self.rec=Rectangle(pos=(400,300))

		else:
			#print("lever on")
			#self.canvas.remove(self.col)
			#self.canvas.remove(self.rec)
			self.canvas.clear()
			with self.canvas:
				self.col=Color(1,0,0,1)
				self.rect=Rectangle(pos=(400,300))

class FirstScreen(Screen):
	def __init__(self,**kwargs):
		super(FirstScreen,self).__init__(**kwargs)
		layout = GridLayout(cols=3,rows=2,spacing=30,padding=30,row_default_height=150)
		with layout.canvas.before:
			Color(.2,.2,.2,1)
			self.rect=Rectangle(size=(800,600), pos=layout.pos)

		self.add_widget(layout)

		Ledbutton = ToggleButton(text="led")
		Ledbutton.bind(on_press=press_callback)

		detectorStatus = Spinner(text='off',values=('on','no data', 'off'),size_hint=(None,None),size=(100,44))
		detectorStatus.bind(text=detectorUpdate)

		quitButton = Button(text="quit")
		quitButton.bind(on_press=end_app)

		switchStatus =  switchLabel(text="Switch")
		switchStatus.start()


		def transition2(obj):
			self.manager.transition=SlideTransition()
			self.manager.current='test2'
			self.manager.transition.direction='left'

		changescreenButton= Button(text="Screen 2")
		changescreenButton.bind(on_press=transition2)

		def buzz(obj):
			if obj.state=='down':
				print("on")
				#GPIO.output(buzzerPin,GPIO.HIGH)
				#obj.p = GPIO.PWM(buzzerPin,5000)
				obj.p.start(50.0)
			else:
				obj.p.stop()
				#GPIO.output(buzzerPin,GPIO.LOW)

		buzzButton=ToggleButton(text='Buzzer')
		buzzButton.bind(on_press=buzz)
		buzzButton.p=GPIO.PWM(buzzerPin,4500)

		layout.add_widget(Ledbutton)
		layout.add_widget(detectorStatus)
		layout.add_widget(switchStatus)
		layout.add_widget(quitButton)
		layout.add_widget(changescreenButton)
		layout.add_widget(buzzButton)

class SecondScreen(Screen):
	def __init__(self,**kwargs):
		super(SecondScreen,self).__init__(**kwargs)

		layout=PageLayout()

		def transitiontest(obj):
			self.manager.transition=SlideTransition()
			self.manager.current='test'
			self.manager.transition.direction='left'
		self.add_widget(layout)

		bio = 'LIGO INFO HERE text text texttext text text  text  text  text  text  text  text  text  text  text  text  text  text  text  text  text  text  text  text  text  text  text  text  text  text  text  text  text  text  text  text  text  text  text  text  text '

		label1=Label(text=bio,text_size=(layout.width,None),size_hint_y=None)
		button1=Button(text="Back to Screen 1")
		button1.bind(on_press=transitiontest)
		layout.add_widget(label1)
		layout.add_widget(button1)


sm = ScreenManager()
sm.add_widget(FirstScreen(name='test'))
sm.add_widget(SecondScreen(name='test2'))

class MyApp(App):
	def menu_callback(obj,dt):
		if GPIO.input(buttonPin):
			sm.transition=FadeTransition()
			sm.current='test'
			return
		else:
			return

	def build(self):

#		layout = GridLayout(cols=2,rows=2,spacing=30,padding=30,row_default_height=150)
#
#		with layout.canvas.before:
#			Color(.2,.2,.2,1)
#			self.rect=Rectangle(size=(800,600), pos=layout.pos)
#
#		Ledbutton = ToggleButton(text="led")
#		Ledbutton.bind(on_press=press_callback)
#
#		detectorStatus = Spinner(text='off',values=('on','no data', 'off'),size_hint=(None,None),size=(100,44))
#		detectorStatus.bind(text=detectorUpdate)
#
#		quitButton = Button(text="quit")
#		quitButton.bind(on_press=end_app)
#
#		switchStatus =  switchLabel(text="Switch")
#		switchStatus.start()
#		layout.add_widget(Ledbutton)
#		layout.add_widget(detectorStatus)
#		layout.add_widget(switchStatus)
#		layout.add_widget(quitButton)
		Clock.schedule_interval(self.menu_callback,1/50)

		return sm

if __name__ == '__main__':
	MyApp().run()

