"""models.py - class definitions for the Zombie Dice game."""

import random
from datetime import date
from protorpc import messages
from google.appengine.ext import ndb


class User(ndb.Model):
    """User Profile"""
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty()
    wins = ndb.IntegerProperty(default=0)
    total_played = ndb.IntegerProperty(default=0)

    @property
    def win_percentage(self):
        if self.total_played > 0:
            return float(self.wins) / float(self.total_played)
        else:
            return float(0)

    def to_form(self):
        return UserForm(name=self.name,
                        email=self.email,
                        wins=self.wins,
                        total_played=self.total_played,
                        win_percentage=self.win_percentage)

    def add_win(self):
        """Add a win"""
        self.wins += 1
        self.total_played += 1
        self.put()

    def add_loss(self):
        """Add a loss"""
        self.total_played += 1
        self.put()

class Game(ndb.Model):
    """Game object"""
    players = ndb.KeyProperty(repeated=True, kind='User')
    statuses = ndb.PickleProperty()
    next_turn = ndb.KeyProperty()  # whose turn it is
    final_player = ndb.KeyProperty()
    game_over = ndb.BooleanProperty(required=True, default=False)
    winner = ndb.KeyProperty()

    @classmethod
    def new_game(cls, *args):
        """creates and returns a new game"""

        # creates the game
        game = Game()  
        game.statuses = {}
        # strip out the list to get to the underlying keys
        for item in args:
            for player in item:
                # sets the next_turn to the first player in the list of players
                game.players.append(player)
                game.statuses[player] = 0

        game.put()
        # finish creating the game (to get a key) before creating next turn
        next_turn = Turn.new_turn(game.players[0], game.key)
        game.next_turn = next_turn.key
        game.put()
        return game

    def to_form(self):
        """Returns a GameForm representation of the Game"""
        # get names of each player in the list of players
        p = []
        for player in self.players:
            p.append(player.get().name)
        # unpack the statuses dict and get names and scores for each player
        s = []
        for player, score in self.statuses.items():
            name = player.get().name
            s.append((name, score))

        try:
            finalPlayer = self.final_player.get().name
        except AttributeError:
            finalPlayer = "None"

        form = GameForm(urlsafe_key=self.key.urlsafe(),
                        status=str(s),
                        players=str(p),
                        next_turn=self.next_turn.get().player.get().name,
                        final_player=finalPlayer,
                        game_over=self.game_over,
                        next_turn_key=str(self.next_turn.urlsafe()))
        if self.winner:
            form.winner = self.winner.get().name
        return form

    def end_game(self, winner):
        """Ends the game"""
        self.winner = winner
        self.game_over = True
        self.put()
        losers = []
        for player in self.players:
            if player != self.winner:
                losers.append(player)
        score = Score(date=date.today(), winner=winner, losers=losers)
        score.put()

        # update the users
        winner.get().add_win()
        for loser in losers:
            loser.get().add_loss()

    def end_turn(self, turn):
        """Adds brains to the player's score,
        creates a new turn and updates the next_turn, checks win conditions"""
        # get the index of the last player
        i = self.players.index(turn.player)
        # only score if player didn't die from 3 or more shots
        if turn.shots < 3:
            score = self.statuses[turn.player]
            score += turn.brains
            self.statuses[turn.player] = score
            self.put()

            # if the last player to play was the final player, figure out the
            # winner and end the game
            if turn.player == self.final_player:
                winner = max(
                    self.statuses.iterkeys(), key=(
                        lambda key: self.statuses[key]))
                self.end_game(winner)
            if score > 12:
                # this works because the first player has an index of 0
                # and getting list[-1] returns the last item on the list
                self.final_player = self.players[i - 1]

        # if at the end of the players list, start back at the beginning
        if len(self.players) - 1 == i:
            next_turn = Turn.new_turn(self.players[0], self.key)

        # otherwise just go to the next player on the list
        else:
            next_turn = Turn.new_turn(self.players[i + 1], self.key)

        # save our work
        self.next_turn = next_turn.key
        next_turn.put()
        # update the game's next turn to be the new turn generated
        self.next_turn = next_turn.key
        self.put()

class Turn(ndb.Model):
    """Works to track each turn"""

    player = ndb.KeyProperty(required=True)  # The User whose turn it is
    game = ndb.KeyProperty(required=True)  # The Game the turn is a part of
    turn_over = ndb.BooleanProperty(default=False)
    cup = ndb.PickleProperty(required=True)
    pool = ndb.PickleProperty(required=True)
    green_used = ndb.IntegerProperty(default=0)
    yellow_used = ndb.IntegerProperty(default=0)
    red_used = ndb.IntegerProperty(default=0)
    brains = ndb.IntegerProperty(default=0)
    shots = ndb.IntegerProperty(default=0)

    @classmethod
    def new_turn(cls, user, game):
        """Creates a new turn"""
        g = ("green", ["brain", "brain", "brain", "foot", "foot", "shot"])
        y = ("yellow", ["brain", "brain", "foot", "foot", "shot", "shot"])
        r = ("red", ["brain", "foot", "foot", "shot", "shot", "shot"])
        turn_id = Turn.allocate_ids(size=1, parent=game)[0]
        turn = Turn(player=user,
                    game=game,
                    cup=[g, g, g, g, g, g,
                         y, y, y, y,
                         r, r, r],
                    pool=[],
                    key=ndb.Key(Turn, turn_id, parent=game),)
        turn.put()
        return turn

    def to_form(self):
        """Returns a TurnForm representation of the Turn"""
        form = TurnForm(player=self.player.get().name,
                        game=str(self.game.get().key.urlsafe()),
                        turn_key=str(self.key.urlsafe()),
                        turn_over=self.turn_over,
                        pool=str(self.pool),
                        green_used=self.green_used,
                        yellow_used=self.yellow_used,
                        red_used=self.red_used,
                        brains=self.brains,
                        shots=self.shots)
        return form

    def take_turn(self):
        """Take a turn, modifying the turn object and returning a TurnForm."""
        # populate the dice pool with three random dice from the cup

        while len(self.pool) < 3:
            die = self.cup.pop(random.randint(0, len(self.cup) - 1))
            self.pool.append(die)
        # make a copy of the pool so we can modify as we go.

        for item in self.pool[:]:
            # roll each item, returning a result like ("green", "brain")
            result = (item[0], item[1][(random.randint(0, 5))])
            if result[1] == "brain":
                self.brains += 1
                # only add to color_used if the result is a brain or shot
                if result[0] == "green":
                    self.green_used += 1
                if result[0] == "red":
                    self.red_used += 1
                if result[0] == "yellow":
                    self.yellow_used += 1
                self.pool.remove(item)
            if result[1] == "shot":
                self.shots += 1
                # feel like I'm violating DRY principle but not sure how to fix
                if result[0] == "green":
                    self.green_used += 1
                if result[0] == "red":
                    self.red_used += 1
                if result[0] == "yellow":
                    self.yellow_used += 1
                self.pool.remove(item)
        self.put()
        # If shots on the current turn are 3 or more, immediately end the turn.
        if self.shots > 2:
            self.brains = 0
            return self.end_turn()
        return self.to_form()

    # a player can either be forced to end their turn, or choose to do so
    def end_turn(self):
        """Ends the current turn, then tells the game to start a new turn."""

        self.turn_over = True
        self.put()
        self.game.get().end_turn(self)
        return self.to_form()

class Score(ndb.Model):
    """Score object"""
    date = ndb.DateProperty(required=True)
    winner = ndb.KeyProperty(required=True)
    losers = ndb.KeyProperty(repeated=True)

    def to_form(self):
        return ScoreForm(date=str(self.date),
                         winner=self.winner.get().name,
                         losers=self.losers.get().name)
                         
class TurnForm(messages.Message):
    """Used to report turn status"""
    player = messages.StringField(1, required=True)
    game = messages.StringField(2, required=True)
    turn_key = messages.StringField(3, required=True)
    turn_over = messages.BooleanField(4, required=True)
    pool = messages.StringField(5, required=True)
    green_used = messages.IntegerField(6, required=True)
    yellow_used = messages.IntegerField(7, required=True)
    red_used = messages.IntegerField(8, required=True)
    brains = messages.IntegerField(9, required=True)
    shots = messages.IntegerField(10, required=True)


class TurnForms(messages.Message):
    """Return multiple TurnForms"""
    items = messages.MessageField(TurnForm, 1, repeated=True)


class TakeTurnForm(messages.Message):
    """Used to take a turn"""
    roll = messages.BooleanField(1, required=True)


class ScoreForm(messages.Message):
    """ScoreForm for outbound Score information"""
    date = messages.StringField(1, required=True)
    winner = messages.StringField(2, required=True)
    losers = messages.StringField(3, required=True)


class ScoreForms(messages.Message):
    """Return multiple ScoreForms"""
    items = messages.MessageField(ScoreForm, 1, repeated=True)


class GameForm(messages.Message):
    """GameForm for outbound game state information"""
    urlsafe_key = messages.StringField(1, required=True)
    status = messages.StringField(2, required=True)
    next_turn = messages.StringField(3, required=True)
    final_player = messages.StringField(4, default="None")
    game_over = messages.BooleanField(5, required=True)
    winner = messages.StringField(7)
    players = messages.StringField(8)
    next_turn_key = messages.StringField(9, required=True)


class GameForms(messages.Message):
    """Container for multiple Game Forms"""
    items = messages.MessageField(GameForm, 1, repeated=True)


class NewGameForm(messages.Message):
    """Used to create a new game."""
    players = messages.StringField(1, repeated=True)


class StringMessage(messages.Message):
    """StringMessage - Outbound single message"""
    message = messages.StringField(1, required=True)


class UserForm(messages.Message):
    """User Form"""
    name = messages.StringField(1, required=True)
    email = messages.StringField(2)
    scores = messages.StringField(3)
    wins = messages.IntegerField(4)
    total_played = messages.IntegerField(5, required=True)
    win_percentage = messages.FloatField(6, required=True)


class UserForms(messages.Message):
    """Container for multiple User Forms"""
    items = messages.MessageField(UserForm, 1, repeated=True)
