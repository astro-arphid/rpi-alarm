#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul 24 12:21:39 2019

@author: christian
"""

import gcn
from tables import *
import os
from bs4 import BeautifulSoup
import requests
import scipy.constants
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import numpy as np
import time
import threading

class Event(IsDescription):
    GraceID=StringCol(30)
    AlertType=StringCol(30)
    Instruments = StringCol(30)
    FAR = StringCol(30)
    skymap=StringCol(30)
    Group=StringCol(30)
    BNS=StringCol(30)
    NSBH=StringCol(30)
    BBH=StringCol(30)
    Terrestrial = StringCol(30)
    HasNS=StringCol(30)
    HasRemnant=StringCol(30)
    Distance=StringCol(30)
    DetectionTime=StringCol(30)
    UpdateTime=StringCol(30)
    MassGap=StringCol(30)
    Revision=StringCol(30)
# Function to call every time a GCN is received.
# Run only for notices of type
# LVC_PRELIMINARY, LVC_INITIAL, or LVC_UPDATE.
@gcn.handlers.include_notice_types(
    gcn.notice_types.LVC_PRELIMINARY,
    gcn.notice_types.LVC_INITIAL,
    gcn.notice_types.LVC_UPDATE,
    gcn.notice_types.LVC_RETRACTION)

def process_gcn(payload, root):
    if ('Thisisaneventsim').encode() in payload:
        sim = True
    else:
        sim = False
    # Respond only to 'test' events.
    # VERY IMPORTANT! Replace with the following code
    # to respond to only real 'observation' events.
    if root.attrib['role'] != 'observation':
        return
    #acknowledge
    #print('I have received a notice!')

    #ensure correct working directory and open the table
    if os.path.basename(os.getcwd()) != "event_data":
        try:
            os.chdir('./event_data')
        except:
            os.mkdir('./event_data')
            os.chdir('./event_data')

    # Read all of the VOEvent parameters from the "What" section.
    params = {elem.attrib['name']:
              elem.attrib['value']
              for elem in root.iterfind('.//Param')}
    descs = [elem.text for elem in root.iterfind('.//Description')]
    
    if params['AlertType'] != 'Retraction':
        #We must first filter out retractions, as they do not have a listed 
        #group' and will flag an error.
        if params['Group'] != 'CBC':
            print(params['GraceID']+' is of type ' + params['Group']+'. Ignoring...')
            return
    
    while True:
        try:
            h5file = open_file("Event Database",mode="a",title="eventinfo")
            break
        except:
            time.sleep(0.5)
    try:
        h5file.create_group("/",'events')
    except NodeError:
        pass
    
    widgetids= [node.name for node in h5file.list_nodes("/events")]

    if sim == False:
        try:
            table = h5file.create_table(h5file.root.events,params['GraceID'],Event,'CBC event')
        except:
            table=h5file.get_node("/events",params['GraceID'])
    else:
        try:
            table = h5file.create_table(h5file.root.events,'EventSimulation',Event,'Simulation')
        except:
            table=h5file.get_node("/events",'EventSimulation')
            
    #Check if the current revision of this event exists - if it does, nothing else needs to be done!  
    if params['AlertType'] == 'Retraction':
        #Remove the event info if a retraction is issued - we don't care anymore
        print(params['GraceID'],'retracted.')
        try:
            h5file.remove_node("/events",params['GraceID'])
        except:
            pass
        h5file.close()
        return
    
    if params['GraceID'] in widgetids and sim == False:
        if params['Pkt_Ser_Num'] == table[-1]['Revision'].decode():
            h5file.close()
            print(params['GraceID'] +' already up to date.')
            return
        else:
            print(params['GraceID'] +' updating...')
    elif sim == True:
        print('Simulation processing...')
    else:
        print(params['GraceID'] +' event adding...')
    h5file.close()
    
    lookoutfor = ['BBH','BNS','NSBH','MassGap','Terrestrial']
    lookoutfor2=['HasNS','HasRemnant']
    order = []
    order2=[]
    vals = []
    vals2=[]
    descriptions={}
    i=0

    det_time = root.find('.//ISOTime')
    det_text = det_time.text
    [one,two] = det_text.split('T')
    one=one.replace(':','-')
    two = two.split('.')[0]
    det_formtime = one+' at '+two

    
    upt_time = root.find('.//Date')
    upt_text = upt_time.text
    [one1,two1] = upt_text.split('T')
    one1=one1.replace(':','-')
    two1=two1.split('.')[0]
    upt_formtime = one1+' at '+two1

    #print(descriptions)
    #prepare path for localization skymap, then download and produce the map in png format
    filesurl = "https://gracedb.ligo.org/superevents/"+params['GraceID']+"/files/"
    skymap = params['GraceID']+'.png'
    r =requests.get(filesurl)
    soup = BeautifulSoup(r.text,"lxml")

    all_files = [a['href'] for a in soup.find_all("a")]
    imglinks = []
    htmllinks=[]

    if any('LALInferenceOffline.png' in s for s in all_files):
        imglinks = [s for s in all_files if 'LALInferenceOffline.png' in s]
    else:
        imglinks = [s for s in all_files if 'bayestar.png' in s]
    imgfile = imglinks[-1]
    imgfilepath = "https://gracedb.ligo.org"+imgfile

    def download(imgfilepath,skymap):
        os.system("curl --silent -0 "+imgfilepath + '> ' + './'+skymap)
        img = plt.imread(skymap)
        plt.imsave(skymap,img[100:475,50:750,:])
    t=threading.Thread(target=download,args=(imgfilepath,skymap))
    t.start()
    if any('bayestar.html' in s for s in all_files):
        htmllinks = [s for s in all_files if 'bayestar.html' in s]
    htmlfile = htmllinks[-1]
    htmlfilepath = "https://gracedb.ligo.org"+htmlfile
    r2 = requests.get(htmlfilepath)
    soup2 = BeautifulSoup(r2.text,"lxml")
    for col in soup2.tbody.find_all("tr"):
        if 'DISTMEAN' in str(col):
            dist = col.text.split('\n')[2]
            dist = str("{0:.0f}".format(float(dist)))
        elif 'DISTSTD' in str(col):
            diststd = col.text.split('\n')[2]
            diststd= str("{0:.0f}".format(float(diststd)))
    finaldist = dist + ' +- '+diststd + ' Mpc'

    while True:
        try: 
            h5file = open_file("Event Database",mode="a",title="eventinfo")
            break
        except:
            time.sleep(0.5)
    try:
        h5file.create_group("/",'events')
    except NodeError:
        pass

    widgetids= [node.name for node in h5file.list_nodes("/events")]

    if sim == False:
        try:
            table = h5file.create_table(h5file.root.events,params['GraceID'],Event,'CBC event')
        except:
            table=h5file.get_node("/events",params['GraceID'])
    else: 
        try:
            table = h5file.create_table(h5file.root.events,'EventSimulation',Event,'Simulation')
        except:
            table=h5file.get_node("/events",'EventSimulation')
    det_event = table.row
    #    
    for key, value in params.items():
        if key == 'FAR':
            per_yr = float(value)*scipy.constants.year
            if per_yr <= 1:
                oneinyr = 1/per_yr
            else:
                oneinyr = per_yr
            if len(str(oneinyr).split('.')[0]) >= 5 or 'e' in str(oneinyr):
                val = "One every "+str("{0:.2e}".format(oneinyr))+" yrs"
            else:
                val = "One every "+str("{0:.3f}".format(oneinyr))+" yrs"
            det_event[key] = val
            descriptions[key]=descs[i]
        if key == 'Pkt_Ser_Num':
            key = 'Revision'
            det_event[key] = value
            descriptions[key] = descs[i]
        elif key in lookoutfor:
            order.append(key)
            vals.append(float(value))
            det_event[key]=str("{0:.3f}".format(float(value)*100))+'%'
            descriptions[key]=descs[i]
        elif key in lookoutfor2:
            order2.append(key)
            vals2.append(float(value))
            if float(value) < 0.001:
                det_event[key] = '< 0.1%'
            else:
                det_event[key]=str("{0:.2f}".format(float(value)*100))+'%'
            descriptions[key]=descs[i]
        elif key == 'GraceID':
            if sim:
                det_event[key] = 'EventSimulation'
            else:
                det_event[key] = value
                descriptions[key]=descs[i]
        else:
            try:
                det_event[key] = value
                descriptions[key]=descs[i]
            except:
                i+=1
                continue
        i+=1


    det_event['skymap'] = skymap
    det_event['Distance'] = finaldist
    det_event['DetectionTime']=det_formtime
    det_event['UpdateTime'] = upt_formtime
    det_event.append()
    table.flush()
    h5file.close()
    '''PLOTTING'''
    if sim:  
        pass
    else:
        #sort the pie values for correct colors
        sort_ints = []
        for cat in order:
            for i,item in enumerate(lookoutfor):
                if cat in item:
                    sort_ints.append(i)
        sorted_vals = [x for _,x in sorted(zip(sort_ints,vals))]
        
        #save the pie of possibilities
        specindex = np.argmax(vals)
        fig1, ax1 = plt.subplots(figsize=(4,4))
        
        colors= [[202/255,214/255,235/255,1],[179/255,242/255,183/255,1],
                 [238/255,242/255,179/255,1],[231/255,179/255,242/255,1],
                 [242/255,179/255,179/255,1]]

        
        ax1.pie(sorted_vals,labels=None,wedgeprops=dict(width=0.5),colors=colors)
        ax1.axis('equal')
    #    plt.text(0,0.1,'Type:',fontsize=20,transform=ax1.transAxes)
    #    plt.text(0,0,order[specindex],fontsize=20,transform=ax1.transAxes)
        plt.text(0.365,0.55,'Event Type:',transform=ax1.transAxes,fontsize=16*0.8)
        if order[specindex] == 'NSBH':
            plt.text(0.395,0.42,order[specindex],fontsize=26*0.8,transform=ax1.transAxes)
        elif order[specindex] == 'Terrestrial':
            plt.text(0.335,0.44,order[specindex],fontsize=22*0.8,transform=ax1.transAxes)
        elif order[specindex] == 'MassGap':
            plt.text(0.335,0.44,order[specindex],fontsize=26*0.8,transform=ax1.transAxes)
        else:
            plt.text(0.42,0.42,order[specindex],fontsize=28*0.8,transform=ax1.transAxes)
    
        plt.text(0,0.05,'Event Type',fontsize=13*0.8,transform=ax1.transAxes)
        plt.text(0,0.01,'Probability Distribution',fontsize=13*0.8,transform=ax1.transAxes)
    
        plt.tight_layout()
        plt.savefig(params['GraceID']+'_pie.png')
        plt.close(fig1)
    t.join()

#gcn.listen(host="209.208.78.170",handler=process_gcn)
#
#
#testing
#os.chdir('./event_data')
#import lxml
#payload = open('S190828l-1-Preliminary.xml', 'rb').read()
#root = lxml.etree.fromstring(payload)
#process_gcn(payload, root)