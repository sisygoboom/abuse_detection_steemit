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

nodes = ['https://rpc.buildteam.io',
         'https://api.steemit.com',
         'https://api.steem.house',
         'https://steemd.steemitdev.com',
         'https://steemd.steemitstage.com',
         'https://steemd.steemgigs.org']

s = Steem(nodes)
bchn = Blockchain(s)
set_shared_steem_instance(s)

######## USER CUSTOMIZABLE DATA ########
# Minimum vote worth to be considered abuse, remember that making this too high
# will prevent you from detecting botnets with lots of smaller votes
min_usd_reward = 0
# Choose your max time till cashout, this is currently set to one day
max_time_days = 1
max_time_hours = 24
# Choose what level of certainty is needed for a spammer/human/bot grouping
class_cert = 0.5
########################################

def db_loader(name, backup):
    """
    Checks file existance, loads to dictionary if true, uses backup if false
    """
    if Path(name).is_file():
        i = open(name,"r").read()
        data = json.loads(i)
        return data
    return backup

# Load json databases if they already exist
data = db_loader('abuse_log.json', {'voters':{},"recievers":{}})
sincerity_data = db_loader('sincerity_data.json', {})

def save():
    """
    Saves data to databases
    """
    # Save the data to the files
    for k,v in {
            'abuse_log.json':data,
            'sincerity_data.json':sincerity_data
            }.items():
        with open(k, "w") as file:
            file.write(json.dumps(v))
        
def find_role(sincerity_info):
    """
    Calculates role of the user based on user defined limits
    """
    # Defaults to unknown and stays this way unless one proves dominant
    
    if sincerity_info['bot_score'] > class_cert:
        role = 'bot'
        
    elif sincerity_info['spam_score'] > class_cert:
        role = 'spammer'
        
    elif sincerity_info['human_score'] > class_cert:
        role = 'human'
        
    else:
        role = 'unknown'
        
    return role

def info_digger(operation):
    """
    Main procedure, every vote we stream is sent here to be analysed
    """
    # Get preliminary information on the post: author and permlink
    author = operation['author']
    permlink = operation['permlink']
    
    # Get time until cashout
    creation = Comment(author + "/" + permlink).time_elapsed()
    week = timedelta(days=7)
    cashout = week - creation
    
    """
    Continue if the difference is smaller than accepted days, but hasn't
    cashed out.
    Bear in mind that a half day is the same as 0 days, a full 24 hours is
    needed for the day.
    """
    if cashout.days < max_time_days and cashout.days>=0:
        # Calculate difference in hours
        hours = cashout.seconds/3600
        
        # If the difference is below max accepted hours, continue
        if hours < max_time_hours:
            # Calculate the number of vests committed by the voter
            voter = operation['voter']
            # Get eight as a fraction
            weight = operation['weight']*0.0001
            voter_account = Account(voter)
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
                # Calculate how much steem that vote has earned the author
                reward_fund = s.get_reward_funds('post')
                fund_vests = float(reward_fund.get('recent_claims'))
                fund_balance = Amount(reward_fund.get('reward_balance')).amount
                fund_percent = vests/fund_vests
                to_steem = fund_percent * fund_balance
                
                # Convert that steem to usd using internal median price
                price = s.get_current_median_history()
                quote = Amount(price["quote"])
                base = Amount(price["base"])
                conversion_rate = base.amount / quote.amount
                usd_reward = float(conversion_rate * to_steem)
                
                # Continue if usdreward is above minimum requirements
                if usd_reward > min_usd_reward:
                    # Get spammer and bot ratings from steem sincerity
                    r = requests.get(
                            'https://steem-sincerity.dapptools.info/s/api/accounts-info/%s,%s'
                            % (voter, author))
                    accounts_info = r.json()['data']
                    
                    # Separate accounts
                    author_info = accounts_info[author]
                    voter_info = accounts_info[voter]
                    
                    # Store dictionary of bot, human and spammer scores
                    author_info = {
                            'bot_score':author_info['classification_bot_score'],
                            'spam_score':author_info['classification_spammer_score'],
                            'human_score':author_info['classification_human_score']
                            }
                    voter_info = {
                            'bot_score':voter_info['classification_bot_score'],
                            'spam_score':voter_info['classification_spammer_score'],
                            'human_score':voter_info['classification_human_score']
                            }
                    
                    # Update dictionaries with new sincerity data
                    sincerity_data[author] = author_info
                    sincerity_data[voter] = voter_info
                    
                    # Visual user feedback
                    print("$" + str(usd_reward))
                    print("voter: @%s (%s)" % (voter, find_role(voter_info)))
                    print("author: @%s (%s)" % (author, find_role(author_info)))
                    print("https://steemit.com/@%s/%s\n" % (author, permlink))
                    
                    """
                    Adds a tally to the voters # of outgoing last day votes
                    also, calculates the cumulative USD reward of all LM votes
                    both incoming and outgoing
                    """
                    voters = data['voters']
                    
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
                    recievers = data['recievers']
                    
                    if author in recievers:
                        # Get data for current author
                        recieving_author = recievers[author]
                        
                        # Specific post is already in database
                        if permlink in recieving_author:
                            # Get data for specific post
                            recieving_link = recieving_author[permlink]
                            # Update usd reward and add the new voter the the list
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
                    
                    save()

# Create datafile if it does not yet exist
save()

# Safetyloop
while True:
    try:
        # Blockstream (Mainloop) - streams all votes on the blockchain
        for i in bchn.stream(opNames=['vote']):
            # Check vote for eligibility
            info_digger(i)
            
    except Exception as e:
        print(e)
        # Switch nodes if stream breaks
        nodes = nodes[1:] + nodes[:1]
        print("=============== node unavaliable, switching ===============")
        sleep(1)