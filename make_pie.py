# -*- coding: utf-8 -*-
"""
Created on Thu Apr  5 02:08:17 2018

@author: chris
"""

import matplotlib.pyplot as plotter
import json
import requests
data = {}
in_file = False

class ProcessData:
    """
    Class for interpreting and presenting data collected
    
    For dictionary format data:
        "in_file=False"
        
    For data stored in a file:
        "data" and "sincerity_data" should be a path and filename
        "in_file=True
    """
    
    def __init__(self, data,
                 sincerity_data,
                 in_file=False,
                 include_other=True,
                 min_accuracy=99.5,
                 exclude=['busy.org']):
        """
        Initialise new instance of ProcessData class
        """
        
        # Load databases from file
        if in_file == True:
            with open(data) as f:
                self.data = json.loads(f.read())
            with open(sincerity_data) as f:
                self.sincerity_data = json.loads(f.read())
                
        # Data already in dictionary format, no need to load from file
        else:
            self.data = data
            self.sincerity_data = sincerity_data        
        
        # Globalise settings
        self.include_other = include_other
        self.min_accuracy = min_accuracy
        self.exclude = exclude

        
    def make_pie_incoming_value(self):
        """
        Make a pie chart for users with the highest value of incoming votes.
        """

        refined = self._de_res(self.get_incoming_value())
        self._render_pie(refined)
        
    def make_pie_outgoing_quantity(self):
        """
        Make a pie chart for highest quantities of outgoing votes.
        """

        refined = self._de_res(self.get_outgoing(quant=True))
        self._render_pie(refined, marker="")
        
    def make_pie_outgoing_value(self):
        """
        Make a pie chart for highest value of outgoing votes.
        """
        
        refined = self._de_res(self.get_outgoing(val=True))
        self._render_pie(refined)
        
    def get_incoming_value(self):
        """
        Collects all data on accounts which have recieved last minute votes
        and updates the pairings for pie chart creation. Returns dictionary
        version of pairings.
        """
        
        # Create an empty, temporary dictionary
        iv = dict()
        
        # Accumulate and filter all accounts which recieved lm votes and are 
        # not in the exclude list
        for k,v in self.data['recievers'].items():
            if k not in self.exclude:
                # Add to dictionary (rounded to 2 decimal places)
                iv[k] = round(v['total_lme'], 2)
                
        return iv
    
    def get_outgoing(self, val=False, quant=False):
        """
        Collects all data on accounts which have transmitted last minute votes
        and updates parings for pie charts. Optional return of data in
        dictionary form.
        """
        
        # Declare dictionaries to be returned
        ov = dict()
        oq = dict()
        
        for k,v in self.data['voters'].items():
            # Get value and quantity variables from the 'v' dictionary
            value = v['value']
            quantity = v['quantity']
            # Ignore data if user is in the exclusion list
            if k not in self.exclude:
                # Add filtered data into the new dictionaries
                ov[k] = round(value, 2)
                oq[k] = quantity
               
        if val == True:
            if quant == True:
                # Return both dictionaries
                return ov, oq
            # Return just value dictionary
            return ov
        elif quant == True:
            # Return just quantity dictionary
            return oq
        
    def sincerity_lookup(self, username):
        """
        Returns a dictionary containing sincerity bot/human/spammer scores.
        """
        
        # Local database present
        if self.sincerity_data:
            # User is in database, return data
            if username in self.sincerity_data:
                return self.sincerity_data[username]
            
        # Database not loaded in or user not in database
        try:
            # Get data from sincerity site
            r = requests.get(
                    'https://steem-sincerity.dapptools.info'
                    '/s/api/accounts-info/' + username
                    )
            r = r.json()['data'][username]
            scores = {
                    'bot_score':r['classification_bot_score'],
                    'spam_score':r['classification_spammer_score'],
                    'human_score':r['classification_human_score']
                    }
            return scores
        
        # Both online and offline options failed, ask user to check command
        except Exception as e:
            print(e)
            raise LookupError('User not found locally or online. Try '
                              'loading in a sincerity db, checking '
                              'spelling or connecting to the internet.')
    
    def _de_res(self, dictionary):
        """
        De-resolution module, simplifies the dataset based on 'min_accuracy'
        """
        
        # Get the total value of all vals
        total = sum(dictionary.values())
        # Create a temporary tuple and list pairing
        new = {'other':0}
        # Repeat for the length accounts
        for accounts, vals in dictionary.items():
            # If the current value takes up sufficient % of total
            if vals/total >= (100-self.min_accuracy)/100:
                # Filter only applicable pairings to the new list and tuple
                new[accounts] = vals
                
            # If value is less than minimum and user has 'include_other = True'
            elif self.include_other == True:
                # Increase the value of the 'other' segment
                new['other'] += vals
        return new
    
    def _render_pie(self, data, marker="$"):
        """
        Lots of repeated code when making pie charts led to this procedure 
        which essentially renders the pie charts based on data supplied.
        """
        
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
        
    def _dict_to_pairing(self, dictionary):
        """
        Takes a dictionary of account names and associated values and returns
        a list and tuple pair ready for pie rendering.
        """
        
        # Declare new list and tuple pair
        names = tuple()
        vals = list()
        
        # Populate tuple and list pairs
        for k,v in dictionary.items():
            names = names + (k,)
            vals.append(v)
            
        return names, vals