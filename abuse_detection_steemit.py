from beem.instance import set_shared_steem_instance
from beem.blockchain import Blockchain
from beem.amount import Amount
from beem.comment import Comment
from beem.account import Account
from beem import Steem
from datetime import timedelta
from pathlib import Path
from time import sleep
import json
import requests

class AbuseDetection:
    """
    The abuse detection library gives the user the ability to collect, store
    and live view potentially mallicious last minute upvotes.
    """
    
    def __init__(
            self,
            min_usd_reward=0,
            max_time_hours=24,
            certainty=0.5,
            containing_folder=''):
        """
        Initialise the abuse detection class.
        
        Certainty defaults to 50%, certainty is the min bot/human/spammer score
        needed to definitively fall into one of the classes.
        
        Containing folder is where you have stored your .json DBs.
        """
        
        self.nodes = [
                'https://api.steemit.com',
                'https://rpc.buildteam.io',
                'https://api.steem.house',
                'https://steemd.steemitdev.com',
                'https://steemd.steemitstage.com',
                'https://steemd.steemgigs.org'
                ]
        s = Steem(self.nodes)
        self.bchn = Blockchain(s)
        set_shared_steem_instance(s)
        self.s = s
        
        containing_folder.replace('\\','/')
        if not containing_folder.endswith('/'):
            containing_folder += '/'
        
        self.certainty = certainty
        self.min_usd_reward = min_usd_reward
        self.max_time_hours = max_time_hours
        self.containing_folder = containing_folder
        
        try:
            self.data = self.db_loader(
                    containing_folder + 'abuse_log.json'
                    )
            self.sincerity_data = self.db_loader(
                    containing_folder + 'sincerity_data.json'
                    )
        except:
            self.data = {'voters':{},"recievers":{}}
            self.sincerity_data = dict()
            
        self.save()
    
    """
    Stream the steem blockchain and sends every vote transaction off to be
    checked. Comes with built in exception handling.
    """
    def stream(self):        
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
    Check file existance, loads to dictionary if true, use backup if false.
    
    @param filepath
    @return data
    """
    def db_loader(self, filepath):        
        if Path(filepath).is_file():
            i = open(filepath,"r").read()
            data = json.loads(i)
            return data
        raise FileNotFoundError('File does not exist.')
        
    def save(self):
        """
        Saves data to databases
        """
        # Save the data to the files
        for k,v in {
                self.containing_folder + 'abuse_log.json':self.data,
                self.containing_folder + 'sincerity_data.json':self.sincerity_data
                }.items():
            with open(k, "w") as file:
                file.write(json.dumps(v))
                
    def find_role(self, sincerity_info):
        """
        Calculates role of the user based on user defined limits
        """
        # Defaults to unknown and stays this way unless one proves dominant
        
        if sincerity_info['bot_score'] > self.certainty:
            return 'bot'
            
        elif sincerity_info['spam_score'] > self.certainty:
            return 'spammer'
            
        elif sincerity_info['human_score'] > self.certainty:
            return 'human'
            
        else:
            return 'unknown'


    def info_digger(self, operation):
        """
        Main procedure, every vote we stream is sent here to be analysed
        """
        self.author = operation['author']
        self.permlink = operation['permlink']
        self.voter = operation['voter']
        usd_reward = self._check(operation)
        if usd_reward != False:
            self._sincerity_update(
                    usd_reward, self.voter, self.author, self.permlink
                    )
            self._update_db(
                    usd_reward, self.voter, self.author, self.permlink
                    )
            self.save()
        
    def _check(self, operation):
        usd_reward = self.age_check(operation)
        return usd_reward
    
    """
    Checks to make sure the post voted on is old enough to be considered abuse
    """
    def _age_check(self, operation):
        # Get preliminary information on the post: author and permlink
        
        # Get time until cashout
        creation = Comment(self.author + "/" + self.permlink).time_elapsed()
        week = timedelta(days=7)
        cashout = week - creation
        
        # Continue if the difference is smaller than accepted days, but hasn't
        # cashed out.
        # Bear in mind that a half day is the same as 0 days, a full 24 hours
        # is needed for the day.
    
        # Calculate difference in hours
        hours = cashout.total_seconds()/3600
        
        # If the difference is below max accepted hours, continue
        if hours < self.max_time_hours and hours > 0:
            return self._vest_check(operation)
        else:
            return False
        
    def _vest_check(self, operation):
        # Calculate the number of vests committed by the voter
        
        # Get eight as a fraction
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
        
        # Continue if usdreward is above minimum requirements
        if usd_reward > self.min_usd_reward:
            return usd_reward
        else:
            return False
        
    def _sincerity_update(self, usd_reward, voter, author, permlink):
        
        r = requests.get(
                'https://steem-sincerity.dapptools.'
                'info/s/api/accounts-info/%s,%s'
                % (voter, author))
        accounts_info = r.json()['data']
        
        # Separate accounts
        author_info = accounts_info[author]
        voter_info = accounts_info[voter]
        
        # Store dictionary of bot, human and spammer scores
        author_info = {
                'bot_score':
                    author_info['classification_bot_score'],
                'spam_score':
                    author_info['classification_spammer_score'],
                'human_score':
                    author_info['classification_human_score']
                }
        voter_info = {
                'bot_score':
                    voter_info['classification_bot_score'],
                'spam_score':
                    voter_info['classification_spammer_score'],
                'human_score':
                    voter_info['classification_human_score']
                }
        
        # Update dictionaries with new sincerity data
        self.sincerity_data[author] = author_info
        self.sincerity_data[voter] = voter_info
        
        # Visual user feedback
        print("$" + str(usd_reward))
        print("voter: @%s (%s)" % 
              (voter, self.find_role(voter_info)))
        print("author: @%s (%s)" % 
              (author, self.find_role(author_info)))
        print("https://steemit.com/@%s/%s\n" % 
              (author, permlink))
        
    def _update_db(self, usd_reward, voter, author, permlink):
        voters = self.data['voters']
        recievers = self.data['recievers']
        
        if voter in voters:
            voters[voter]['quantity'] += 1
            voters[voter]['value'] += usd_reward
        # Create a new entry for unknown user
        else:
            voters[voter] = dict()
            voters[voter]['quantity'] = 1
            voters[voter]['value'] = usd_reward
        
        """
        Updates the total revenue from last day votes for the 
        author, also updates stats for individual posts for
        further data mining
        """
        
        
        if author in recievers:
            # Get data for current author
            recieving_author = recievers[author]
            
            # Specific post is already in database
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
            recieving_author['total_lme'] += usd_reward
            # Add new voter to list
            recieving_link['voters'].append(voter)
        
        # Author is not in the database yet
        else:
            # Create dictionary for new author
            recievers[author] = dict()
            recieving_author = recievers[author]
            # Populate with necessary information
            recieving_author['total_lme'] = usd_reward
            recieving_author[permlink] = dict()
            recieving_author[permlink]['bal'] = usd_reward
            recieving_author[permlink]['voters'] = [voter]