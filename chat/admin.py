from django.contrib import admin
from chat.models import *

admin.site.register(Room)
admin.site.register(Player)
admin.site.register(Game)
admin.site.register(Hand)
admin.site.register(Bid)
admin.site.register(HandEntry)
admin.site.register(Message)
