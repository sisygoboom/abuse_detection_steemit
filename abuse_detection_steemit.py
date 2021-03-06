from beem.instance import set_shared_steem_instance
from beem.blockchain import Blockchain
from beem.amount import Amount
from beem.comment import Comment
from beem.account import Account
from beem import Steem
from datetime import timedelta
from make_pie import ProcessData
from pathlib import Path
from time import sleep
from threading import Thread
import json, os

"""
The abuse detection library gives the user the ability to collect, store
and live view potentially mallicious last minute upvotes.
"""
class AbuseDetection:
    
    """
    Initialise class.
    
    @param min_usd_reward       minimum vote value for vote to be considered
                                abuse, defaults to 0
    @param max_time_hours       time in hours till cashout for a vote to be 
                                considered abuse, defaults to 24 hours
    @param containing_folder    location of .json DBs, defaults to current dir
                                remember to enter raw text for directories
                                e.g. r'C:/users/sisygoboom'
    """
    def __init__(
            self,
            min_usd_reward=0,
            max_time_hours=36,
            containing_folder=None,
            data=None
            ):
        # initialise variables
        self.min_usd_reward = min_usd_reward
        self.max_time_hours = max_time_hours
        self.containing_folder = containing_folder
        self.running = False
        
        # declare nodes
        self.nodes = [
                'https://api.steemit.com',
                'https://rpc.buildteam.io',
                'https://api.steem.house',
                'https://steemd.steemitdev.com',
                'https://steemd.steemitstage.com',
                'https://steemd.steemgigs.org'
                ]
        
        # create steem instances
        self.s = Steem(self.nodes)
        self.bchn = Blockchain(self.s)
        set_shared_steem_instance(self.s)
        
        if not containing_folder:
            self.containing_folder = os.getcwd()
        if not self.containing_folder.endswith('/'):
            self.containing_folder += '/'
        
        if data:
            self.data = data
        else:
            # attempt to load databases
            try:
                self.data = self.db_loader(
                        self.containing_folder + 'abuse_log.json'
                        )
            
            # create new dictionaries in absence of existing databases
            except:
                self.data = {'voters':{},"recievers":{}}
                self.save()
    
    """
    Stream the steem blockchain and sends every vote transaction off to be
    checked. Comes with built in exception handling.
    """    
    def _stream(self):        
        # Safetyloop
        while True:
            try:
                # Blockstream (Mainloop) - streams all votes on the blockchain
                for i in self.bchn.stream(opNames=['vote']):
                    # Check vote for eligibility
                    self.info_digger(i)
                    
            except Exception as e:
                print(e)
                # Switch nodes if stream breaks
                self.nodes = self.nodes[1:] + self.nodes[:1]
                print("============ node unavaliable, switching ============")
                sleep(1)
    
    """
    Starts a thread of the stream procedure so that other functions can be 
    called while it is running
    """
    def stream(self):
        if not self.running:
            self.stream_thread = Thread(target=self._stream)
            self.stream_thread.start()
            self.running = True
    
    """
    Check file existance, loads to dictionary if true, use backup if false.
    
    @param filepath
    
    @return data
    """
    def db_loader(self, filepath):
        if Path(filepath).is_file():
            i = open(filepath,"r").read()
            data = json.loads(i)
            return data
        raise FileNotFoundError('Directory does not exist.')
    
    """
    Saves data to databases
    """
    def save(self):
        # Save the data to the files
        for k,v in {
                self.containing_folder
                + 'abuse_log.json':self.data
                }.items():
            with open(k, "w") as file:
                file.write(json.dumps(v))
                if not file.closed: file.close()

    """
    Main procedure, every vote we stream is sent here to be analysed, can be 
    used to analyse individual operations as well
    
    @param operation    the blockchain operation object to be analyed
    """
    def info_digger(self, operation):
        # get operation details
        self.author = operation['author']
        self.permlink = operation['permlink']
        self.voter = operation['voter']
        
        # validate the opeation and get usd value of vote
        usd_reward = self._check(operation)
        
        # if operation validated, add the operation details to the databases
        if usd_reward != False:
            self._update_db(usd_reward)
            self.save()
            
    """
    Creates an instance of ProcessData from make_pie.py which allows you to
    create pie charts all through the same AbuseDetection instance. This allows
    for the data to be passed easily and saves the user from finding and
    entering long directories.
    
    @param include_other
    @param min_accuracy
    @param exclude
    
    @return mp
    """
    def piecharts(self,
                  include_other=True,
                  min_accuracy=99,
                  exclude=['busy.org']):
        d = self.data
        mp = ProcessData(data=d,
                         include_other=include_other,
                         min_accuracy=min_accuracy,
                         exclude=exclude)
        return mp
        
    """
    Starts the pocess of validating an operation
    
    @param operation
    
    @return usd_reward  returns either boolean False (invalid op) or float 
                        (value of vote)
    """
    def _check(self, operation):
        usd_reward = self._age_check(operation)
        return usd_reward
    
    """
    Checks to make sure the post voted on is old enough to be considered abuse
    
    @param operation
    
    @return usd_reward  returns either boolean False (invalid op) or float 
                        (value of vote)
    """
    def _age_check(self, operation):
        # Get preliminary information on the post: author and permlink
        
        # Get time until cashout
        creation = Comment(self.author + "/" + self.permlink).time_elapsed()
        week = timedelta(days=7)
        cashout = week - creation
    
        # Calculate difference in hours
        hours = cashout.total_seconds()/3600
        
        # If the difference is below max accepted hours, continue
        if hours < self.max_time_hours and hours > 0:
            return self._vest_check(operation)
        else:
            return False
        
    """
    Work out how many vests the vote was worth, return flase if value is
    negative
    
    @param operation
    
    @return usd_reward  returns either boolean False (invalid op) or float 
                        (value of vote)
    """
    def _vest_check(self, operation):
        # Calculate the number of vests committed by the voter
        
        # Get weight as a fraction
        weight = operation['weight']*0.0001
        voter_account = Account(self.voter)
        
        # Tally vests
        vests = float(voter_account['vesting_shares'].amount)
        vests -= float(voter_account['delegated_vesting_shares'].amount)
        vests += float(voter_account['received_vesting_shares'].amount)
        
        # Vests if upvote was 100%
        vests *= 1000000
        vests *= 0.02
        
        # Multiply by weight (fraction)
        vests *= weight
        
        # Ignore downvotes
        if vests > 0:
            return self._usd_check(vests)
        else:
            return False
        
    """
    Work out how much the vote was worth in USD
    
    @param vests
    
    @return usd_reward  returns either boolean False (invalid op) or float 
                        (value of vote)
    """
    def _usd_check(self, vests):
        # Calculate how much steem that vote has earned the author
        reward_fund = self.s.get_reward_funds('post')
        fund_vests = float(reward_fund.get('recent_claims'))
        fund_balance = Amount(reward_fund.get('reward_balance')).amount
        fund_percent = vests/fund_vests
        to_steem = fund_percent * fund_balance
        
        # Convert that steem to usd using internal median price
        price = self.s.get_current_median_history()
        quote = Amount(price["quote"])
        base = Amount(price["base"])
        conversion_rate = base.amount / quote.amount
        usd_reward = float(conversion_rate * to_steem)
        
        # Continue if usd_reward is above minimum requirements
        if usd_reward > self.min_usd_reward:
            return usd_reward
        else:
            return False
    
    """
    Updates the total revenue from last day votes for the author as well as
    value given out by voters, as well as quantities of last minute votes, also
    updates stats for individual posts for further data mining
    
    @param usd_reward
    @param voter
    @param author
    @param permlink
    """
    def _update_db(self, usd_reward):
        # initialise variables
        voter = self.voter
        author = self.author
        permlink = self.permlink
        voters = self.data['voters']
        recievers = self.data['recievers']
        
        print('$' + str(round(usd_reward,3)))
        print('Author: ' + author)
        print('Voter: ' + voter)
        print("https://steemit.com/@%s/%s\n" % (author, permlink))
        
        # update voter records
        if voter in voters:
            voters[voter]['quantity'] += 1
            voters[voter]['value'] += usd_reward
        # create a new entry for unknown user
        else:
            voters[voter] = dict()
            voters[voter]['quantity'] = 1
            voters[voter]['value'] = usd_reward        
        
        # update reciever records
        if author in recievers:
            # get data for current author
            recieving_author = recievers[author]
            
            # specific post is already in database
            if permlink in recieving_author:
                # Get data for specific post
                recieving_link = recieving_author[permlink]
                # Update /create post reward
                recieving_link['bal'] += usd_reward
                
            # New permlink, but author already in database
            else:
                # Create new dictionary for permlink
                recieving_author[permlink] = dict()
                recieving_link = recieving_author[permlink]
                #Populate dictionary with base information
                recieving_link['bal'] = usd_reward
                recieving_link['voters'] = list()
            
            # Update total last minute earnings for author
            recieving_author['value'] += usd_reward
            recieving_author['quantity'] += 1
            # Add new voter to list
            recieving_link['voters'].append(voter)
        
        else:
            # Create dictionary for new author
            recievers[author] = dict()
            recieving_author = recievers[author]
            # Populate with necessary information
            recieving_author['value'] = usd_reward
            recieving_author['quantity'] = 1
            recieving_author[permlink] = dict()
            recieving_author[permlink]['bal'] = usd_reward
            recieving_author[permlink]['voters'] = [voter]