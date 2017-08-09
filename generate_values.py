import csv
from math import floor
import sys


class Player:
    def __init__(self, name):
        self.name = name
        self.projected_points = 0
        self.starter_vbd = 0
        self.bench_vbd = 0
        self.base_price = 0

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
            self.projected_points += getattr(self, action, 0) * scoring[action]

    def __str__(self):
        return "%s\t%s\t%s\t%f\t%f\t%f\t%f" % (self.name, self.position,
                                               self.team, self.projected_points,
                                               self.starter_vbd, self.bench_vbd,
                                               self.base_price)


class League:
    def __init__(self, user_settings, player_set):
        self.user_settings = user_settings
        self.player_set = player_set

    def calc_projected_points(self):
        list_of_players = self.player_set.get_all()
        for player in list_of_players:
            player.calc_points(self.user_settings.scoring)

    def get_starting_spots(self):
        starter_counts = {}
        starter_counts['QB'] = (self.user_settings.qb
                                * self.user_settings.num_teams)
        starter_counts['RB'] = (self.user_settings.rb
                                * self.user_settings.num_teams)
        starter_counts['WR'] = (self.user_settings.wr
                                * self.user_settings.num_teams)
        starter_counts['TE'] = (self.user_settings.te
                                * self.user_settings.num_teams)

        flex_list = self.player_set.get_flex(self.user_settings.flex_type,
                                             starter_counts['QB'],
                                             starter_counts['RB'],
                                             starter_counts['WR'],
                                             starter_counts['TE'],
                                             (self.user_settings.flex
                                              * self.user_settings.num_teams))

        for player in flex_list:
            starter_counts[player.position] += 1
        starter_counts['K'] = (self.user_settings.num_teams
                               * self.user_settings.k)
        starter_counts['DEF'] = (self.user_settings.num_teams
                                 * self.user_settings.team_def)
        return starter_counts

    def get_roster_spots(self, starter_counts):
        roster_spots = {}
        total_bench_size = (self.user_settings.bench
                            * self.user_settings.num_teams)
        total_starters = 0
        for position in ["QB", "RB", "WR", "TE"]:
            total_starters += starter_counts[position]

        if user_settings.bench_allocation is None:
            for position in ["QB", "RB", "WR", "TE"]:
                roster_spots[position] = int(
                    floor(starter_counts[position]
                        + (float(starter_counts[position]) / float(total_starters)
                            * total_bench_size)))
        else:
            for position in user_settings.bench_allocation:
                roster_spots[position] += user_settings.bench_allocation[position]
        return roster_spots

    def get_bench(self):
        starter_counts = self.get_starting_spots()
        roster_counts = self.get_roster_spots(starter_counts)
        bench_players = {}
        for position in ["QB", "RB", "WR", "TE"]:
            bench_players[position] = getattr(player_set, position)[starter_counts[
                position]:roster_counts[position]]
        return bench_players


class PlayerSet:
    def __init__(self):
        self.QB = []
        self.RB = []
        self.WR = []
        self.TE = []

    def get_all(self):
        return self.QB + self.RB + self.WR + self.TE

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
        for list_of_players in [self.QB, self.RB, self.WR, self.TE]:
            list_of_players.sort(key=lambda player: player.projected_points,
                                 reverse=True)
        top_n = {}
        for position in ["QB", "RB", "WR", "TE"]:
            top_n[position] = (getattr(self, position)
                               [:int(position_counts[position])])
        return top_n

    def load_projection_stats_from_csv(self, csv_filename):
        with open(csv_filename) as stats_file:
            reader = csv.reader(stats_file)
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


class UserSettings:

    def __init__(self, scoring, num_teams=12, team_budget=200, qb=1, rb=2, wr=2,
                 te=1, flex=1, k=1, team_def=1, bench=6, flex_type="rb/wr/te",
                 starter_budget_pct=.88, bench_allocation=None):
        self.scoring = scoring
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
        self.starter_budget_pct = starter_budget_pct
        self.bench_allocation = bench_allocation

    def get_roster_size(self):
        return (self.get_num_starters() + self.bench)

    def get_num_starters(self):
        return (self.qb + self.rb + self.wr + self.te + self.flex + self.k
                + self.team_def)

    def get_available_budget(self):
        return (self.team_budget * self.num_teams
                - ((self.k + self.team_def) * self.num_teams))


class VBDModel:
    def calc_vbd(self, league):
        starter_counts = league.get_starting_spots()
        roster_counts = league.get_roster_spots(starter_counts)
        starters = league.player_set.get_top_n(starter_counts)
        self.set_vbd(starters, 'starter_vbd')
        self.set_vbd(player_set.get_top_n(roster_counts), 'bench_vbd')

    def set_vbd(self, list_of_players, target_field):
        for position in list_of_players:
            pos_base_vbd = list_of_players[position][-1].projected_points
            for player in list_of_players[position]:
                setattr(player, target_field,
                        player.projected_points - pos_base_vbd)


class PriceModel:

    def calc_base_prices(self, league):
        bench_pf = self.get_bench_pf(league)
        starter_pf = self.get_starter_pf(league, bench_pf)

        for player in league.player_set.get_all():
            player.base_price = (player.starter_vbd * starter_pf +
                                 (player.bench_vbd - player.starter_vbd)
                                 * bench_pf)

    def get_bench_pf(self, league):
        bench_budget = (user_settings.get_available_budget()
                        * (1 - user_settings.starter_budget_pct))
        bench_players = league.get_bench()
        bench_vbd = 0
        for position in bench_players:
            for player in bench_players[position]:
                bench_vbd += player.bench_vbd
        return bench_budget / bench_vbd

    def get_starter_pf(self, league, bench_pf):
        starter_counts = league.get_starting_spots()

        starters = league.player_set.get_top_n(starter_counts)

        start_value_over_bench = 0
        starter_vbd = 0
        for position in starters:
            player = starters[position][0]
            start_value_over_bench += ((player.bench_vbd - player.starter_vbd)
                                       * starter_counts[position])
            for player in starters[position]:
                starter_vbd += player.starter_vbd

        starter_budget = ((user_settings.get_available_budget()
                          * user_settings.starter_budget_pct)
                          - start_value_over_bench * bench_pf)
        return starter_budget / starter_vbd


if __name__ == '__main__':
    scoring = {
        "passAtt": 0,
        "passComp": 0,
        "passYds": .04,
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

    user_settings = UserSettings(scoring, num_teams=10, wr=3)
    player_set = PlayerSet()
    league = League(user_settings, player_set)
    player_set.load_projection_stats_from_csv(sys.argv[1])
    league.calc_projected_points()
    #  @TODO Take starting totals and calculate starter and bench vbd
    vbd_model = VBDModel()
    vbd_model.calc_vbd(league)
    price_model = PriceModel()
    price_model.calc_base_prices(league)
#    print(player_set)
    calculated_prices = sum(player.base_price for player in player_set.get_all())
    print(calculated_prices)
    print(user_settings.get_available_budget())
    print("Budget margin: %f" % ((calculated_prices
                                  / user_settings.get_available_budget() - 1)))
