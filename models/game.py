"""game.py - game-related class definitions for the Zombie Dice game."""

from datetime import date
from protorpc import messages
from google.appengine.ext import ndb
from .turn import Turn # game logic needs to be able to create turns

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
                game.players.append(player)
                # sets the next_turn to the first player in the list of players
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