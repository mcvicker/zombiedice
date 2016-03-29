"""Zombie Dice API implemented using Google Cloud Endpoints.

Contains declarations of endpoint, endpoint methods,
as well as the ProtoPRC message class and container required
for endpoint method definition.
"""

import endpoints
from protorpc import messages
from protorpc import message_types
from protorpc import remote

from models import User, UserForms, GameForm, GameForms, NewGameForm
from models import Game, Turn, TurnForm, TakeTurnForm, TurnForms, StringMessage

from utils import get_by_urlsafe

__author__ = "danielmcvicker@gmail.com (Daniel McVicker)"

NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
USER_REQUEST = endpoints.ResourceContainer(user_name=messages.StringField(1),
                                           email=messages.StringField(2))
GET_GAME_REQUEST = endpoints.ResourceContainer(
    urlsafe_game_key=messages.StringField(1),)
TAKE_TURN_REQUEST = endpoints.ResourceContainer(
    TakeTurnForm,
    urlsafe_turn_key=messages.StringField(1))
USER_GAMES_REQUEST = endpoints.ResourceContainer(
    urlsafe_user_key=messages.StringField(1),)
CANCEL_GAME_REQUEST = endpoints.ResourceContainer(
    urlsafe_game_key=messages.StringField(1),)
GAME_HISTORY_REQUEST = endpoints.ResourceContainer(
    urlsafe_game_key=messages.StringField(1),)


@endpoints.api(name='zombiedice', version='v0.1')
class ZombieDiceApi(remote.Service):
    """Game API for the Zombie Dice game"""

    @endpoints.method(message_types.VoidMessage, UserForms,
                      path="users", http_method='GET', name="get_users")
    def get_users(self, request):
        """This returns all users"""
        users = User.query().fetch()
        return UserForms(items=[user.to_form() for user in users])

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=StringMessage,
                      path='user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Create a User with a unique username."""
        if User.query(User.name == request.user_name).get():
            raise endpoints.ConflictException(
                'A User with that name already exists.')
        user = User(name=request.user_name, email=request.email)
        user.put()
        return StringMessage(message='User {} created!'.format(
            request.user_name))

    @endpoints.method(response_message=UserForms,
                      path='user/ranking',
                      name='get_user_rankings',
                      http_method='GET')
    def get_user_rankings(self, request):
        """Return all Users, sorted by win percentage"""
        users = User.query(User.total_played > 0).fetch()
        users = sorted(users, key=lambda x: x.win_percentage, reverse=True)
        return UserForms(items=[user.to_form() for user in users])

    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        """Creates new game"""
        players = []
        for player in request.players:
            # get the full user data for the player
            user = User.query(User.name == player).get()
            if not user:
                raise endpoints.NotFoundException(
                    'One or more of those usernames does not exist!')
            # append the key to the list of players
            players.append(user.key)

        game = Game.new_game(players)

        return game.to_form()

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Return the current game state."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            return game.to_form()
        else:
            raise endpointsNotFoundException('Game not found!')

    @endpoints.method(request_message=TAKE_TURN_REQUEST,
                      response_message=TurnForm,
                      path='turn/{urlsafe_turn_key}',
                      name='take_turn',
                      http_method='PUT')
    def take_turn(self, request):
        """Takes a turn. Returns the turn state with message."""
        turn = get_by_urlsafe(request.urlsafe_turn_key, Turn)
        if not turn:
            raise endpoints.NotFoundException('Turn not found')
        if turn.turn_over:
            raise endpoints.BadRequestException('This turn is over!')

        if request.roll:
            return turn.take_turn()
        else:
            turn.end_turn()

            return turn.to_form()

    @endpoints.method(request_message=USER_GAMES_REQUEST,
                      response_message=GameForms,
                      path='user/games/{urlsafe_user_key}',
                      name='get_user_games',
                      http_method='GET')
    def get_user_games(self, request):
        """Return all Games the user has played or is playing. """
        player = get_by_urlsafe(request.urlsafe_user_key, User)
        games = Game.query(Game.players == player.key)
        return GameForms(items=[game.to_form() for game in games])

    @endpoints.method(request_message=CANCEL_GAME_REQUEST,
                      response_message=StringMessage,
                      path='game/{urlsafe_game_key}',
                      name='cancel_game',
                      http_method='DELETE')
    def cancel_game(self, request):
        """Delete a game in progress. Games that are over cannot be deleted."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game and not game.game_over:
            # first delete all child turns
            turns = Turn.query(ancestor=game.key).fetch()
            for turn in turns:
                turn.key.delete()
            game.key.delete()
            return StringMessage(message='Game with key: {} deleted.'.
                                 format(request.urlsafe_game_key))
        elif game and game.game_over:
            raise endpoints.BadRequestException('Game is already over!')
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=GAME_HISTORY_REQUEST,
                      response_message=TurnForms,
                      path='game/history/{urlsafe_game_key}',
                      name='get_game_history',
                      http_method='GET')
    def get_game_history(self, request):
        """Return all Turns for a given game. """
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        turns = Turn.query(ancestor=game.key).fetch()
        return TurnForms(items=[turn.to_form() for turn in turns])


APPLICATION = endpoints.api_server([ZombieDiceApi])
