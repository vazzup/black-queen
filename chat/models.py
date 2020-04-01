from __future__ import unicode_literals

from django.db import models
from django.utils import timezone

class Room(models.Model):
    name = models.TextField()
    label = models.SlugField(unique=True)
    locked = models.BooleanField(default=False)

    def __unicode__(self):
        return self.label

    def as_dict(self):
        return {'name': self.name, 'type': 'room', 'locked': self.locked, 'label': self.label}

class Player(models.Model):
    room = models.ForeignKey(Room, related_name='players')
    handle = models.TextField()

    def __unicode__(self):
        return self.room.name + '-' + self.handle

    def as_dict(self):
        return {'handle': self.handle, 'type': 'player'}

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
