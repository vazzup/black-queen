import re
import json
import logging
from channels import Group, Channel
from channels.sessions import channel_session
from .models import Room

log = logging.getLogger(__name__)

@channel_session
def ws_connect(message):
    # Extract the room from the message. This expects message.path to be of the
    # form /chat/{label}/, and finds a Room if the message path is applicable,
    # and if the Room exists. Otherwise, bails (meaning this is a some othersort
    # of websocket). So, this is effectively a version of _get_object_or_404.
    try:
        prefix, label = message['path']..strip('/').split('/')
        if prefix != 'chat':
            log.debug('invalid ws path=%s', message['path'])
            return
        room = Room.objects.get(label=label)
    except ValueError:
        log.debug('invalid ws path=%s', message['path'])
        return
    except Room.DoesNotExist:
        log.debug('ws room does not exist label=%s', label)
        return

    log.debug('chat connect room=%s client=%s:%s',
        room.label, message['client'][0], message['client'][1])

    # Need to be explicit about the channel layer so that testability works
    # This may be a FIXME?
    Group('chat-'+label, channel_layer=message.channel_layer).add(message.reply_channel)

    message.channel_session['room'] = room.label


def sorter(cards):
    card_list = []
    for card in cards:
        card_list.append((card%4, card//4, card))
    card_list.sort()
    return [card[2] for card in card_list]


@channel_session
def ws_receive(message):
    # Look up the room from the channel session, bailing if it doesn't exist
    try:
        label = message.channel_session['room']
        room = Room.objects.get(label=label)
    except KeyError:
        log.debug('no room in channel_session')
        return
    except Room.DoesNotExist:
        log.debug('recieved message, but room does not exist label=%s', label)
        return

    # Parse out a chat message from the content text, bailing if it doesn't
    # conform to the expected message format.
    try:
        data = json.loads(message['text'])
    except ValueError:
        log.debug("ws message isn't json text=%s", text)
        return

    if data:
        log.debug('chat message room=%s handle=%s type=%s data=%s',
            room.label, data['handle'], data['type'], str(data))
        if data['type'] == 'bid':
            player_bidding = room.players.filter(handle=data['handle']).last()
            game = room.games.filter(active=True).last()
            if game.next_to_bid == player_bidding:
                if data['value'] == '0':
                    new_bid = game.bids.create(player=player_bidding, value=0)
                else:
                    game.current_bid = game.current_bid + 5
                    new_bid = game.bids.create(player=player_bidding, value=game.current_bid)

                bidder_index = 0
                start_index = None
                for player in room.players.all():
                    if player.handle == player_bidding.handle:
                        start_index = bidder_index
                        break
                    bidder_index += 1
                # from players of the room find next after index
                next_player = None
                next_players = []
                for player in room.players.all()[start_index+1:room.players.count()]:
                    if len(game.bids.filter(player=player)) == 0 or game.bids.filter(player=player).last().value > 0:
                        next_players.append(player)
                if next_player == None:
                    for player in room.players.all()[0:start_index+1]:
                        if len(game.bids.filter(player=player)) == 0 or game.bids.filter(player=player).last().value > 0:
                            next_players.append(player)
                next_player = next_players[0]
                if len(next_players) > 1 or (next_player and data['value']=='5'):
                    game.next_to_bid = next_player
                    game.save()
                    bid = {}
                    bid['next'] = next_player.handle
                    bid['handle'] = data['handle']
                    bid['value'] = new_bid.value
                    bid['type'] = 'bid'
                    Group('chat-'+label, channel_layer=message.channel_layer).send({'text': json.dumps(bid)})
                else:
                    game.save()
                    winner = None
                    for player in room.players.all():
                        if game.bids.filter(player=player).last().value > 0:
                            winner = player
                            break

                    # nextplayer size must be 1
                    # bid is over, confirm that this is indeed true
                    # send message out to start game
                    bid = {}
                    bid['next'] = next_player.handle
                    bid['handle'] = data['handle']
                    bid['value'] = new_bid.value
                    bid['type'] = 'bid'
                    Group('chat-'+label, channel_layer=message.channel_layer).send({'text': json.dumps(bid)})
                    m = room.messages.create(handle='blackqueen', message=winner.handle +' has won the bid. Waiting on deciding partners and hakkam.')
                    Group('chat-'+label, channel_layer=message.channel_layer).send({'text': json.dumps(m.as_dict())})
            else:
                Group('chat-'+label+'player-'+data['handle'], channel_layer=message.channel_layer).add(message.reply_channel)
                Group('chat-'+label+'player-'+data['handle'], channel_layer=message.channel_layer).send({'text': json.dumps({'type': 'alert', 'message': 'Not your turn to bid'})})
                Group('chat-'+label+'player-'+data['handle'], channel_layer=message.channel_layer).discard(message.reply_channel)




        if data['type'] == 'start':
            log.debug('room players' + str(room.players.count()))
            if (room.players.count() == 5 or room.players.count() == 7) and not room.locked:
                room.owner = data['handle']
                room.locked = True
                room.save()
                Group('chat-'+label, channel_layer=message.channel_layer).send({'text': json.dumps(room.as_dict())})
                m = room.messages.create(handle='blackqueen', message=data['handle'] + ' has locked the room. Do not refresh page now.')
                Group('chat-'+label, channel_layer=message.channel_layer).send({'text': json.dumps(m.as_dict())})
                cards = {}
                cards['type'] = 'collect'
                per_person = None
                all_cards = None
                if room.players.count() == 5:
                    all_cards = list(range(40)) + list(range(40))
                    per_person = 16
                elif room.players.count() == 7:
                    all_cards = list(range(49)) + list(range(49))
                    per_person = 14
                import random
                random.shuffle(all_cards)
                player_idx = 0
                for player in room.players.all():
                    cards[player.handle] = sorter(all_cards[player_idx*per_person:(player_idx*per_person)+per_person])
                    player_idx += 1
                game = room.games.create()
                start_index = room.games.count() % room.players.count()
                start_player = room.players.all()[start_index]
                game.bids.create(player=start_player, value=150)
                # from players of the room find next after index
                next_player = None
                for player in room.players.all()[start_index+1:room.players.count()]:
                    if len(game.bids.filter(player=player)) == 0 or game.bids.filter(player=player).last().value > 0:
                        next_player = player
                        break
                if next_player == None:
                    for player in room.players.all()[0:start_index+1]:
                        if len(game.bids.filter(player=player)) == 0 or game.bids.filter(player=player).last().value > 0:
                            next_player = player
                            break
                game.next_to_bid = next_player
                game.minimum = start_player
                game.save()
                cards['start'] = start_player.handle
                cards['next'] = next_player.handle
                cards['dealer'] = room.players.all()[(start_index+room.players.count()-1)%room.players.count()].handle
                Group('chat-'+label, channel_layer=message.channel_layer).send({'text': json.dumps(cards)})
            else:
                Group('chat-'+label+'player-'+data['handle'], channel_layer=message.channel_layer).add(message.reply_channel)
                Group('chat-'+label+'player-'+data['handle'], channel_layer=message.channel_layer).send({'text': json.dumps(room.as_dict())})
                Group('chat-'+label+'player-'+data['handle'], channel_layer=message.channel_layer).discard(message.reply_channel)
        if data['type'] == 'join':
            names = []
            for player in room.players.all():
                names.append(player.handle)
            if data['handle'] not in names:
                p = room.players.create(handle=data['handle'])
                Group('chat-'+label, channel_layer=message.channel_layer).send({'text': json.dumps(p.as_dict())})
                m = room.messages.create(handle='blackqueen', message=data['handle'] + ' just joined the game.')
                Group('chat-'+label, channel_layer=message.channel_layer).send({'text': json.dumps(m.as_dict())})
            else:
                Group('chat-'+label+'player-'+data['handle'], channel_layer=message.channel_layer).add(message.reply_channel)
                Group('chat-'+label+'player-'+data['handle'], channel_layer=message.channel_layer).send({'text': json.dumps({'type': 'alert', 'message': 'handle already used in room, please choose another'})})
                Group('chat-'+label+'player-'+data['handle'], channel_layer=message.channel_layer).discard(message.reply_channel)
        if data['type'] == 'dm':
            m = room.messages.create(handle=data['handle'], message=data['message'])
            Group('chat-'+label, channel_layer=message.channel_layer).send({'text': json.dumps(m.as_dict())})
        if data['type'] == 'beat':
            Group('chat-'+label+'player-'+data['handle'], channel_layer=message.channel_layer).add(message.reply_channel)
            Group('chat-'+label+'player-'+data['handle'], channel_layer=message.channel_layer).send({'text': json.dumps({'ping': 'pong'})})
            Group('chat-'+label+'player-'+data['handle'], channel_layer=message.channel_layer).discard(message.reply_channel)

@channel_session
def ws_disconnect(message):
    try:
        label = message.channel_session['room']
        room = Room.objects.get(label=label)
        Group('chat-'+label, channel_layer=message.channel_layer).discard(message.reply_channel)
    except (KeyError, Room.DoesNotExist):
        pass
