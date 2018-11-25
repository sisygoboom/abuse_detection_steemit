# -*- coding: utf-8 -*-
"""
Created on Wed Nov 14 16:26:35 2018

@author: chris
"""

import tkinter as tk
import json
import os
import operator

class SlveDat(tk.Frame):
    """
    Initialise the gui class.
    """
    def __init__(self, master, path=None):
        tk.Frame.__init__(self, master)
        self.pack(side='top', fill=tk.BOTH, expand=1)
        
        # Declare tk variables
        self.abuse_category = tk.StringVar()
        self.ordering = tk.StringVar()
        # Set tk variables
        self.abuse_category.set('Voters')
        self.ordering.set('Value')
        
        # Create frames
        self.viewer_frame = tk.Frame(self, width=30)
        self.descrp_frame = tk.Frame(self, width=15)
        self.values_frame = tk.Frame(self, width=15)
        self.filter_frame = tk.Frame(self, width=30)
        
        # Create widgets
        # --- listbox
        self.user_browser = tk.Listbox(self.viewer_frame, width=30, height=50)
        self.scrollbar = tk.Scrollbar(self.viewer_frame)
        # --- static labels
        self.name_label = tk.Label(self.descrp_frame, text='Username:')
        self.total_rcvd_label = tk.Label(self.descrp_frame, text='Total $:')
        self.total_lmv_label = tk.Label(self.descrp_frame, text='Total #:')
        # --- variable labels
        self.user_name_label = tk.Entry(self.values_frame, width=20)
        self.rcvd_label = tk.Entry(self.values_frame, width=20)
        self.lmv_label = tk.Entry(self.values_frame, width=20)
        # --- searching options
        self.perspective_option = tk.OptionMenu(
                self.filter_frame,
                self.abuse_category,
                'Voters',
                'Recievers',
                command=self.populate
                )
        self.order_option = tk.OptionMenu(
                self.filter_frame,
                self.ordering,
                'Value',
                'Quantity',
                'Alphabetic',
                command=self.populate
                )
        self.namefilter_entry = tk.Entry(self.filter_frame)
        
        # Widget settings
        self.user_browser.bind('<<ListboxSelect>>', self.selection)
        self.user_browser.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.user_browser.yview)
        self.namefilter_entry.bind('<KeyRelease>', self.populate)
        
        # Declare frame and widet groupings
        frames = [
                self.viewer_frame,
                self.descrp_frame,
                self.values_frame,
                self.filter_frame
                ]
        self.entries = [
                self.user_name_label,
                self.rcvd_label,
                self.lmv_label
                ]
        
        # Pack the frames
        for i in frames:
            i.pack(side='left', fill=tk.Y, expand=1)
        
        # Pack the widgets onto the frame
        # --- listbox
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.user_browser.pack()
        # --- static labels
        self.name_label.pack(side='top', anchor='w')
        self.total_rcvd_label.pack(side='top', anchor='w')
        self.total_lmv_label.pack(side='top', anchor='w')
        # --- variable labels
        self.user_name_label.pack(side='top')
        self.rcvd_label.pack(side='top')
        self.lmv_label.pack(side='top')
        # --- searching options
        self.perspective_option.grid(sticky='news')
        self.order_option.grid(sticky='news')
        self.namefilter_entry.grid()
        
        # Startup functions
        self.db_loader(path=path)
        
    """
    Populates the listbox with all users in the selected dataset (voters/
    recievers), in order (alphabetical/$/#), with users filtered out based on
    user search. This is called whenever there is a keypress in the
    namefilter_entry widget
    
    @param event
    """
    def populate(self, event=None):
        # Get filtration settings
        print(event)
        dataset = self.get_dataset()
        order = self.ordering.get()
        filtertext = self.namefilter_entry.get()
        
        # Create a temporary dictionary so entries can be ordered after filters
        temp_dict = dict()
        
        # Loops through every user in the selected dataset
        for k, v in self.data[dataset].items():
            # Check if the username cointains the filtertext
            if filtertext.lower() in k:
                # TODO make both datasets use the same keys for $ and #
                # Add correct value to temporary list
                if dataset == 'voters':
                    if order == 'Value':
                        temp_dict[k] = v['value']
                    else:
                        temp_dict[k] = v['quantity']
                
                if dataset == 'recievers':
                    if order == 'Value':
                        temp_dict[k] = v['total_lme']
                    else:
                        temp_dict[k] = v['total_votes']
        
        # Order the dictionary
        if order == 'Alphabetic':
            temp_dict = sorted(temp_dict.items(), key=operator.itemgetter(0))
        else:
            temp_dict = sorted(temp_dict.items(), key=operator.itemgetter(1))
        
        # Clear listbox
        self.user_browser.delete(0, tk.END)
        # Fill listbox with filtered, ordered users
        for user, values in temp_dict:
            self.user_browser.insert(0, user)
    
    """
    Loads the databases. If no path is supplied, it will use the working 
    directory. Is called at instance initialisation.
    
    @param path
    """
    def db_loader(self, path=None):
        # If no path is specified, get current path
        if not path:
            path = os.getcwd()
        
        try:
            # Load data from databases
            i = open(path + r'\sincerity_data.json','r').read()
            x = open(path + r'\abuse_log.json', 'r').read()
            # Load data into dictionaries
            self.sincerity_data = json.loads(i)
            self.data = json.loads(x)
            
            # Update the listbox
            self.populate()
            
        except Exception as e:
            raise e
            
    """
    This procedure is called whenever a user makes a selection in the 
    user_browser widget. It updates the Entry widgets to contain information 
    relating to the selected user.
    
    @param event
    """
    def selection(self, event=None):
        # Get the selected uername
        index = self.user_browser.curselection()
        user = self.user_browser.get(index[0])
        # Get the dataset to look in
        dataset = self.get_dataset()
        
        # TODO make both datasets use the same keys for $ and #
        # Find the value and quantity of votes cast/recieved by user
        if dataset == 'voters':
            total_lme = round(self.data[dataset][user]['value'], 3)
            total_lmv = self.data[dataset][user]['quantity']
        
        if dataset == 'recievers':
            total_lme = round(self.data[dataset][user]['total_lme'], 3)
            total_lmv = self.data[dataset][user]['total_votes']
        
        # Enable widget editing
        for widget in self.entries:
            widget.config(state='normal')
            
        # Clear entries
        self.user_name_label.delete(0, tk.END)
        self.rcvd_label.delete(0, tk.END)
        self.lmv_label.delete(0, tk.END)
        
        # Insert new entries
        self.user_name_label.insert(0, user)
        self.rcvd_label.insert(0, total_lme)
        self.lmv_label.insert(0, total_lmv)
        
        # Disable widget editing
        for widget in self.entries:
            widget.config(state='readonly')
        
        print(user)
        
    """
    Get the dataset to use (voter/recievers) and make it lowercase before 
    returning.
    
    @return dataset
    """
    def get_dataset(self):
        dataset = self.abuse_category.get()
        dataset = dataset.lower()
        return dataset
        
if __name__ == '__main__':
    root = tk.Tk()
    root.title('SLVE - Data Analysis Tool')
    root.geometry('520x200')
    slve_dat = SlveDat(root)
    root.mainloop()