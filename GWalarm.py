#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug  5 17:04:33 2019

@author: christian
"""

import kivy
kivy.require('1.11.0')

from kivy.config import Config
Config.set('graphics','width','800')
Config.set('graphics','height','480')
Config.set('kivy','default_font',[
           './fonts/OpenSans-Light.ttf','./fonts/OpenSans-Regular.ttf','./fonts/OpenSans-LightItalic.ttf',
           './fonts/OpenSans-Bold.ttf'])

import threading
import time
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import AsyncImage
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle
from kivy.properties import ListProperty, ObjectProperty, StringProperty, AliasProperty, DictProperty, NumericProperty
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition, SlideTransition, NoTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.carousel import Carousel
from kivy.uix.popup import Popup
from kivy.uix.recycleview import RecycleView
from kivy.uix.behaviors  import ButtonBehavior, ToggleButtonBehavior
from kivy.uix.modalview import ModalView
from kivy.animation import Animation
from kivy.uix.slider import Slider
from kivy.lang.builder import Builder

from detector_monitorv2 import statusdetect
from sync_database import sync_database
import gcn
from gcn_test import process_gcn
import requests
from bs4 import BeautifulSoup
from tables import * 
import datetime
import os
import re
import numpy as np
from matplotlib.image import imread
from matplotlib.pyplot import imsave
import random
import lxml
import math
import scipy.constants


'''CHECK IF ON RASPBERRY PI FOR GPIO FUNCTIONALITY'''
if os.uname()[4][:3] == 'arm':

    import RPi.GPIO as GPIO
    buzzPin=5
    testPin=6
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(buzzPin,GPIO.OUT)
    GPIO.setup(testPin,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
    GPIO.output(buzzPin,GPIO.LOW)
    
    '''test if hardware is present - shows buzzer volume to user'''
    GPIO.output(buzzPin,GPIO.HIGH)
    time.sleep(0.5)
    if GPIO.input(testPin):
        GPIO.output(buzzPin,GPIO.LOW)
        import board
        import neopixel
        neoPin = board.D12
        num_leds = 8
        pixels = neopixel.NeoPixel(neoPin,num_leds,pixel_order=neopixel.RGB,auto_write=False)
        print('Hardware has been detected. Enabling...')
        
    else:
        GPIO.output(buzzPin,GPIO.LOW)
        print('No hardware detected - the hardware is not present.')
        GPIO.cleanup()
        pixels = None
        buzzPin= None
else:
    print('No hardware detected - not on RPi.')
    pixels = None
    buzzPin= None

'''TEXT TO SPEECH INIT'''
#import pyttsx3
#engine = pyttsx3.init()
#engine.setProperty('voice','english-north')
#engine.setProperty('rate',130)
from gtts import gTTS

Builder.unload_file("GWalarm.kv")
Builder.load_file('GWalarm.kv')

'''are we in the right folder? Preserves img functionality'''
if os.path.basename(os.getcwd()) != 'event_data':
    os.chdir('./event_data')

class Event(IsDescription):
    AlertType=StringCol(30)
    BBH=StringCol(30)
    BNS=StringCol(30)
    FAR = StringCol(30)
    GraceID=StringCol(30)
    Group=StringCol(30)
    HasNS=StringCol(30)
    HasRemnant=StringCol(30)
    Instruments = StringCol(30)
    MassGap=StringCol(30)
    NSBH=StringCol(30)
    Terrestrial = StringCol(30)
    skymap=StringCol(30)
    DetectionTime=StringCol(30)
    UpdateTime=StringCol(30)
    MassGap=StringCol(30)
    Distance=StringCol(30)
    Revision=StringCol(30)

global flag
global main_flag
global newevent_flag
flag = 0
main_flag=0
newevent_flag=0



class HisColLabel(ToggleButtonBehavior,Label):
    sorttype=ObjectProperty()
    newsort=ObjectProperty()
    names=ObjectProperty()
    specialnames=ObjectProperty()
    lookout = ObjectProperty()
    backcolors=ObjectProperty()
    primed=NumericProperty()
    imgsource=ObjectProperty()
    
    def on_press(self):
        self.primed=1
        for child in self.parent.children:
            if child.primed != 1:
                child.imgsource='./neutral.png'
        self.primed=0

    def on_state(self,widget,value):    
        Clock.schedule_once(lambda dt:self.on_state_for_real(widget,value),0)
    def on_state_for_real(self,widget,value):
        global flag
        flag = 1
        if value == 'down':
            self.newsort = self.sorttype+' Descending'
            self.imgsource='./ascending.png'

        else:
            self.newsort = self.sorttype+' Ascending'
            self.imgsource='./descending.png'
        t2 = threading.Thread(target=historyUpdatev2,args=(App.get_running_app().root.get_screen('history').ids.rv,
                                                         self.names,self.specialnames,self.lookout,
                                                         self.backcolors,self.newsort),daemon=True)
        t2.start()

class EventInfoHeader(GridLayout):
    paramdict=ObjectProperty()
    var=StringProperty('0')
    speaker_color=ObjectProperty()
    
    def read_event_params(self):
        stats = []
        lookoutfor = ['BBH','BNS','NSBH','MassGap','Terrestrial']
        for name in lookoutfor:
            stats.append(float(self.paramdict[name].strip('%')))
        ev_type= lookoutfor[np.argmax(stats)]

        if ev_type == 'Terrestrial':
            processType = 'False Alarm'
        elif ev_type == 'BNS':
            processType = 'Binary Neutron Star merger'
        elif ev_type == 'BBH':
            processType = 'Binary Black Hole merger'
        elif ev_type == 'MassGap':
            processType = 'MassGap event'
        elif ev_type == 'NSBH':
            processType = 'Neutron Star Black Hole merger'
            
        far = self.paramdict['FAR'].split()
        far[2] = "{0:.0f}".format(float(far[2]))
        far = " ".join(far)
        
        dist = float(self.paramdict['Distance'].split()[0])
        distly = dist*3.262e+6
        
        insts = self.paramdict['Instruments']
        insts_out =''
        if 'V1' in insts:
            insts_out+='Virgo, '
        if 'L1' in insts:
            insts_out+='LIGO Livingston, '
        if 'H1' in insts:
            insts_out+='LIGO Hanford, '
        processed = insts_out.split(',')[0:-1]
        insts_formed = ''
        for i,elem in enumerate(processed):
            if i == len(processed)-1 and len(processed) != 1:
                insts_formed+= ' and '+ elem
            else:
                insts_formed+= elem
        InitialToken = 'This event was detected by '+insts_formed+' . '
        EventTypeToken = 'The event is most likely to be a ' + processType + ', with a probability of ' + "{0:.0f}".format(float(self.paramdict[ev_type][:-1])-1) + ' percent. '
        FalseAlarmToken = 'The false alarm rate of the event is ' + far +'. '
        DistanceLookBackToken = 'It is approximately ' + oom_to_words(dist,'Megaparsecs',tts='on') + ' away, which is equivalent to a lookback time of '+ oom_to_words(distly,'years',tts='on')+'. '
    
        tokens=[InitialToken,EventTypeToken,FalseAlarmToken,DistanceLookBackToken]
        renderthreads = []
        def render_audio(token,num):
            print(token)
            tts=gTTS(token)
            tts.save('readout'+num+'.mp3')
            
        for k,token in enumerate(tokens):
#            engine.say(token)
#            engine.runAndWait()
            t=threading.Thread(target=render_audio,args=(token,str(k)))
            renderthreads.append(t)
            t.start()
        for t in renderthreads:
            t.join()
        maximum = k
        print(self.var)
        for i in range(maximum+1):
            if self.var == '0':
                os.system("mpg321 --stereo readout"+str(i)+".mp3")
    def read_aloud(self):
        self.speaker_color=[0.8,0.8,0.8,0.4]
        t=threading.Thread(target=self.read_event_params)
        t.start()
    def speaker_back(self):
        self.speaker_color=[0,0,0,0]
        

class HistoryScreenv2(Screen):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        if os.path.basename(os.getcwd()) != "event_data":
            try:
                os.chdir("./event_data")
            except:
                os.mkdir("./event_data")
                os.chdir("./event_data")    
                
        while True:
            try:
                h5file = open_file("Event Database",mode="r",title="eventinfo")
                break
            except:
                print("file in use... trying again in 5s")
                time.sleep(5)
        try:
            h5file.root.events
        except NoSuchNodeError:
            time.sleep(5)
            pass
        #grab a table, it doesn't matter which one!
        x=0
        for table in h5file.iter_nodes(where="/events",classname="Table"):
            tables=table
            if x==0:
                break
        
        def receive():
                gcn.listen(host="209.208.78.170",handler=process_gcn)
        t4 = threading.Thread(target=receive,daemon=True,name='gcnthread')
        t4.start()
            
        names = tables.colnames
#        num_events = len(h5file.list_nodes(where="/events",classname="Table"))
        h5file.close()
        specialnames=['GraceID','Distance','Instruments','FAR','UpdateTime']
        lookoutfor = ['BBH','BNS','NSBH','MassGap','Terrestrial']
        backcolors = [[202/255,214/255,235/255,0.8],[179/255,242/255,183/255,0.8],
                      [238/255,242/255,179/255,0.8],[231/255,179/255,242/255,0.8],
                      [242/255,179/255,179/255,0.8]]
        
        for child in self.ids.HisCols.children:
            child.names = names
        t2 = threading.Thread(target=historyUpdatev2,args=(self.ids.rv,names,specialnames,lookoutfor,backcolors,'Time Descending',True),daemon=True)
        t2.start()
        
    def stupid(obj):
        def refresh_all(arg):
            global main_flag
            main_flag = 1
            
            #stop all threads
#            for t in threading.enumerate():
#                print(t.name)
                
            App.get_running_app().stop()
            App.get_running_app().root_window.close()
            print('shutdown')
            #time.sleep(5)
            sync_database()
            #Wait for it to finish....
            print('done - restart away')
        content = Button(text='Ok')
        content.bind(on_press=refresh_all)
        confirm = Popup(title='Are you sure?',content=content,size_hint=(0.4,0.4))
        confirm.open()
        
        
def oom_to_words(inputval,unit,tts='off'):
    far_oom = int(math.log10(inputval))
    far_token = ''
    inputval = float("{0:.2f}".format(inputval))
    if tts == 'on':
        if far_oom >= 3 and far_oom < 6:
            far_token = 'Thousand'
        inputval = round(inputval/10**far_oom)*10**far_oom
    if far_oom >= 6 and far_oom < 9:
        far_token = 'Million'
    elif far_oom >= 9 and far_oom < 12:
        far_token = 'Billion'
    elif far_oom >= 12 and far_oom < 15:
        far_token='Trillion'
    elif far_oom >= 15 and far_oom < 18:
        far_token ='Quadrillion'
    elif far_oom >= 18 and far_oom < 21:
        far_token = 'Quintillion'
    elif far_oom >= 21 and far_oom < 24:
        far_token = 'Sextillion'
    elif far_oom >= 24:
        far_token = 'Septillion'
    far_token+= ' '+unit
    far_rem_oom = far_oom % 3
    far_div_oom = far_oom - far_rem_oom
#    print(inputval/(10**far_div_oom) + far_token)
    if tts=='on':
        return_string = str(int(float("{0:.2f}".format(inputval/(10**far_div_oom))))) +' '+ far_token 
    else:
        return_string = str(float("{0:.2f}".format(inputval/(10**far_div_oom)))) +' '+ far_token 
    return return_string

def process_FAR(FAR,tts='off'):
    per_yr = FAR*scipy.constants.year
    if per_yr <= 1:
        oneinyr = 1/per_yr
    else:
        oneinyr = per_yr
#    if len(str(oneinyr).split('.')[0]) >= 5 or 'e' in str(oneinyr):
#        val = "One every "+str("{0:.2e}".format(oneinyr))+" yrs"
#    else:
#        val = "One every "+str("{0:.3f}".format(oneinyr))+" yrs"
        
    val = 'One every ' + oom_to_words(oneinyr,'years',tts)
    return val
    
def historyUpdatev2(rv,names,specialnames,lookoutfor,backcolors,sorttype='Time Descending',led_init = False):
    print('Begin History update')
    '''An important function that is responsible for populating and repopulating the history screen.'''
    
    global flag
    global main_flag
    #reset stop flag
    main_flag=0
    if os.path.basename(os.getcwd()) != "event_data":
        try:
            os.chdir("./event_data")
        except:
            os.mkdir("./event_data")
            os.chdir("./event_data")    
        
    #initial check to ensure file exists with necessary groupings
    while True:
        try:
            h5file = open_file("Event Database",mode="r",title="eventinfo")
            break
        except:
            print("file in use... trying again in 5s")
            time.sleep(5)
    try:
        h5file.root.events
    except NoSuchNodeError:
        time.sleep(5)
        pass
    h5file.close()
    
    #initial stat
    stats = os.stat("./Event Database")
    lastaccess= stats.st_mtime
    first = 1
    while True:
        stats = os.stat("./Event Database")
        access = stats.st_mtime 
        if access != lastaccess or first == 1:
            lastaccess=access
            
            while True:
                try:
                    h5file = open_file("Event Database",mode="r",title="eventinfo")
                    break
                except:
                    print("file in use... trying again in 5s")
                    time.sleep(5)
            
            #get all tables
            tables = [table for table in h5file.iter_nodes(where="/events",classname="Table")]
            sort_vars = []
            
            widgetids = []
            if rv.data:
                nomlist = rv.data[0]['namelist']
                idindex = nomlist.index('GraceID')
                widgetids= [elem['row'][idindex] for elem in rv.data]
            
            '''Iterate through all events, re-drawing row-by-row the history viewer'''
            for table in tables:
                row=table[-1]
                if 'Time' in sorttype:
                    sort_vars.append(row['UpdateTime'].decode().split()[0])
                elif 'Distance' in sorttype:
                    sort_vars.append(float(row['Distance'].decode().split()[0]))
                elif 'GraceID' in sorttype:
                    string = str(row['GraceID'].decode())
                    sort_vars.append(int(re.sub("[a-zA-Z]","",string)))
                elif 'FAR' in sorttype:
                    sort_vars.append(float(row['FAR'].decode()))#.split()[2]))
                elif 'Instruments' in sorttype:
                    sort_vars.append(row['Instruments'].decode())
            if sort_vars != []:
                if 'Descending' in sorttype:
                    try:
                        tables = [x for _,x in reversed(sorted(zip(sort_vars,tables)),key=len[0])]
                    except TypeError:
                        tables2=[]
                        sort_indexes = reversed(np.argsort(np.array(sort_vars)))
                        for index in sort_indexes:
                            tables2.append(tables[index])
                        tables=tables2
                elif 'Ascending' in sorttype:
                    try:
                        tables = [x for _,x in (sorted(zip(sort_vars,tables)))]
                    except TypeError:
                        tables2=[]
                        sort_indexes = (np.argsort(np.array(sort_vars)))
                        for index in sort_indexes:
                            tables2.append(tables[index])
                        tables=tables2
            new_data = []
            for i,table in enumerate(tables):
                to_add_to_data={}
                row = table[-1]
                orderedrow = []
                to_add_to_data['namelist']=names
                to_add_to_data['name']=row['GraceID'].decode()
                for key in names:
                    if key == 'FAR':
                        val = process_FAR(float(row[key].decode()))
                        orderedrow.append(val)
                    else:       
                        orderedrow.append(row[key].decode())
                to_add_to_data['row'] = orderedrow
                if row['GraceID'].decode() not in widgetids:
                    if first == 0:
                        if row['Revision'].decode() == '1':
                            '''NEW EVENT!!!'''
                            global newevent_flag
                            if newevent_flag == 0:
                                newevent_flag=1
                
                for j in range(len(specialnames)):
                    string=row[specialnames[j]]
                    if specialnames[j] == 'Distance':
                        to_add_to_data['text'+str(j)] = string.decode().replace('+-',u'\xb1')
                    elif specialnames[j] == 'FAR':
                        to_add_to_data['text'+str(j)] = process_FAR(float(string.decode()))
                    else:
                        to_add_to_data['text'+str(j)] = string.decode() 
                stats = []
                for name in lookoutfor:
                    stats.append(float(row[name].decode().strip('%')))
                to_add_to_data['bgcol'] = backcolors[np.argmax(stats)]
                new_data.append(to_add_to_data)
                
                if i == 0 and sorttype == 'Time Descending':
                    rv.winner = lookoutfor[np.argmax(stats)]
                
            rv.data = new_data
            
            print('Event History Updated...')
            if pixels:
                type_notif(rv.winner)
            h5file.close()
            #reset the flag
            first = 0

        waittime = 5   
        i=0
        while i < waittime:
            if flag ==1:
                print('History Thread restarting...')
                flag=0
                return
            if main_flag ==1:
                print('history thread closing...')
                return
            i+=0.2
            time.sleep(0.2)

class DevPop(ModalView):
    def simulate(self):
        global newevent_flag
        if newevent_flag == 0:
            #don't start if it's not safe
            self.dismiss()
            
            def process():
                payload=open("EventDemonstration.xml",'rb').read()
                string='Thisisaneventsim'
                root=lxml.etree.fromstring(payload)
                payload+=string.encode()
                process_gcn(payload,root)
                global newevent_flag
                newevent_flag=1
                
            t = threading.Thread(target=process)
            t.start()
        else:
            content = Label(text='The event is coming, be patient!')
            popu = Popup(title="It's on the way...",content=content)
            popu.open()
            Clock.schedule_interval(lambda dt: popu.dismiss(),5)

class InfoPop(ModalView):
    namelist=ObjectProperty()
    row=ObjectProperty()
    def gloss_open(self):
        descdict = {'GraceID': 'Identifier in GraceDB', 'AlertType': 'VOEvent alert type', 
            'Instruments': 'List of instruments used in analysis to identify this event', 
            'FAR': 'False alarm rate for GW candidates with this strength or greater', 
            'Group': 'Data analysis working group', 
            'BNS': 'Probability that the source is a binary neutron star merger (both objects lighter than 3 solar masses)', 
            'NSBH': 'Probability that the source is a neutron star-black hole merger (primary heavier than 5 solar masses, secondary lighter than 3 solar masses)', 
            'BBH': 'Probability that the source is a binary black hole merger (both objects heavier than 5 solar masses)', 
            'Terrestrial': 'Probability that the source is terrestrial (i.e., a background noise fluctuation or a glitch)', 
            'HasNS': 'Source classification: binary neutron star (BNS), neutron star-black hole (NSBH), binary black hole (BBH), MassGap, or terrestrial (noise)', 
            'HasRemnant': 'Probability that at least one object in the binary has a mass that is less than 3 solar masses',
            'Distance':'Posterior mean distance to the event (with standard deviation) in MPc',
            'DetectionTime':'The mean date & time at which the event was first detected',
            'UpdateTime': "The date & time of the most recent update to this event's parameters",
            'MassGap':"Compact binary systems with at least one compact object whose mass is in the hypothetical 'mass gap' between neutron stars and black holes, defined here as 3-5 solar masses.",
            'Revision':"The number of revisions (updates) made to this event's parameters"}
        content = GridLayout(rows=2)
        _glossary = Glossary(size_hint_y=0.9)
        descdata=[]
        sortedkeys=[]
        for key in descdict:
            sortedkeys.append(key)
        sortedkeys.sort()
        for key in sortedkeys:
            descdata.append({'nom':key,'desc':descdict[key]})
        _glossary.data = descdata
        content.add_widget(_glossary)
        but = Button(text='Done',size_hint_y=0.1)
        content.add_widget(but)
        pop = Popup(title='Glossary',content=content,size_hint=(0.25,1),pos_hint={'x':0,'y':0})
        but.bind(on_press=pop.dismiss)
        pop.open()
    
    def on_open(self):
        self.var = '0'
    def on_dismiss(self):
        Clock.schedule_once(lambda dt: self.fin_dismiss(),0.25)
    def fin_dismiss(self):
            self.ids.caro.index=0
            self.var = '1'
        
class GlossDefLabel(Label):
    nom=ObjectProperty()
    desc=ObjectProperty()

class Glossary(RecycleView):
    pass
        
class EventContainer(ButtonBehavior,GridLayout):
    name=ObjectProperty()
    namelist=ListProperty(['test1','test2'])
    row = ListProperty(['test1','test2'])
    pop = ObjectProperty()
    img= StringProperty()
    text0=StringProperty('tobereplaced')
    text1=StringProperty('tobereplaced')
    text2=StringProperty('tobereplaced')
    text3=StringProperty('tobereplaced')
    text4=StringProperty('tobereplaced')

    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self.finish_init,0)
        
    def finish_init(self,dt):
        self.pop = InfoPop(namelist=self.namelist,row=self.row)
        
    def details(self):
        self.pop.namelist = self.namelist
        self.pop.row = self.row
        self.pop.background_color=self.bgcol
        self.pop.background_color[3] = 1
        self.pop.open()

def statusupdate(obj):
    global main_flag
    main_flag=0
    while True:
        data,stats,names = statusdetect()
        
        for i,elem in enumerate(data):
            setattr(obj,'det'+str(i+1)+'props',elem)
        
        '''LED CONTROL'''
        if pixels:
            order = ['GEO 600','LIGO Livingston','LIGO Hanford','Virgo']
            statindexes = [names.index(item) for item in order]
            stats = [x for _,x in sorted(zip(statindexes,stats))]

            for i,stat in enumerate(stats):
                if stat == 0:
                    #red
                    pixels[i+2] = (255,0,0)
                if stat == 1:
                    #orange
                    pixels[i+2] = (228,119,10) 
                if stat == 2:
                    #green
                    pixels[i+2] = (17,221,17)
                if stat == 3:
                    #yellow
                    pixels[i+2] = (0,0,0)
            pixels.show()
        
        waittime = 30
        i = 0
        while i < waittime:
            if main_flag == 1:
                print('Status Thread closing...')
                return
            i+=1
            time.sleep(1)

def plotupdate(obj):
    global main_flag
    main_flag=0
    while True:
        if os.path.basename(os.getcwd()) != 'event_data':
            try:
                os.chdir("./event_data")
            except:
                os.mkdir("./event_data")
                os.chdir("./event_data")
        #formulate the url to get today's
        date = datetime.datetime.today()
        sort_date = [str(date.year),str(date.month).zfill(2),str(date.day).zfill(2)]
        datestring = sort_date[0]+sort_date[1]+sort_date[2]
        url = "https://www.gw-openscience.org/detector_status/day/"+datestring+"/"
        url2 = "https://www.gw-openscience.org/detector_status/day/"+datestring+"/instrument_performance/analysis_time/"
        #grab the soup and parse for links + descripts
        date = datetime.datetime.today()
        try:
            sort_date = [str(date.year),str(date.month).zfill(2),str(date.day).zfill(2)]
            datestring = sort_date[0]+sort_date[1]+sort_date[2]
            url = "https://www.gw-openscience.org/detector_status/day/"+datestring+"/"
            url2 = "https://www.gw-openscience.org/detector_status/day/"+datestring+"/instrument_performance/analysis_time/"
            resp=requests.get(url)
            r = resp.text
            while True:
                if 'Not Found' in str(r):
                    date = date - datetime.timedelta(days=1)
                    sort_date = [str(date.year),str(date.month).zfill(2),str(date.day).zfill(2)]
                    datestring = sort_date[0]+sort_date[1]+sort_date[2]
                    url = "https://www.gw-openscience.org/detector_status/day/"+datestring+"/"
                    url2 = "https://www.gw-openscience.org/detector_status/day/"+datestring+"/instrument_performance/analysis_time/"
                    

                '''check the first link to make sure it actually loads - problem occurs at midnight GMT'''
                resp=requests.get(url)
                r = resp.text
                soup=BeautifulSoup(r,"lxml")
                
                try:
                    for link in soup.find_all("a"):
                        linkstr = str(link.get("href"))
                        if 'png' in linkstr:
                            filepath = 'Detector_Plot_0.png'                
                            source='https://www.gw-openscience.org'+linkstr
                            os.system("curl --silent -0 "+ source+ ' > ' + filepath)
                            img = imread("./"+filepath)
                            break
                    break
                except:
                    r+='Not Found'
                    continue
            soup=BeautifulSoup(r,"lxml")
            resp2 = requests.get(url2)
            r2 = resp2.text
            soup2 = BeautifulSoup(r2,"lxml")
        except:
            print("URL Error: URL to the Range plots is broken : check online")                
        descripts=[]
        paths=[]
        i=0
        for link in soup.find_all("a"):
            linkstr = str(link.get("href"))
            if 'png' in linkstr:
                filepath = 'Detector_Plot_'+str(i)+'.png'                
                source='https://www.gw-openscience.org'+linkstr
                os.system("curl --silent -0 "+ source+ ' > ' + filepath)
                descripts.append(str(link.get("title")))
                paths.append(filepath)
                i+=1
        for link in soup2.find_all("a"):
            linkstr=str(link)
            if 'png' and 'COINC' in linkstr:
                filepath = 'Detector_Plot_'+str(i)+'.png'
                descripts.append(str(link['title']))
                source= 'https://www.gw-openscience.org'+str(link.get("href"))
                os.system("curl --silent -0 "+ source+ ' > ' + filepath)
                paths.append(filepath)
                
                img = imread("./"+filepath)
                cropimg = img[50:550,100:1200,:]
                imsave("./Detector_Plot_3.png",cropimg,format='png')
                i+=1
                break

        obj.imgsources = paths
        obj.descs = descripts
        waittime=3600
        i=0
        while i < waittime:
            if main_flag == 1:
                print('Plot Thread closing...')
                return
            i+=5
            time.sleep(5)

            
def type_notif(e_type,flasher='off'):
    def color(event_type):
        if event_type == 'Terrestrial':
            pixels[1] = (255,80,70)
        elif event_type == 'NSBH':
            pixels[1] = (255,255,25)
        elif event_type == 'BBH':
            pixels[1] = (122,180,255)
        elif event_type == 'MassGap':
            pixels[1] = (245,66,230)
        elif event_type == 'BNS':
            pixels[1] = (102,255,112)
        pixels.show()
    if flasher == 'on':
        duration=10
        step=0.5
        j = 0
        while j < duration:
            color(e_type)
            time.sleep(step)
            pixels[1]=(0,0,0)
            pixels.show()
            time.sleep(step)
            j+=step
        color(e_type)
    else:
        color(e_type)  
            
def buzz(times,step):
    i=0
    while i < times:
        GPIO.output(buzzPin,GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(buzzPin,GPIO.LOW)
        time.sleep(0.05)
        GPIO.output(buzzPin,GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(buzzPin,GPIO.LOW)
        time.sleep(0.05)
        GPIO.output(buzzPin,GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(buzzPin,GPIO.LOW)
        time.sleep(0.05)
        GPIO.output(buzzPin,GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(buzzPin,GPIO.LOW)
        i+=1
        time.sleep(step)


class VolSlider(BoxLayout):
    def changevol(self,value):
        val = self.ids.slider.value
        if pixels:
            os.system("amixer set PCM "+str(val)+"%")


class MainScreenv2(Screen):
    notif_light_var=NumericProperty(0)

    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        event_waiting_thread = threading.Thread(target=self.event_waiting)
        event_waiting_thread.start()
        
    def event_waiting(self):
        '''New event popup handler'''
        global newevent_flag
        global main_flag
        newevent_flag=0
        main_flag=0
                    
        while True:
            while True:
                #check for the flag once per minute (same rate the file is polled)
                if newevent_flag == 1:
                    #skip a level up to execute the rest of the loop, then back to waiting.
                    if buzzPin is not None:
                        buzzthread = threading.Thread(target=buzz,args=(3,1))
                        buzzthread.start()
                    if pixels:
                        notifthread = threading.Thread(target=self.notifier)
                        notifthread.start()
                    print('New event has been detected!!')
                    break
                if main_flag == 1:
                    print('Event listener #2 closing...')
                    #return takes you right out of the function
                    return
                time.sleep(5)
            
            #Close all active popups - prevents crashes if left unattended for a while.
            for widg in App.get_running_app().root_window.children:
                if isinstance(widg,InfoPop):
                    widg.dismiss()
            
            #Read in the new event
            if os.path.basename(os.getcwd()) != "event_data":
                try:
                    os.chdir("./event_data")
                except:
                    os.mkdir("./event_data")
                    os.chdir("./event_data")
            while True:
                try:
                    h5file = open_file("Event Database",mode="a",title="eventinfo")
                    break
                except:
                    print("file in use... trying again in 5s")
                    time.sleep(5)
            try:
                h5file.root.events
            except NoSuchNodeError:
                time.sleep(5)
                pass      
            
            tabs=[tab.name for tab in h5file.list_nodes("/events")]
            if 'EventSimulation' not in tabs:
                eventid = list(reversed(sorted(tabs)))[0]
            else:
                eventid = 'EventSimulation'
            for tab in h5file.list_nodes("/events"):
                if tab.name == eventid:
                    new_event_table=tab
            namelist = new_event_table.colnames
            new_event_row = new_event_table[-1]
            orderedrow = []
            for key in namelist:
                orderedrow.append(new_event_row[key].decode())
            name_row_dict = dict(zip(namelist,orderedrow))
            
            stats = []
            lookoutfor = ['BBH','BNS','NSBH','MassGap','Terrestrial']
            for name in lookoutfor:
                stats.append(float(new_event_row[name].decode().strip('%')))
            winner = lookoutfor[np.argmax(stats)]
            if pixels:
                t = threading.Thread(target=type_notif,args=(winner,'on'))
                t.start()
                
            speech_thread  = threading.Thread(target=self.read_event_params,args=(name_row_dict,winner))
            speech_thread.start()

            if  eventid == 'EventSimulation':
                h5file.remove_node("/events",'EventSimulation')
            h5file.close()
            
            newevent_flag=0
    
            pop = InfoPop(namelist=namelist,row=orderedrow)
            extralabel = Label(text='[b]NEW EVENT[/b]',markup=True,font_size=20,halign='left',color=[0,0,0,1],size_hint_x=0.2)
            pop.ids.header.add_widget(extralabel)
            #pop.bind(on_dismiss=lambda dt:)
            if pixels:
                pop.ids.but1.bind(on_press=self.notif_off)
                pop.ids.but2.bind(on_press=self.notif_off)
            pop.open()

    def notifier(self):
        self.notif_light_var=1
        rand1 = round(random.random()*255)
        rand2 = round(random.random()*255)
        rand3 = round(random.random()*255)
                
        while self.notif_light_var==1:
            pixels[0] = (rand1,rand2,rand3)
            pixels.show()
            time.sleep(0.005)
            rand1+=3
            rand2+=2
            rand3+=1
            if rand1 > 255:
                rand1-=255
            if rand2 > 255:
                rand2 -= 255
            if rand3 > 255:
                rand3 -= 255
            
        pixels[0] = (0,0,0)
        pixels.show()
    
    def notif_off(self,instance):
        self.notif_light_var = 0
    
    def read_event_params(self,paramdict,ev_type):
        if ev_type == 'Terrestrial':
            processType = 'False Alarm'
        elif ev_type == 'BNS':
            processType = 'Binary Neutron Star merger'
        elif ev_type == 'BBH':
            processType = 'Binary Black Hole merger'
        elif ev_type == 'MassGap':
            processType = 'MassGap event'
        elif ev_type == 'NSBH':
            processType = 'Neutron Star Black Hole merger'
            
        far = float(paramdict['FAR'])
        
        dist = float(paramdict['Distance'].split()[0])
        distly = dist*3.262e+6
        
        insts = paramdict['Instruments']
        insts_out =''
        if 'V1' in insts:
            insts_out+='Virgo, '
        if 'L1' in insts:
            insts_out+='LIGO Livingston, '
        if 'H1' in insts:
            insts_out+='LIGO Hanford, '
        processed = insts_out.split(',')[0:-1]
        insts_formed = ''
        for i,elem in enumerate(processed):
            if i == len(processed)-1 and len(processed) != 1:
                insts_formed+= ' and '+ elem
            else:
                insts_formed+= elem
        
        InitialToken = 'A new event has been detected by '+insts_formed+' . '
        EventTypeToken = 'The event is most likely to be a ' + processType + ', with a probability of ' + "{0:.0f}".format(float(paramdict[ev_type][:-1])-1) + ' percent. '
        FalseAlarmToken = 'The false alarm rate of the event is ' + process_FAR(far,tts='on') +'. '
        DistanceLookBackToken = 'It is approximately ' + oom_to_words(dist,'Megaparsecs',tts='on') + ' away, which is equivalent to a lookback time of '+ oom_to_words(distly,'years',tts='on')+'. '
    
        tokens=[InitialToken,EventTypeToken,FalseAlarmToken,DistanceLookBackToken]
        renderthreads = []
        def render_audio(token,num):
            print(token)
            tts=gTTS(token)
            tts.save('readout'+num+'.mp3')
            
        for k,token in enumerate(tokens):
#            engine.say(token)
#            engine.runAndWait()
            t=threading.Thread(target=render_audio,args=(token,str(k)))
            renderthreads.append(t)
            t.start()
        for t in renderthreads:
            t.join()
        maximum = k
        for i in range(maximum+1):
            print(i)
            os.system("mpg321 --stereo readout"+str(i)+".mp3")
        
class StatusScreenv2(Screen):
    det1props = ListProperty()
    det2props = ListProperty()
    det3props = ListProperty()
    det4props = ListProperty()
    det5props = ListProperty()   
    bios=ListProperty()
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.bios=(['LIGO Livingston is one of two trailblazing gravitational wave detectors (the other being LIGO Hanford). The observatory uses ultra-high-vacuum technology to achieve extremely precise measurement capability. \n Forming a pair seperated by over 3000km, LIGO Hanford and Livingston observed gravitational waves for the first time in history in February, 2016.',
                       'LIGO Hanford is one of two trailblazing gravitational wave detectors (the other being LIGO Livingston). The observatory uses ultra-high-vacuum technology to achieve extremely precise measurement capability. \n Forming a pair seperated by over 3000km, LIGO Hanford and Livingston observed gravitational waves for the first time in history in February, 2016.',
                       'GEO600 is a gravitational wave detector located in Hanover, Germany. Although smaller than other counterparts worldwide, the detector is still capable of extremely precise measurement, only a few orders of magnitude less sensitive than significantly larger detectors. It has been a vital proof of concept for many advanced technologies and features that will surely be seen in future gravitational wave observatories. ',
                       "The Virgo interferometer is Europe's largest to date. Currently, Virgo is being modified and improved to its next stage, 'Advanced Virgo', which aims to improve sensitivity by a factor of 10 by installing new adaptive-optic mirror systems and additional cryotraps to prevent the entry of residual particles. \n Virgo made its first GW detection, alongside LIGO, in August 2017 - the merger of two neutron stars.", 
                       "The Kamioka Gravitational Wave Detector (KAGRA) will be the world's first underground gravitational wave observatory. It is currently under construction in the Kamioka mine, Japan, with the University of Tokyo. \n The detector will utilise cryogenic cooling to reduce the interference of thermal noise in the measuring process. It will be completed towards the end of 2019."])
        t = threading.Thread(target=statusupdate,args=(self,),daemon=True)
        t.start()
  
    def retract(self,presser):
        for child in self.children[0].children:
            if child.pos[1] < 240:
                anim = Animation(x=child.pos[0],y=child.pos[1]-240-child.height,duration=0.5)
                anim.start(child)
            elif child.pos[1] > 240:
                anim=Animation(x=child.pos[0],y=240+child.pos[1]+child.height,duration=0.5)
                anim.start(child)
                
        App.get_running_app().root.transition=FadeTransition(duration=0.3)
        def change(presser):
            App.get_running_app().root.current='statinfo'
            App.get_running_app().root.current_screen.detlist = presser.prop
            App.get_running_app().root.current_screen.bio = presser.bio
        Clock.schedule_once(lambda dt: change(presser),0.5)

class PlotsScreen(Screen):
    imgsources = ListProperty()
    descs = ListProperty()
    
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        t3 = threading.Thread(target=plotupdate,args=(self,),daemon=True)
        t3.start()
        
class StatBio(Screen):
    detlist=ListProperty()
    bio=ObjectProperty()
    def change(obj):    
        App.get_running_app().root.current = 'status'
        App.get_running_app().root.transition=NoTransition()
        for child in App.get_running_app().root.current_screen.children[0].children:
            if child.pos[1] < 240:
                anim = Animation(x=child.pos[0],y=240+child.pos[1]+child.height)
                anim.start(child)
            elif child.pos[1] > 240:
                anim=Animation(x=child.pos[0],y=child.pos[1]-240-child.height)
                anim.start(child)
        App.get_running_app().root.transition=SlideTransition()


class MyApp(App):
    def build_config(self,config):
        config.setdefaults('Section',{'PeriodicBackup':'0'})
    def on_start(self):
        global flag
        global main_flag
        global newevent_flag
        flag = 0
        main_flag=0
        newevent_flag=0
        
    def build(self):
        config = self.config
        now = time.time()
        last_backup =float(config.get('Section','PeriodicBackup'))
        print('It has been '+ str((now - last_backup)/86400) + ' days since the last backup')
        
        if os.path.basename(os.getcwd()) != "event_data":
            dir_to_search = "event_data"
        else:
            dir_to_search=None
        if 'Event Database' not in os.listdir(dir_to_search):
            print('Event file not found.')
            file_presence = 0
        else:
            file_presence = 1

        if now-last_backup > 86400 or file_presence == 0:
            print('Performing Periodic Event Sync. Please be patient - this may take a while...')
            sync_database()
            config.set('Section','PeriodicBackup',now)
            config.write()
            print('Initial Event Sync Complete...')
        else:
            print('Event Sync not required...')
        
        sm = ScreenManager()
        sm.add_widget(MainScreenv2(name='main'))
        sm.add_widget(HistoryScreenv2(name='history'))
        sm.add_widget(StatusScreenv2(name='status'))
        sm.add_widget(PlotsScreen(name='plots'))
        sm.add_widget(StatBio(name='statinfo'))
        
        print('Initialised application...')
        return sm

if __name__ == '__main__':
    MyApp().run()
    main_flag = 1 
    Builder.unload_file("GWalarm.kv")
    if pixels:
        GPIO.cleanup()
    time.sleep(10)
    print('KeyboardInterrupt to close listener...')
    raise KeyboardInterrupt