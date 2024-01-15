import requests
import json
from datetime import datetime, timezone
import time

class Utils(object):
    def days_difference(date_str):
        given_date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
        current_date = datetime.utcnow().replace(tzinfo=timezone.utc)
        difference = (current_date - given_date).days
        return difference


class FileHandler(object):
    @staticmethod
    def read_json(fileDir, data):
        with open(fileDir, 'r') as f:
            data = f.read()
        return json.loads(data)

    @staticmethod
    def write_json(fileDir, data):
        with open(fileDir, 'w') as f:
            f.write(json.dumps(data))

class Api(object):
    def __init__(self, bearer, serverID):
        self.__bearer = bearer
        self.__serverID = serverID
        self.__headers = {
            'Authorization': f'Bearer {self.__bearer}',
            'Content-Type': 'application/json',
        }

    @staticmethod
    def get_data(url, headers={}, params={}):
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            server_data = response.json()
            return server_data
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return None

    def get_server_list(self, size):
        params = {
            'filter[servers]': self.__serverID,
            'filter[online]': 'true',
            'page[size]': size,
        }
        return self.get_data("https://api.battlemetrics.com/players", self.__headers, params=params)

    def get_player_count(self):
        return self.get_data(url=f"https://api.battlemetrics.com/servers/{self.__serverID}")["data"]["attributes"]["players"]

    def set_serverID(self, newID):
        self.__serverID = newID

    def find_online_players(self):
        playerCount = self.get_player_count()
        self.__players = []
        if playerCount > 100:
            print(playerCount)
            numReq = (playerCount // 100) + 1
            size = playerCount // numReq
            data = self.get_server_list(size)
            FileHandler.write_json("bm.txt", data)
            self.add_to_players(data)
            next = self.find_next(data)
            for i in range(numReq):
                newData = self.get_data(next)
                next = self.find_next(newData)
                self.add_to_players(newData)
            print(len(self.__players))
        else:
            data = self.get_server_list(playerCount)
            self.add_to_players(data)
        return self.__players

    def add_to_players(self, data):
        for playerData in data["data"]:
            newPlayer = Player(playerData, self.__bearer, self.__serverID)
            self.__players.append(newPlayer)

    def find_next(self, data):
        return data["links"]["next"]

class Player(object):
    def __init__(self, data, bearer, serverID):
        self.id = data["id"]
        self.name = data["attributes"]["name"]
        self.AccountAge = Utils.days_difference(data["attributes"]["createdAt"])
        self.bearer = bearer
        self.hours = 0
        self.serverHours = 0
        self.firstJoinAge = None
        self.playerData = None
        self.serverID = serverID
        self.totalServers = 0

    def getPlayerData(self):
        headers = {
            'Authorization': f'Bearer {self.bearer}',
            'Content-Type': 'application/json',
        }
        params = {
            "include": "server",
            "fields[server]": "name"
        }
        self.playerData = Api.get_data("https://api.battlemetrics.com/players/"+self.id, headers=headers, params=params)

    def findHours(self):
        if not self.playerData:
            self.getPlayerData()
        for i in self.playerData["included"]:
            if i["relationships"]["game"]["data"]["id"] != "rust":
                continue
            if i["id"] == self.serverID:
                self.serverHours = i["meta"]["timePlayed"] / 3600
                self.firstJoinAge = Utils.days_difference(i["meta"]["firstSeen"])
            self.hours += i["meta"]["timePlayed"] / 3600
        self.totalServers = len(self.playerData["included"])


    def findFirstJoin(self):
        pass

if __name__ == "__main__":
    bearer_token = "" # UPLOAD YOUR TOKEN HERE
    server_id = "16772881"
    api = Api(bearer_token, server_id)
    players = api.find_online_players()
    print(len(players))
    count = 0
    explored = []
    for player in players:
        if player.id not in explored:
            explored.append(player.id)
        else:
            continue
        count += 1
        if count % 100 == 0:
            print(count)
        player.findHours()
        #priority goes accountAge, hours, firstJoinAge, serverHours
        #print(player.id, player.hours, player.serverHours, player.AccountAge, player.firstJoinAge)
        if player.AccountAge > 120:
            continue
        if player.AccountAge < 15:
            print("Low age", player.id)
        elif player.totalServers < 5:
            print("Super lower severs", player.id)
        elif player.hours < 50:
            print("Low hours", player.id)
        elif player.firstJoinAge < 1:
            print("New account", player.id)

    print(len(explored))



