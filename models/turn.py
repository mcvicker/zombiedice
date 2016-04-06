"""turn.py - turn-related class definitions for the Zombie Dice game."""
import random
from protorpc import messages
from google.appengine.ext import ndb

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