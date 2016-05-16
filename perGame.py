from trueskill import Rating, rate_1vs1
import json
import sys
import requests
import os


class Player:

    def __init__(self, name):
        self.rank = Rating()  # Player's TrueSkill Rating object
        self.name = name  # Player's name
        self.playerIDs = {}  # Player ids are not consistent across tournaments, so this is a list of this player's id in each tournament
        self.won = 0
        self.lost = 0
        self.matches = []
        self.record = {}
        self.place = {}


class Match:
    def __init__(self, opponent, score, result, tIndex):
        self.opponent = opponent
        self.score = score
        self.result = result
        self.tIndex = tIndex


class Stats:
    def __init__(self, wins, losses):
        self.wins = wins
        self.losses = losses


class APIKeyMissingError(Exception):
    pass


# Helper function to make all tags lowercase, remove spaces and names in parentheses, and correct tag changes
# Example: Bonfire10 (Tom) -> bonfire10  Guard Skill -> guardskill
def standardizeName(tag):
    tag = tag.lower().replace(" ", "")  # Change the name to lowercase and remove any spaces
    tagEnd = tag.find('(', 0, len(tag))
    #print(tagEnd)
    if tagEnd != -1:
        tag = tag[:tagEnd]  # Remove the name in parentheses if it exists (Ex: "Tag (Name)" becomes "Tag")
    #print("New name is {}".format(str))
    for tags in taglist:
        if tag == tags['tag1']:
            tag = tags['tag2']
    # Fixes those who changed their tags, pairings stored in the config file.
    return tag


# Load data from config file (api key required, tag pairings optional)
api_key = ""
f = open('config.txt').read()
data = json.loads(f)
print(data)
if data.get('api_key'):
    api_key = data.get('api_key')
else:
    raise APIKeyMissingError() # Can't do much without an api key
taglist = []
if data.get('duplicate_tags'):
    taglist = data.get('duplicate_tags')


# Set up the directories for the output files.
script_dir = os.path.dirname(__file__)  # Absolute dir the script is in
rel_path = "prv2.csv"
abs_file_path = os.path.join(script_dir, rel_path)

rel_stats_path = "stats.txt"
abs_stats_path = os.path.join(script_dir, rel_stats_path)

rel_place_path = "place.txt"
abs_place_path = os.path.join(script_dir, rel_place_path)

# Gets all the tournament ids
tResp = requests.get('https://wpismash:'+api_key+'@api.challonge.com/v1/tournaments.json')
if tResp.status_code != 200:
    # This means something went wrong.
    print('stop that right now')
    print(tResp.status_code)
data = json.dumps(tResp.json(), indent=2)
load = json.loads(data)
tId = []
tList = []
for count, t in enumerate(load):
    #print(t["tournament"]["id"])
    if "Melee" in str(t["tournament"]["name"]) and ("Singles" in (str(t["tournament"]["name"])) or ("Singles:" in (str(t["tournament"]["name"])))) and not "Freshman" in (str(t["tournament"]["name"])) and not "pools" in (str(t["tournament"]["name"]).lower()):
        tId.append(t["tournament"]["id"])
        tList.append(count)

# Creates a helper list of the urls where the list of participants for each tournament is found.
pURLs = []
for i in tId:
    pURLs.append("https://wpismash:"+api_key+"@api.challonge.com/v1/tournaments/"+str(i)+"/participants.json")

# Creates the player objects and stores their player ids from each tournament they attended.
playerList = []
playerNames = []
pURL = "https://wpismash:"+api_key+"@api.challonge.com/v1/tournaments/"+str(tId[1])+"/participants.json"
for count, pURL in enumerate(pURLs):
    pResp = requests.get(pURL)
    pdata = json.dumps(pResp.json(), indent=2)
    pload = json.loads(pdata)
    for participant in pload:
        #print(participant)
        #print(participant["participant"]["name"])
        x = Player(participant['participant']['name'])
        if "Bye" not in participant['participant']['name']:
            tempName = standardizeName(participant['participant']['name'])
            if tempName not in playerNames:
                playerNames.append(tempName)
                for t, i in enumerate(tList):
                    x.playerIDs[t] = 0 # All player ids for all tournaments are initialized to 0, then filled in for tournaments that player attended
                x.playerIDs[count] = participant['participant']['id']
                playerList.append(x)
            else:
                #print(participant['participant']['name'])
                for player in playerList:
                    if standardizeName(player.name) == tempName:
                        player.playerIDs[count] = participant['participant']['id']
                        player.place[count] = participant['participant']['final_rank']
'''
for name in playerNames:
    print (name)

for player in playerList:
    for x in range(0,len(player.playerIDs)):
        print(player.playerIDs[x])
'''
# The first number in range is the number of the starting tournament to record. 15 corresponds to the first tournament of the 2015-2016 school year.
for x in range(15, len(tId)):
    print("Tournament # " + str(x))
    mURL = "https://wpismash:"+api_key+"@api.challonge.com/v1/tournaments/"+str(tId[x])+"/matches.json"
    mResp = requests.get(mURL)
    mdata = json.dumps(mResp.json(), indent=2)
    mload = json.loads(mdata)
    for match in mload:
        #print(match['match'])
        #print(match['match']['winner_id'])
        #print(match['match']['loser_id'])
        for count, player in enumerate(playerList, start=0):
            if player.playerIDs[x] == match['match']['winner_id']:
                winnerindex = count
            if player.playerIDs[x] == match['match']['loser_id']:
                loserindex = count
        #if playerList[loserindex].name == "Stormcloud (Lindsay)":
            #print("old : " +str(playerList[loserindex].rank.sigma))

        score1 = match['match']['scores_csv'].split('-')[0]
        score2 = match['match']['scores_csv'].split('-')[1]
        score = match['match']['scores_csv']
        if score1 < score2:
            score = score2+"-"+score1
        loserScore = min(int(score1), int(score2))
        winnerScore = max(int(score1), int(score2))
        newr1 = playerList[loserindex].rank
        newr2 = playerList[winnerindex].rank
        for j in range(0, loserScore):
            playerList[loserindex].rank, playerList[winnerindex].rank = rate_1vs1(newr1, newr2)
            newr1 = playerList[loserindex].rank
            newr2 = playerList[winnerindex].rank
        for k in range(0, winnerScore):
            playerList[winnerindex].rank, playerList[loserindex].rank = rate_1vs1(newr2, newr1)
            newr1 = playerList[loserindex].rank
            newr2 = playerList[winnerindex].rank
        playerList[loserindex].lost+=1
        playerList[winnerindex].won+=1

        playerList[loserindex].matches.append(Match(playerList[winnerindex].name,
                                                    score,
                                                    "Lost",
                                                    x))
        playerList[winnerindex].matches.append(Match(playerList[loserindex].name,
                                                     score,
                                                     "Won",
                                                     x))
        #print("score was "+match['match']['scores_csv'])

        # if playerList[loserindex].name == "Stormcloud (Lindsay)":
        #   print("new : " +str(playerList[loserindex].rank.sigma))
'''
for player in playerList:
    if player.name == "Stormcloud (Lindsay)":
        for x in range(0, len(player.playerIDs)):
            print(str(player.playerIDs[x]))
'''

sortList = []

# Eligibility calculations
for player in playerList:
    t = 0
    recent = 0
    for tournamentID in player.playerIDs:
        if player.playerIDs[tournamentID] != 0:
            t += 1
    x = 0
    for tournamentID in player.playerIDs:
        if player.playerIDs[tournamentID] != 0 and x > 14:  # This is the tournament number that is the cutoff for "recent"
            recent += 1
        x += 1
    print(player.name + " attended " + str(recent) + " tournaments")
    if recent >= 4:  # Number of tournaments the player must have attended; can be recent, overall, or both.
        sortList.append(player)

# Sorts by rank (mu - 3*sigma) to make excel sheet easier to work with
for passnum in range(len(sortList)-1, 0, -1):
        for i in range(passnum):
            if (sortList[i].rank.mu - sortList[i].rank.sigma*3) < (sortList[i+1].rank.mu - sortList[i+1].rank.sigma*3):
                temp = sortList[i]
                sortList[i] = sortList[i+1]
                sortList[i+1] = temp

for player in playerList:
    for m in player.matches:
        stats = player.record.get(m.opponent)  # Gets this player's record against their opponent in a given match
        if stats is None:  # If the player doesn't have any matches against this person recorded yet, create a new Stats object.
            if m.result == "Won":
                player.record[m.opponent] = Stats(1, 0)
            else:
                player.record[m.opponent] = Stats(0, 1)
        else:
            if m.result == "Won":
                player.record[m.opponent].wins += 1
            else:
                player.record[m.opponent].losses += 1

# Writes the PR
f = open(abs_file_path, 'w')

f.write("Name")
f.write(",")
f.write("Mu")
f.write(",")
f.write("Sigma")
f.write(",")
f.write("TrueSkill")
f.write(",")
f.write("Total Wins")
f.write(",")
f.write("Total Losses")
f.write('\n')

for player in sortList:
    f.write(player.name)
    f.write(",")
    f.write(str(player.rank.mu))
    f.write(",")
    f.write(str(player.rank.sigma))
    f.write(",")
    f.write(str(player.rank.mu - player.rank.sigma*3))
    f.write(",")
    f.write(str(player.won))
    f.write(",")
    f.write(str(player.lost))
    f.write('\n')
f.close()
print(abs_file_path)

# Writes the stats file
s = open(abs_stats_path, 'w')
s.write("Name")
s.write(",")
s.write("Opponent")
s.write(",")
s.write("Score")
s.write(",")
s.write("Result")
s.write(",")
s.write("Tournament ID#")
s.write('\n')

for player in sortList:
    for m in player.matches:
        s.write(player.name)
        s.write(",")
        s.write(m.opponent)
        s.write(",")
        s.write(m.score)
        s.write(",")
        s.write(m.result)
        s.write(",")
        s.write(str(m.tIndex))
        s.write('\n')

s.write('\n')
s.write("Name")
s.write(",")
s.write("Opponent")
s.write(",")
s.write("Wins")
s.write(",")
s.write("Losses")
s.write(",")
s.write("Winrate")
s.write(",")
s.write("Total Winrate")
s.write('\n')

for player in sortList:
    doneWinrate = False
    for oppo in player.record:
        s.write(player.name)
        s.write(",")
        s.write(oppo)
        s.write(",")
        s.write(str(player.record[oppo].wins))
        s.write(",")
        s.write(str(player.record[oppo].losses))
        s.write(",")
        s.write(str(player.record[oppo].wins/(player.record[oppo].wins + player.record[oppo].losses)))
        if not doneWinrate:
            s.write(",")
            s.write(str(player.won/(player.won+player.lost)))
            doneWinrate = True
        s.write('\n')

s.close()

# Stats on each player's placements, separate file from other stats
p = open(abs_place_path, 'w')
for player in sortList:
    for r in player.place:
        p.write(player.name)
        p.write(",")
        p.write(str(r))
        p.write(",")
        p.write(str(player.place[r]))
        p.write('\n')

p.close()

print(abs_stats_path)
print(sys.version)



