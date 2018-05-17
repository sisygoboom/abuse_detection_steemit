from steem.instance import set_shared_steemd_instance
from steem.blockchain import Blockchain
from steem.steemd import Steemd
from steem.amount import Amount
from datetime import datetime
from pathlib import Path
from steem import Steem
from time import sleep
import json

nodes = ['https://rpc.buildteam.io',
         'https://api.steemit.com',
         'https://api.steem.house',
         'https://steemd.steemitdev.com',
         'https://steemd.steemitstage.com',
         'https://steemd.steemgigs.org']

s = Steem(nodes)
bchn = Blockchain(s)
set_shared_steemd_instance(Steemd(nodes=nodes))

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

### Main procedure, every vote we stream is sent here to be analysed
def infoDigger(operation):
    # Get preliminary information on the post: author, permlink and cashout time
    author = operation['author']
    permlink = operation['permlink']
    cashout = s.get_content(author, permlink)['cashout_time']
    # Make cashout into a datetime object
    cashout = datetime.strptime(cashout, '%Y-%m-%dT%H:%M:%S')
    # Get the difference between current time and the cashout time
    now = datetime.now()
    diff = cashout - now
    
    # Continue if the difference is smaller than accepted days, but hasn't cashed out
    # Bear in mind that a half day is the same as 0 days, a full 24 hours is needed for the day
    if diff.days < max_time_days and diff.days>=0:
        # Calculate difference in hours
        hours = diff.seconds/3600
        
        # If the difference is below max accepted hours, continue
        if hours < max_time_hours:
            ### Calculate the number of vests committed by the voter
            voter = operation['voter']
            # Get eight as a fraction
            weight = operation['weight']*0.0001
            try: voter_account = s.get_account(voter)
            except: print(voter)
            # Tally vests
            vests = float(voter_account['vesting_shares'].replace(' VESTS',''))
            vests -= float(voter_account['delegated_vesting_shares'].replace(' VESTS',''))
            vests += float(voter_account['received_vesting_shares'].replace(' VESTS',''))
            # Vests if upvote was 100%
            vests *= 1000000
            vests *= 0.02
            # Multiply by weight (fraction)
            vests *= weight
            
            # Ignore downvotes
            if vests > 0:
                # Calculate how much steem that vote has earned the author
                reward_fund = s.get_reward_fund('post')
                fund_vests = float(reward_fund.get('recent_claims'))
                fund_balance = Amount(reward_fund.get('reward_balance')).amount
                fund_percent = vests/fund_vests
                to_steem = fund_percent * fund_balance
                
                # Convert that steem to usd using internal median price
                price = s.get_current_median_history_price()
                quote = Amount(price["quote"])
                base = Amount(price["base"])
                conversion_rate = base.amount / quote.amount
                usd_reward = float(conversion_rate * to_steem)
                
                # Continue if usdreward is above minimum requirements
                if usd_reward > min_usd_reward:
                    # Visual user feedback
                    print("$" + str(usd_reward))
                    print(voter)
                    print("https://steemit.com/@" + author + "/" + permlink)
                    
                    # Adds a tally to the voters # of outgoing last day votes
                    # also, calculates the cumulative USD reward of all LM votes
                    # both incoming and outgoing
                    if voter in data['voters']:
                        data['voters'][voter]['quantity'] += 1
                        data['voters'][voter]['value'] += usd_reward
                    # Create a new entry for unknown user
                    else:
                        data['voters'][voter] = {"quantity":1,"value":usd_reward}
                    
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
                        # Populate with necessary information
                        recievers[author]['total_lme'] = usd_reward,
                        recievers[author][permlink] = dict()
                        recievers[author][permlink]['bal'] = usd_reward,
                        recievers[author][permlink]['voters'] = [voter]
                    
                    save()

# Create datafile if it does not yet exist
save()

### Safetylopp
while True:
    try:
        # Blockstream (Mainloop) - streams all votes on the blockchain
        for i in bchn.stream(filter_by=['vote']):
            # Check vote for eligibility
            infoDigger(i)
            
    except Exception as e:
        print(e)
        # Switch nodes if stream breaks
        nodes = nodes[1:] + nodes[:1]
        print("======================= node unavaliable, switching =======================")
        sleep(1)