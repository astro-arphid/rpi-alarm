#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 13 10:19:09 2019

@author: christian
"""

def statusdetect():
    from bs4 import BeautifulSoup 
    import requests 
    url = "https://ldas-jobs.ligo.caltech.edu/~gwistat/gwistat/gwistat.html"
    try:
        r =requests.get(url) 
    except:
        print ('ERROR: Issues requesting website:  ' + url + '\n')
        r=''
        pass
    if hasattr(r, 'text'):
        soup = BeautifulSoup(r.text,"lxml")
    else:
        soup = BeautifulSoup(r,"lxml")
#    if '404' in str(soup):
#        print('404')
    names = ['GEO 600','LIGO Hanford','LIGO Livingston','Virgo','KAGRA']
    detrows = []
    to_add=[]
    i=0
    for row in soup.find_all('td'):
        if i > 0:
            to_add.append(row.text)
            i-=1
            if i == 0:
                detrows.append(to_add)
                to_add=[] 
        if row.text in names:
            i = 4
            to_add.append(row.text)
            i-=1
    statuses = []
    for row in detrows:
        if row[2] == 'Timestamp error':
            row[3] = 'N/A'
            statuses.append(1)
        elif row[2] == 'Future addition':
            row[3] = 'N/A'
            statuses.append(3)
        elif row[2] == 'Commissioning':
            row[2] = 'Commission'
            statuses.append(1)
        elif row[2] == 'Observing'or row[2] == 'Science':
            statuses.append(2)
        elif row[2] == 'Down' or row[2] == 'Info too old' or row[2] == 'Unlocked':
            statuses.append(0)
        else:
            statuses.append(1)
    export=[]
    for i,row in enumerate(detrows):
        if statuses[i] == 0:
            #red 
            toput = [236/255,23/255,23/255,0.7]
        elif statuses[i] == 1:
            #orange
            toput=[228/255,119/255,10/255,0.7]
        elif statuses[i] == 2:
             #green
             toput=[132/255,241/255,70/255,0.7]
        elif statuses[i] == 3:
            #yellow
            toput=[229/255,237/255,78/255,0.7]
        temp=[row[0],row[2],row[3],toput]
        export.append(temp)
    try:
        export[0],export[2] = export[2],export[0]
    except:
        export = []
        statuses=[]
        for i in range(0,5):
            export.append(['Website','is','down.',[236/255,23/255,23/255,0.7]])
            statuses.append(0)
            
    return export,statuses, names