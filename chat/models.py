from __future__ import unicode_literals

from django.db import models
from django.utils import timezone
from django.db.models import Q


class Room(models.Model):
    name = models.TextField()
    label = models.SlugField(unique=True)
    locked = models.BooleanField(default=False)
    owner = models.CharField(max_length=100, null=True, default=None)

    def __unicode__(self):
        return self.label

    def as_dict(self):
        return {'name': self.name, 'type': 'room', 'locked': self.locked, 'label': self.label}

class Player(models.Model):
    room = models.ForeignKey(Room, related_name='players')
    handle = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    def __unicode__(self):
        return self.room.name + '-' + self.handle

    def as_dict(self):
        return {'handle': self.handle, 'type': 'player'}

    class Meta:
        ordering = ["timestamp"]

class Game(models.Model):
    room = models.ForeignKey(Room, related_name='games')
    hakkam = models.IntegerField(default=5)
    current_bid = models.IntegerField(default=150)
    winning_bid = models.IntegerField(null=True, default=None)
    bid_winner = models.ForeignKey(Player, null=True, default=None)
    partner1 = models.ForeignKey(Player, null=True, default=None, related_name='games_partner1')
    partner2 = models.ForeignKey(Player, null=True, default=None, related_name='games_partner2')
    partner1card = models.IntegerField(null=True, default=None)
    partner2card = models.IntegerField(null=True, default=None)
    active = models.BooleanField(default=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    next_to_bid = models.ForeignKey(Player, null=True, default=None, related_name='games_next_to_bid')
    minimum = models.ForeignKey(Player, null=True, default=None, related_name='games_minimum')
    cards = models.TextField(null=True, default=None)


    def evaluate_bid(self):
        if self.bids.count() > self.room.players.count():
            bid_dict = {}
            for bid in self.bids.all():
                if bid.value == 0:
                     bid_dict.pop(bid.player.handle, None)
                else:
                    bid_dict[bid.player.handle] = bid.value, bid.player
            if len(bid_dict)==1:
                return True, bid_dict.values()[0][0], bid_dict.values()[0][1]
        return False, None, None


    class Meta:
        ordering = ["timestamp"]

class Bid(models.Model):
    game = models.ForeignKey(Game, related_name='bids')
    player = models.ForeignKey(Player)
    value = models.IntegerField() # 0 is pass
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["timestamp"]



class Hand(models.Model):
    game = models.ForeignKey(Game, related_name='hands')
    hand_winner = models.ForeignKey(Player, null=True, default=None)
    first_suit = models.IntegerField(null=True, default=None)
    active = models.BooleanField(default=True)
    points = models.IntegerField(null=True, default=None)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)


    def a_better_than_b(self, a, b):
        hakkam = self.game.hakkam
        first_suit = self.first_suit
        if b == -1:
            return 1
        suit_a = a%4
        val_a = a//4
        suit_b = b%4
        val_b = b//4
        if suit_a != first_suit and suit_a != hakkam:
            return -1
        if suit_a == hakkam and suit_b == hakkam:
            if val_a < val_b:
                return 1
            if val_a > val_b:
                return -1
            return 1
        elif suit_a == hakkam:
            return 1
        elif suit_b == hakkam:
            return -1
        else:
            if val_a < val_b:
                return 1
            if val_a > val_b:
                return -1
            return 1


    def get_points(self, a):
        val_a = a//4
        suit_a = a%4
        if val_a == 2 and suit_a == 0:
            return 30
        if val_a == 0:
            return 15
        if val_a == 4:
            return 10
        if val_a == 9:
            return 5
        return 0


    def compute_winner(self):
        if self.entries.count() == self.game.room.players.count():
            current_best = -1
            # ordering is AS, AD, AC, AH, KS, KD, ...
            hakkam = self.game.hakkam
            winner = None
            points = 0
            points_cards = []
            for entry in self.entries.all():
                ab = self.a_better_than_b(entry.card_played, current_best)
                if self.get_points(entry.card_played) > 0:
                    points_cards.append(entry.card_played)
                points += self.get_points(entry.card_played)
                if ab == 1:
                    current_best = entry.card_played
                    winner = entry.player
        return winner, points, points_cards


    class Meta:
        ordering = ["timestamp"]


class HandEntry(models.Model):
    hand = models.ForeignKey(Hand, related_name='entries')
    player = models.ForeignKey(Player, null=True, default=None)
    card_played = models.IntegerField()
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    def get_points(self):
        a = self.card_played
        val_a = a//4
        suit_a = a%4
        if val_a == 2 and suit_a == 0:
            return 30
        if val_a == 0:
            return 15
        if val_a == 4:
            return 10
        if val_a == 9:
            return 5

    def is_partner(self):
        if self.card_played == self.hand.game.partner1card and self.hand.game.partner1 == None:
            self.hand.game.partner1 = self.player
            self.hand.game.save()
            return True
        elif self.card_played == self.hand.game.partner2card and self.hand.game.partner2 == None:
            self.hand.game.partner2 = self.player
            self.hand.game.save()
            return True
        return False

    class Meta:
        ordering = ["timestamp"]


class Message(models.Model):
    room = models.ForeignKey(Room, related_name='messages')
    handle = models.TextField()
    message = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    def __unicode__(self):
        return '[{timestamp}] {handle}: {message}'.format(**self.as_dict())

    @property
    def formatted_timestamp(self):
        return self.timestamp.strftime('%b %-d %-I:%M %p')

    def as_dict(self):
        return {'handle': self.handle, 'message': self.message, 'timestamp': self.formatted_timestamp, 'type': 'dm'}
