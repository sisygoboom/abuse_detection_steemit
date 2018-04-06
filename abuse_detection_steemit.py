from steem.instance import set_shared_steemd_instance
from steem.blockchain import Blockchain
from steem.steemd import Steemd
from coinmarketcap import Market
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

coinmarketcap = Market()
s = Steem(nodes)
bchn = Blockchain(s)
set_shared_steemd_instance(Steemd(nodes=nodes))

# minimum vote worth to be considered abuse, remember that making this too high
# will prevent you from detecting botnets with lots of smaller votes
min_usd_reward = 0
#choose your max time till cashout, this is set to one day
max_time_days = 1
max_time_hours = 24

# load json database if it already exists, or create a new one
if Path("abuse_log").is_file():
    i = open("abuse_log","r").read()
    data = json.loads(i)
else:
    data = {'voters':{},"recievers":{}}

### saves data to database
def save():    
    with open("abuse_log", "w") as abuse_log:
        abuse_log.write(json.dumps(data))

def infoDigger(opType):
    # get preliminary information on the post: author, permlink and cashout time
    author = opType['author']
    permlink = opType['permlink']
    cashout = s.get_content(author, permlink)['cashout_time']
    # make cashout into a datetime object
    cashout = datetime.strptime(cashout, '%Y-%m-%dT%H:%M:%S')
    # get the difference between now and the cashout time
    now = datetime.now()
    diff = cashout - now
    
    # if the difference is smaller than accepted days, but hasn't cashed out, continue
    # bear in mind that a half day is the same as 0 days, a full 24 hours is needed for the day
    if diff.days < max_time_days and diff.days>=0:
        hours = diff.seconds/3600
        print("https://steemit.com/@" + author + "/" + permlink)
        print(str(hours) + " hours till payout")
        
        # if the difference is below max accepted hours, continue
        if hours < max_time_hours:
            # calculate the number of vests committed by the voter
            voter = opType['voter']
            weight = opType['weight']*0.0001
            try: voterAccount = s.get_account(voter)
            except: print(voter)
            vests = float(voterAccount['vesting_shares'].replace(" VESTS",""))
            vests -= float(voterAccount['delegated_vesting_shares'].replace(" VESTS",""))
            vests += float(voterAccount['received_vesting_shares'].replace(" VESTS",""))
            vests *= 1000000
            vests *= 0.02
            vests *= weight
            
            # make sure it's an upvote
            if vests > 0:
                # calculate how much steem that vote has earned the author
                rewardFund = s.get_reward_fund('post')
                fundVests = float(rewardFund.get('recent_claims'))
                fundBalance = Amount(rewardFund.get("reward_balance")).amount
                fundPercent = vests/fundVests
                to_steem = fundPercent * fundBalance
                
                price = s.get_current_median_history_price()
                quote = Amount(price["quote"])
                base = Amount(price["base"])
                conversion_rate = base.amount / quote.amount
                usdReward = float(conversion_rate * to_steem)
                
                print("$" + str(usdReward))
                print(voter)
                
                if usdReward > min_usd_reward:
                    # adds a tally to the voters # of outgoing last day votes
                    if voter in data['voters']:
                        data['voters'][voter] += 1
                    else: data['voters'][voter] = 1
                    
                    # updates the total revenue from last day votes for the author
                    # also updates stats for individual posts for further data mining
                    recievers = data['recievers']
                    if author in recievers:
                        recieving_author = recievers[author]
                        if permlink in recievers[author]:
                            recieving_link = recieving_author[permlink]
                            recieving_link['bal'] = usdReward
                            recieving_link['voters'].append(voter)
                            recieving_author['total_lme'] += usdReward
                        else:
                            recieving_author[permlink] = {'bal':usdReward,'voters':[voter]}
                            recieving_author['total_lme'] += usdReward
                    else:
                        recievers[author] = {'total_lme':usdReward,permlink:{'bal':usdReward,'voters':[voter]}}
                    
                    save()

save()
while True:
    try:
        # blockstream
        for i in bchn.stream(filter_by=['vote']):
            infoDigger(i)
    except Exception as e:
        print(e)
        # switch nodes if stream breaks
        nodes = nodes[1:] + nodes[:1]
        print("======================= node unavaliable, switching =======================")
        sleep(5)