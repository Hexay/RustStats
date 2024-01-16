import requests
import json
from datetime import datetime, timezone
import time
import os
import sys

class Utils(object):
    def days_difference(date_str):
        given_date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
        current_date = datetime.utcnow().replace(tzinfo=timezone.utc)
        difference = (current_date - given_date).days
        return difference


class FileHandler(object):
    @staticmethod
    def read_json(fileDir):
        with open(fileDir, 'r') as f:
            data = f.read()
        return json.loads(data)

    @staticmethod
    def write_json(fileDir, data):
        with open(fileDir, 'w') as f:
            f.write(json.dumps(data))

    @staticmethod
    def list_dir(dir):
        files = os.listdir(dir)
        return files

    @staticmethod
    def read_file(fileDir):
        with open(fileDir, 'r') as f:
            data = f.read()
        return data

    @staticmethod
    def write_file(fileDir, data):
        with open(fileDir, "w", encoding="utf-8") as f:
            f.write(data)

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

    def get_server_list(self):
        params = {
            'include': 'player',
        }
        return self.get_data(f"https://api.battlemetrics.com/servers/{self.__serverID}", self.__headers, params=params)

    def get_player_count(self):
        return self.get_data(url=f"https://api.battlemetrics.com/servers/{self.__serverID}")["data"]["attributes"]["players"]

    def set_serverID(self, newID):
        self.__serverID = newID

    def find_online_players(self):
        self.__players = []
        data = self.get_server_list()
        FileHandler.write_json("bm.txt", data)
        self.add_to_players(data)
        return self.__players

    def add_to_players(self, data):
        for playerData in data["included"]:
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
        self.clan = "[" in self.name
        #print(self.id, self.name,self.AccountAge)

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

class config(object):
    def __init__(self):
        self.data = self.exists()
        self.bearer = self.data["bearer"]
        self.serverID = self.data["serverID"]
        self.minAccountAge = self.data["minAccountAge"]
        self.totalServers = self.data["totalServers"]
        self.hours = self.data["hours"]
        self.firstJoinAge = self.data["firstJoinAge"]
        self.WriteOutputLinkRCON = self.data["WriteOutputLinkRCON"] == "True"


    def exists(self):
        if "config.json" in FileHandler.list_dir(os.getcwd()): # Lists files in current directory
            return FileHandler.read_json("config.json")
        else:
            self.no_config()

    def no_config(self):
        print("Copy config file from github!");
        FileHandler.write_json("config.json", "")
        time.sleep(3);
        sys.exit()

    def get_url(self, player):
        if self.WriteOutputLinkRCON:
            url = "https://www.battlemetrics.com/rcon/players/" + player.id
        else:
            url = "https://www.battlemetrics.com/players/" + player.id
        return url

if __name__ == "__main__":
    config = config()
    bearer_token = config.bearer
    server_id = config.serverID
    api = Api(bearer_token, server_id)
    players = api.find_online_players()
    print(len(players))
    count = 0
    explored = []
    s = ""
    for player in players:
        reason = ""
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
        x = True
        if player.totalServers < config.totalServers:
            reason = "Low Servers"
            print("Super lower severs", player.id)
        elif player.AccountAge < config.minAccountAge:
            reason = "New acc"
            print("Low age", player.id)
        elif player.hours < config.hours:
            reason = "Low hours"
            print("Low hours", player.id)
        elif player.firstJoinAge < config.firstJoinAge:
            reason = "Just joined server"
            print("New account", player.id)
        else:
            x = False

        if x:
            url = config.get_url(player)
            a = player.name + " - " + url + "\n"
            a += f"{reason} Servers:{str(player.totalServers)} Age:{str(player.AccountAge)} Hours:{str(round(player.hours,2))} FirstJoinServ:{str(player.firstJoinAge)}"+"\n"+"\n"
            s += a
    FileHandler.write_file("output.txt", s)




    print(len(explored))



