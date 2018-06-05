# -*- coding: utf-8 -*-
"""
Created on Thu Apr  5 02:08:17 2018

@author: chris
"""

import matplotlib.pyplot as plotter
import json
from pathlib import Path

# Load database
with open("abuse_log.json","r") as f:
    data = json.loads(f.read())

# Declare tuple and list pairings with the 'other' categories as the first entries
names = ('other',)
values = [0]
outgoing_names = ('other',)
outgoing_quant = [0]
outgoing_value = [0]

#### USER CUSTOMISEABLE DATA ####
include_other = True
min_accuracy = 99.5
exclude = ['busy.org']
#################################


"""
De-resolution module, simplifies the dataset based on 'min_accuracy'
"""
def de_res(accounts, vals):
    # Get the total value of all vals
    total = sum(vals)
    # Create a temporary tuple and list pairing
    acc_new = ('other',)
    val_new = [0]
    # Repeat for the length accounts
    for i in range(len(accounts)):
        # If the current value takes up sufficient % of total
        if vals[i]/total >= (100-min_accuracy)/100:
            # Filter only applicable pairings to the new list and tuple
            acc_new = acc_new + (accounts[i],)
            val_new.append(vals[i])
        # If the value is less than minimum and user has 'include_other = True'
        elif include_other == True:
            # Increase the value of the 'other' instead of creating a new entry
            val_new[0] += vals[i]
    
    return acc_new, val_new

"""
Lots of repeated code when making pie charts led to this procedure
"""
def render_pie(n, v, marker="$"):
    # Initialise the pie chart
    figureObject, axesObject = plotter.subplots()
    # Define the settings for the pie chart
    axesObject.pie(v,labels=n,autopct='%1.2f',startangle=90)
    # Render the chart for viewing by the user
    plotter.show()
    # Print the chart information in detail for close anlysys by user
    for i in range(len(n)):
        print(n[i] + " = "+ marker + str(round(v[i],2)))

"""
Collects all data on accounts which have recieved votes
"""  
for k,v in data['recievers'].items():
    # Ignore data if user is in the exclusion list
    if k not in exclude:
        # Input the username and total earnings into the tuple/list pair
        names = names + (k,)
        values.append(v['total_lme'])
        # Print username and total last minute earnings
        print(k + " = $" + str(round(v['total_lme'],2)))

print('\n')

"""
Collects all data on accounts which have transmitted last minute votes
"""
for k,v in data['voters'].items():
    # Get value and quantity variables from the 'v' dictionary
    value = v['value']
    quantity = v['quantity']
    # Ignore data if user is in the exclusion list
    if k not in exclude:
        # Input data int list and paired tuples
        outgoing_names = outgoing_names + (k,)
        outgoing_quant.append(quantity)
        outgoing_value.append(value)

"""
Reduce the resolution of the datasets so as to not congest the pie chart
"""
# Incoming value
names, values = de_res(names, values)
# Outgoing quantity         
outgoing_names_quant, outgoing_quant = de_res(outgoing_names, outgoing_quant)
# Outgoing value
outgoing_names_value, outgoing_value = de_res(outgoing_names, outgoing_value)

"""
Renders the pie charts with a title above and detailed information below
"""
print("\nMost upvoted accounts by value")
render_pie(names, values)

print("\nAccounts with the most outgoing votes")
render_pie(outgoing_names_quant, outgoing_quant, marker="")

print("\nAccounts with the highest value of outgoing votes")
render_pie(outgoing_names_value, outgoing_value)

"""
Allows user to get sincerity stats on specific users.
"""
while True:
    # Get username to look up
    username = input("Enter username for classification \
                     info or type '$exit' to quit: ")
    
    # Exit
    if username == '$exit':
        break

    # Load sincerity db
    if Path('sincerity_data.json').is_file():
        i = open('sincerity_data.json','r').read()
        data = json.loads(i)
    else:
        print("No data file")
    
    # Display results
    if username in data:
        print(data[username])
    else:
        print("User not found")