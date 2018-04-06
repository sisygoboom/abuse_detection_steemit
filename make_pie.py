# -*- coding: utf-8 -*-
"""
Created on Thu Apr  5 02:08:17 2018

@author: chris
"""

import matplotlib.pyplot as plotter
import json

with open("abuse_log","r") as f:
    data = json.loads(f.read())

names = ('other',)
values = [0]
outgoing_names = ('other',)
outgoing_quant = [0]
include_other = False
  
for k,v in data['recievers'].items():
    if v['total_lme'] > 5:
        names = names + (k,)
        values.append(v['total_lme'])
        print(k + " = $" + str(round(v['total_lme'],2)))
    elif include_other == True:
        values[0] += v['total_lme']
        
print('\n')

for k,v in data['voters'].items():
    if v > 5:
        outgoing_names = outgoing_names + (k,)
        outgoing_quant.append(v)
        print(k + " = " + str(v))
    elif include_other == True:
        outgoing_quant[0] += v
    
print("Most upvoted accounts by value (total of above $5)")
figureObject, axesObject = plotter.subplots()
axesObject.pie(values,labels=names,autopct='%1.2f',startangle=90)

print("Accounts with the most outgoing votes")
figureObject, axesObject = plotter.subplots()
axesObject.pie(outgoing_quant,labels=outgoing_names,autopct='%1.2f',startangle=90)