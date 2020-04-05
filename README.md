# Black Queen

Simple webapp for Indian card game Black Queen using django-channels(websockets)

Requirements : Redis, Postgres

Game Rules

The game is played among 5 or 7 players with 2 standard decks of cards excluding some 2s for equal cards to each player.


Some cards are assigned points, as follows:-
    
All aces: 15 points each

All tens: 10 points each

All fives: 5 points each

Queen of Spades: 30 points

These sum up to 150 for one deck, hence, 300 for two.
The game begins with a bidding round - each player bids the amount of points that his 
team (not yet decided) can make, without consulting others.
Bidding starts at 150 points and ends when all but one player has passed on.

The highest bidder then decides the trump and announces (one if 5 players else two cards) from the entire deck -
players with these cards belong to his team, and are called his "partners".
They don't reveal themselves as partners though. If both the cards belong to the same player, 
he is a double partner.
The highest bidder can also announce cards from his own stack as well.
The game then proceeds like any other trick taking game, 
but everyone keeps track of the number of points in the trick as well.
One has to cleverly decide when to contribute points to the current trick and when not to, 
based on their guess of the partners.



At the end of the game, if the bidding team achieves the points they bid or more, 
all of them get a score of the points they bid, and negative points if they loose.


This whole process is called a round, and the game can be played for a fixed number of rounds, 
and the person with the highest total score wins at the end.
