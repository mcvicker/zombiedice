# Zombie Dice

Zombie Dice is a multiplayer game: the goal is to accumulate as many brains as possible without dying.
[Read More](http://www.sjgames.com/dice/zombiedice/img/ZDRules_English.pdf)

## Implementation

Zombie Dice has been implemented as a Google Cloud Endpoints API. 

## Set-Up Instructions:
1.  Update the value of application in app.yaml to the app ID you have registered
 in the App Engine admin console and would like to use to host your instance of this sample.
1.  Run the app with the devserver using dev_appserver.py DIR, and ensure it's
 running by visiting the API Explorer - by default localhost:8080/_ah/api/explorer.
1.  (Optional) Generate your client library(ies) with the endpoints tool.
 Deploy your application.

## Game Description
Zombie Dice is a multiplayer 'press your luck' dice game: the goal is to accumulate as many brains each turn without dying from shotgun blasts.
[Read More](http://www.sjgames.com/dice/zombiedice/img/ZDRules_English.pdf)

Many different Zombie Dice games can be played by many different Users at any given time. Each game can be retrieved or played by using the path parameter
`urlsafe_game_key`.

## Files Included:
 - api.py: Contains endpoints and game playing logic.
 - app.yaml: App configuration.
 - cron.yaml: Cronjob configuration.
 - main.py: Handler for taskqueue handler.
 - models.py: Entity and message definitions including helper methods.
 - utils.py: Helper function for retrieving ndb.Models by urlsafe Key string.
 
 ## Endpoints Included:
 - **create_user**
    - Path: 'user'
    - Method: POST
    - Parameters: user_name, email (optional)
    - Returns: Message confirming creation of the User.
    - Description: Creates a new User. user_name provided must be unique. Will 
    raise a ConflictException if a User with that user_name already exists.
   
 - **get_users**
    - Path: 'users'
    - Method: GET
    - Parameters: none
    - Returns: All users registered for the API.
 
 - **get_user_rankings**
    - Path: 'user/ranking'
    - Method: GET
    - Parameters: none
    - Returns: All users who have played at least one game, sorted by win percentage.
 
 - **new_game**
    - Path: 'game'
    - Method: POST
    - Parameters: user_names
    - Returns: GameForm with initial game state.
    - Description: Creates a new Game. user_names provided must correspond to an
    existing user - will raise a NotFoundException if not. 
     
 - **get_game**
    - Path: 'game/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameForm with current game state.
    - Description: Returns the current state of a game.
 
 - **cancel_game**
    - Path: 'game/{urlsafe_game_key}'
    - Method: DELETE
    - Parameters: urlsafe_game_key
    - Returns: Message
    - Description: Deletes the given game along with all associated turns. Returns either a success message or an error.
    
 - **take_turn**
    - Path: 'game/{urlsafe_turn_key}'
    - Method: PUT
    - Parameters: urlsafe_turn_key, roll
    - Returns: TurnForm with new turn state.
    - Description: Accepts a roll flag and returns the updated state of the turn.
    If this causes a turn to end, a new turn will be created. Use get_game to see the new turn. 
    
 - **get_user_games**
    - Path: 'user/games/{urlsafe_user_key}'
    - Method: GET
    - Parameters: urlsafe_user_key
    - Returns: GameForms
    - Description: Returns all games that the given user has played or is playing.
 
- **get_game_history**
    - Path: 'game/history/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: TurnForms
    - Description: Returns all turns that belong to a given game.

##Models Included:
 - **User**
    - Stores unique user_name and (optional) email address.
    
 - **Game**
    - Stores unique game states. Associated with User model via KeyProperty.

 - **Turn**
    - Stores unique turn states. Associated with User model via KeyProperty. A specific game will be the ancestor of many turns.
    
 - **Score**
    - Records completed games. Associated with Users model via KeyProperty.
    
##Forms Included:
 - **GameForm**
    - Representation of a Game's state (urlsafe_key, status (the players and the brains they have accumulated),
    next_turn player, final_player, game_over flag, winner, players, next_turn_key).
- **GameForms**
    - Multiple GameForm container.
 - **NewGameForm**
    - Used to create a new game (user_names)
 - **TakeTurnForm**
    - Inbound take turn form (roll flag).
  - **TurnForm**
    - Representation of a Turn's state (player, game, turn_key, turn_over flag, pool, green_used, yellow_used, red_used, brains, shots) 
- **TurnForms**
    - Multiple TurnForm container.
 - **ScoreForm**
    - Representation of a completed game's Score (date, winner, losers).
 - **ScoreForms**
    - Multiple ScoreForm container.
 - **StringMessage**
    - General purpose String container.
 - **UserForm**
    - Representation of a user. (name, email, scores, wins, total_played, win_percentage)
- **UserForms**
    - Multiple UserForm container.    
    