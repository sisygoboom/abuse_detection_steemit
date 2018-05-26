from beem.instance import set_shared_steem_instance
from beem.blockchain import Blockchain
#from beem.steemd import Steemd
from beem.amount import Amount
from beem.comment import Comment
from beem.account import Account
from beem import Steem
from datetime import datetime
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

# Minimum vote worth to be considered abuse, remember that making this too high
# will prevent you from detecting botnets with lots of smaller votes
min_usd_reward = 0
# Choose your max time till cashout, this is currently set to one day
max_time_days = 1
max_time_hours = 24

# load json database if it already exists
if Path("abuse_log.json").is_file():
    i = open("abuse_log.json","r").read()
    data = json.loads(i)
# Database doesn't already exist so we create one
else:
    data = {'voters':{},"recievers":{}}

### Saves data to database
def save():    
    with open("abuse_log.json", "w") as abuse_log:
        abuse_log.write(json.dumps(data))
        
def findRole(sincerity_info):
    role = 'unknown'
    if sincerity_info['bot_score'] > 0.5: role = 'bot'
    elif sincerity_info['spam_score'] > 0.5: role = 'spammer'
    elif sincerity_info['human_score'] > 0.5: role = 'human'
    return role

### Main procedure, every vote we stream is sent here to be analysed
def infoDigger(operation):
    # Get preliminary information on the post: author and permlink
    author = operation['author']
    permlink = operation['permlink']
    
    # Get time until cashout
    creation = Comment(author + "/" + permlink).time_elapsed()
    week = timedelta(days=7)
    cashout = week - creation
    
    # Continue if the difference is smaller than accepted days, but hasn't cashed out
    # Bear in mind that a half day is the same as 0 days, a full 24 hours is needed for the day
    if cashout.days < max_time_days and cashout.days>=0:
        # Calculate difference in hours
        hours = cashout.seconds/3600
        
        # If the difference is below max accepted hours, continue
        if hours < max_time_hours:
            ### Calculate the number of vests committed by the voter
            voter = operation['voter']
            # Get eight as a fraction
            weight = operation['weight']*0.0001
            try: voter_account = Account(voter)
            except: print(voter)
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
                    r = requests.get('https://steem-sincerity.dapptools.info/s/api/accounts-info/%s,%s' % (voter, author))
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
                    
                    # Visual user feedback
                    print("$" + str(usd_reward))
                    print("voter: @%s (%s)" % (voter, findRole(voter_info)))
                    print("author: @%s (%s)" % (author, findRole(author_info)))
                    print("https://steemit.com/@%s/%s\n" % (author, permlink))
                    
                    
                    # Adds a tally to the voters # of outgoing last day votes
                    # also, calculates the cumulative USD reward of all LM votes
                    # both incoming and outgoing
                    voters = data['voters']
                    
                    if voter in voters:
                        voters[voter]['quantity'] += 1
                        voters[voter]['value'] += usd_reward
                    # Create a new entry for unknown user
                    else:
                        voters[voter] = dict()
                        voters[voter]['quantity'] = 1
                        voters[voter]['value'] = usd_reward
                    # Store/update sincerity information
                    voters[voter]['info'] = voter_info
                    
                    # Updates the total revenue from last day votes for the author
                    # also updates stats for individual posts for further data mining
                    # Get current recievers database
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
                    
                    # Store/update sincerity information
                    recieving_author['info'] = author_info
                    
                    save()

# Create datafile if it does not yet exist
save()

### Safetylopp
while True:
#    try:
        # Blockstream (Mainloop) - streams all votes on the blockchain
        for i in bchn.stream(opNames=['vote']):
            # Check vote for eligibility
            infoDigger(i)
            
#    except Exception as e:
#        print(e)
#        # Switch nodes if stream breaks
#        nodes = nodes[1:] + nodes[:1]
#        print("======================= node unavaliable, switching =======================")
#        sleep(1)