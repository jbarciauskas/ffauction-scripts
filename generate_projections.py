import csv
import sys


class Player:
    def __init__(self, name):
        self.name = name
        self.projected_points = 0
        self.starter_vbd = 0
        self.bench_vbd = 0

    def init_from_row(self, row):
        self.team = row['team']
        self.position = row['position']

        self.passAtt = float(row['passAtt'])
        self.passComp = float(row['passComp'])
        self.passYds = float(row['passYds'])
        self.passTds = float(row['passTds'])
        self.twoPts = float(row['twoPts'])
        self.sacks = float(row['sacks'])
        self.passInt = float(row['passInt'])
        self.rushAtt = float(row['rushAtt'])
        self.rushYds = float(row['rushYds'])
        self.rushTds = float(row['rushTds'])
        self.rec = float(row['rec'])
        self.recYds = float(row['recYds'])
        self.recTds = float(row['recTds'])
        self.fumbles = float(row['fumbles'])

    def calc_points(self, scoring):
        self.projected_points = 0
        for action in scoring:
            print(action)
            self.projected_points += getattr(self, action, 0) * scoring[action]

    def __str__(self):
        return "%s\t%s\t%s\t%f\t%f\t%f" % (self.name, self.position, self.team,
                                           self.projected_points,
                                           self.starter_vbd, self.bench_vbd)


class PlayerSet:
    def __init__(self):
        self.QB = []
        self.RB = []
        self.WR = []
        self.TE = []
        pass

    # @TODO Add other flex types
    def get_flex(self, flex_type, qb, rb, wr, te, flex):
        if flex_type == "rb/wr/te":
            remaining_rb = self.RB[rb:]
            remaining_wr = self.WR[wr:]
            remaining_te = self.TE[te:]
            remaining = sorted(remaining_rb + remaining_wr + remaining_te,
                               key=lambda player: player.projected_points,
                               reverse=True)
            return remaining[:flex]

    def get_top_n(self, position_counts):
        top_n = {}
        for position in ["QB", "RB", "WR", "TE"]:
            print(position_counts[position])
            top_n[position] = getattr(self, position)[:int(position_counts[position])]
        return top_n

    def calc_projected_points(self, scoring):
        for list_of_players in [self.QB, self.RB, self.WR, self.TE]:
            for player in list_of_players:
                player.calc_points(scoring)
        for list_of_players in [self.QB, self.RB, self.WR, self.TE]:
            list_of_players.sort(key=lambda player: player.projected_points,
                                 reverse=True)

    def load_projection_stats_from_csv(self, csvFilename):
        with open(csvFilename) as statsFile:
            reader = csv.reader(statsFile)
            headers = next(reader)
            for row in reader:
                name = row[0]
                player = Player(name)
                rowDict = {}
                for i in range(1, len(row)):
                    rowDict[headers[i]] = row[i]

                player.init_from_row(rowDict)

                if player.position == 'QB':
                    self.QB.append(player)
                if player.position == 'RB':
                    self.RB.append(player)
                if player.position == 'WR':
                    self.WR.append(player)
                if player.position == 'TE':
                    self.TE.append(player)

    def __str__(self):
        table_of_players = ""
        for list_of_players in [self.QB, self.RB, self.WR, self.TE]:
            for player in list_of_players:
                table_of_players += str(player) + "\n"
        return table_of_players


class League:

    def __init__(self, point_settings, num_teams=12, team_budget=200, qb=1,
                 rb=2, wr=2, te=1, flex=1, k=1, team_def=1, bench=6,
                 flex_type="rb/wr/te"):
        self.point_settings = point_settings
        self.num_teams = num_teams
        self.team_budget = team_budget
        self.qb = qb
        self.rb = rb
        self.wr = wr
        self.te = te
        self.flex = flex
        self.k = k
        self.team_def = team_def
        self.bench = bench
        self.flex_type = flex_type

    def get_roster_size(self):
        return (self.get_num_starters() + self.bench)

    def get_num_starters(self):
        return (self.qb + self.rb + self.wr + self.te + self.flex + self.k +
                self.team_def)

    def get_starting_spots(self, player_set):
        self.starter_counts = {}
        self.starter_counts['QB'] = self.qb * self.num_teams
        self.starter_counts['RB'] = self.rb * self.num_teams
        self.starter_counts['WR'] = self.wr * self.num_teams
        self.starter_counts['TE'] = self.te * self.num_teams

        flex_list = player_set.get_flex(self.flex_type,
                                        self.starter_counts['QB'],
                                        self.starter_counts['RB'],
                                        self.starter_counts['WR'],
                                        self.starter_counts['TE'],
                                        self.flex * self.num_teams)

        for player in flex_list:
            self.starter_counts[player.position] += 1
        self.starter_counts['K'] = self.num_teams * self.k
        self.starter_counts['DEF'] = self.num_teams * self.team_def
        return self.starter_counts

    def get_roster_spots(self, starter_counts):
        roster_spots = {}
        total_bench_size = self.bench * self.num_teams
        total_starters = 0
        for position in starter_counts:
            total_starters += starter_counts[position]

        for position in starter_counts:
            roster_spots[position] = (starter_counts[position]
                                      + (starter_counts[position]
                                         / total_starters * total_bench_size))

        return roster_spots


def get_point_settings():
    """
    Returns a dictionary of the point value of each type of action for a league
    """
    return {
        "passAtt": 0,
        "passComp": 0,
        "passYds": .4,
        "passTds": 4,
        "twoPts": 2,
        "sacks": -.5,  # Yahoo default: 0
        "passInt": -2,  # Yahoo default: 1
        "rushAtt": 0,
        "rushYds": .1,
        "rushTds": 6,
        "rec": 0,  # PPR setting
        "recYds": .1,
        "recTds": 6,
        "fumbles": -2
    }


class VBDModel:
    def __init__(self, league):
        self.league = league

    def calc_vbd(self, player_set):
        starter_counts = self.league.get_starting_spots(player_set)
        roster_counts = self.league.get_roster_spots(starter_counts)
        self.starter_vbd = 0
        self.bench_vbd = 0
        self.set_vbd(player_set.get_top_n(starter_counts), 'starter_vbd')
        self.set_vbd(player_set.get_top_n(roster_counts), 'bench_vbd')

    def set_vbd(self, list_of_players, target_field):
        for position in list_of_players:
            pos_base_vbd = list_of_players[position][-1].projected_points
            for player in list_of_players[position]:
                setattr(player, target_field,
                        player.projected_points - pos_base_vbd)


if __name__ == '__main__':
    player_set = PlayerSet()
    player_set.load_projection_stats_from_csv(sys.argv[1])
    player_set.calc_projected_points(get_point_settings())
    print(player_set)
    league = League(get_point_settings(), num_teams=10, wr=3)
    print(league.get_starting_spots(player_set))
    #  @TODO Take starting totals and calculate starter and bench vbd
    vbdModel = VBDModel(league)
    vbdModel.calc_vbd(player_set)
    print(player_set)
