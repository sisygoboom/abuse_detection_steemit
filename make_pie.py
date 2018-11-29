# -*- coding: utf-8 -*-
"""
Created on Thu Apr  5 02:08:17 2018

@author: chris
"""

import matplotlib.pyplot as plotter
import json

"""
Class for interpreting and presenting data collected

For dictionary format data:
    "in_file=False"
    
For data stored in a file:
    "data" should be a raw string path and filename
    "in_file=True
"""
class ProcessData:
    
    """
    Initialise new instance of ProcessData class
    
    @param data
    @param in_file
    @param include_other
    @param min_accuracy
    @param exclude
    """
    def __init__(self,
                 data,
                 in_file=False,
                 include_other=True,
                 min_accuracy=99,
                 exclude=['busy.org']):
        # initialise variables
        self.include_other = include_other
        self.min_accuracy = min_accuracy
        self.exclude = exclude
        
        # Load databases from file
        if in_file == True:
            with open(data) as f:
                self.data = json.loads(f.read())
                
        # Data already in dictionary format, no need to load from file
        else:
            self.data = data   
        
    """
    Make a pie chart for users with the highest value of incoming votes.
    """
    def make_pie_incoming_value(self):
        refined = self._de_res(self.get_incoming(val=True))
        self._render_pie(refined)
    
    """
    Make a pie chart for users with the highes quantity of incoming votes
    """
    def make_pie_incoming_quantity(self):
        refined = self._de_res(self.get_incoming(quant=True))
        self._render_pie(refined, marker="")
    
    """
    Make a pie chart for highest quantities of outgoing votes.
    """
    def make_pie_outgoing_quantity(self):
        refined = self._de_res(self.get_outgoing(quant=True))
        self._render_pie(refined, marker="")
        
    """
    Make a pie chart for highest value of outgoing votes.
    """
    def make_pie_outgoing_value(self):
        refined = self._de_res(self.get_outgoing(val=True))
        self._render_pie(refined)
    
    """
    Collects all data on accounts which have recieved last minute votes
    and updates the pairings for pie chart creation. Returns dictionary
    version of pairings.
    
    @param val
    @param quant
    
    @return incoming_value, incoming_votes
    @return incoming_value
    @return incoming_votes
    """
    def get_incoming(self, val=False, quant=False):
        # Create an empty, temporary dictionary
        incoming_value = dict()
        incoming_votes = dict()
        
        # Accumulate and filter all accounts which recieved lm votes and are 
        # not in the exclude list
        for k,v in self.data['recievers'].items():
            if k not in self.exclude:
                # Add to dictionaries
                if val:
                    incoming_value[k] = round(v['total_lme'], 2)
                if quant:
                    incoming_votes[k] = v['total_votes']
                    
                
        if quant and val:
            return incoming_value, incoming_votes
        elif val:
            return incoming_value
        elif quant:
            return incoming_votes
    
    """
    Collects all data on accounts which have transmitted last minute votes
    and updates parings for pie charts. Optional return of data in
    dictionary form.
    
    @param val
    @param quant
    
    @return outgoing_value, outgoing_quantity
    @return outgoing_value
    @return outgoing_quantity
    """
    def get_outgoing(self, val=False, quant=False):
        # Declare dictionaries to be returned
        outgoing_value = dict()
        outgoing_quantity = dict()
        
        for k,v in self.data['voters'].items():
            # Get value and quantity variables from the 'v' dictionary
            value = v['value']
            quantity = v['quantity']
            # Ignore data if user is in the exclusion list
            if k not in self.exclude:
                # Add filtered data into the new dictionaries
                outgoing_value[k] = round(value, 2)
                outgoing_quantity[k] = quantity
               
        if val == True:
            if quant == True:
                # Return both dictionaries
                return outgoing_value, outgoing_quantity
            # Return just value dictionary
            return outgoing_value
        elif quant == True:
            # Return just quantity dictionary
            return outgoing_quantity
    
    """
    De-resolution module, simplifies the dataset based on 'min_accuracy'
    
    @param dictionary
    
    @return new_dictionary
    """
    def _de_res(self, dictionary):
        # Get the total value of all vals
        total = sum(dictionary.values())
        # Create a temporary tuple and list pairing
        new_dictionary = {'other':0}
                    
        # Repeat for every account
        for accounts, vals in dictionary.items():
            # If the current value takes up sufficient % of total
            if vals/total >= (100-self.min_accuracy)/100:
                # Filter only applicable pairings to the new list and tuple
                new_dictionary[accounts] = vals
                
            # If value is less than minimum and user has 'include_other = True'
            elif self.include_other == True:
                # Increase the value of the 'other' segment
                new_dictionary['other'] += vals
                
        return new_dictionary
    
    """
    Lots of repeated code when making pie charts led to this procedure 
    which essentially renders the pie charts based on data supplied.
    
    @param data
    @param marker
    """
    def _render_pie(self, data, marker="$"):
        # Split the dictionary into a list and tuple pair
        n, v = self._dict_to_pairing(data)
        
        # Initialise the pie chart
        figureObject, axesObject = plotter.subplots()
        # Define the settings for the pie chart
        axesObject.pie(v,labels=n,autopct='%1.2f',startangle=90)
        # Render the chart for viewing by the user
        plotter.show()
        
        # Print the chart information below the pie for close anlysys by user
        for i in range(len(n)):
            print(n[i] + " = " + marker + str(round(v[i],2)))
    
    """
    Takes a dictionary of account names and associated values and returns
    a list and tuple pair ready for pie rendering.
    
    @param dictionary
    
    @return names
    @return vals
    """
    def _dict_to_pairing(self, dictionary):
        # Declare new list and tuple pair
        names = tuple()
        vals = list()
        
        # Populate tuple and list pairs
        for k,v in dictionary.items():
            names = names + (k,)
            vals.append(v)
            
        return names, vals