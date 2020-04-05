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
        prefix, label = message['path'].strip('/').split('/')
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
    message.reply_channel.send({'text': json.dumps({'ping' : 'pong'})})

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
        if data['type'] == 'play':
            player = room.players.filter(handle=data['handle']).last()
            game = room.games.filter(active=True).last()
            card = int(data['value'])
            suit = card % 4
            value = card // 4
            hand = game.hands.filter(active=True).last()
            valid_to_play = True
            hand_end = False
            game_end = False
            og_cards = json.loads(game.cards)
            if hand.entries.count() == 0:
                hand.entries.create(player=player, card_played=card)
                hand.first_suit = suit
                hand.save()
            else:
                player_initial = og_cards[player.handle]
                player_played = []
                if game.hands.filter(active=False).count() > 0:
                    player_played = [handd.entries.filter(player=player).last().card_played for handd in game.hands.filter(active=False)]
                player_now = player_initial[:]
                for cardd in player_played:
                    player_now.remove(cardd)
                if card not in player_now:
                    valid_to_play = False
                else:
                    player_now_suit = set([i%4 for i in player_now])
                    if hand.first_suit != suit and hand.first_suit in player_now_suit:
                        valid_to_play = False
                    else:
                        hand.entries.create(player=player, card_played=card)
                        if hand.entries.count() == room.players.count():
                            # last play of hand, mark hand nonactive
                            hand.active = False
                            hand.save()
                            hand_end = True
                            if ((game.hands.count() == 16) and (room.players.count()==5)) or ((game.hands.count()==14) and (room.players.count()==7)):
                                game_end = True
                                game.active = False
                                game.save()
                            # check if last play of game
                            # prompt game end
                            # start new hand if not
            if valid_to_play:
                # send everyone the played card
                # entry already made
                last_entry = hand.entries.all().last()
                # update partners
                if not game.partner1 and card == game.partner1card:
                    game.partner1 = player
                    game.save()
                if room.players.count() == 7 and not game.partner2 and card == game.partner2card:
                    game.partner2 = player
                    game.save()
                play = {}
                play['type'] = 'play'
                play['clear_cards'] = False
                if hand.entries.count() == 1:
                    play['clear_cards'] = True
                play['success'] = True
                play['message'] = str(True)
                play['value'] = card
                play['player'] = player.handle
                play['points'] = last_entry.get_points()
                play['next'] = [playerr.handle for idx, playerr in enumerate(room.players.all()) if room.players.all()[(idx + room.players.count() - 1) % room.players.count()].handle == player.handle][0]
                play['new_hand'] = False
                if hand_end:
                    play['new_hand'] = True
                    # send everyone updated points
                    # create new hand too
                    best_card = 101 + game.hakkam
                    winner, points, points_cards = hand.compute_winner()
                    play['winner'] = winner.handle
                    play['next'] = winner.handle
                    play['winner_points'] = points
                    play['points_cards'] = points_cards
                    if not game_end:
                        game.hands.create()
                    else:
                        play['new_hand'] = False
                        play['game_end'] = True
                        play['owner'] = room.owner
                        # Get last game, compute game winner, and find points for each user
                        points_dict = {}
                        score = {}
                        for playerr in room.players.all():
                            points_dict[playerr.handle] = 0
                            score[playerr.handle] = 0
                        for handd in game.hands.all():
                            # find hand winner and point
                            winner, points, points_cards = handd.compute_winner()
                            points_dict[winner.handle] += points
                        # could optionally compute winner here and send it to all users
                        partners_lis = [game.bid_winner.handle , game.partner1.handle]
                        if room.players.count() == 7:
                            partners_lis += [game.partner2.handle]
                        partners = set(partners_lis)
                        e_points = 0
                        for partnerr in partners:
                            e_points += points_dict[partnerr]
                        play['winning_bid'] = game.winning_bid
                        play['partners_won'] = False

                        if e_points >= game.winning_bid:
                            play['partners_won'] = True
                            for partner in partners_lis:
                                score[partner] += game.winning_bid
                        else:
                            for playerr in room.players.all():
                                if playerr.handle not in partners:
                                    score[pplayerr.handle] += game.winning_bid
                            for partnerr in partners:
                                if partners.count(partnerr) > 1:
                                    score[partnerr] -= game.winning_bid
                        play['scores'] = score
                        play['partners'] = list(partners)

                Group('chat-'+label, channel_layer=message.channel_layer).send({'text': json.dumps(play)})

            else:
                play = {}
                play['type'] = 'play'
                play['success'] = False
                play['message'] = "Illegal card played."
                play['next'] = player.handle
                message.reply_channel.send({'text': json.dumps(play)})


        if data['type'] == 'select_partner':
            player_selecting = room.players.filter(handle=data['handle']).last()
            game = room.games.filter(active=True).last()
            # mark the partners and shiz and then tell everyone the partners and shiz
            hakkam = int(data['hakkam'])
            game.hakkam = hakkam
            partner1value = int(data['partner1value'])
            partner1suit = int(data['partner1suit'])
            if room.players.count() == 7:
                partner2value = int(data['partner2value'])
                partner2suit = int(data['partner2suit'])
                game.partner2card = (partner2value * 4) + partner2suit
            game.partner1card = (partner1value * 4) + partner1suit
            game.save()
            # Time for the first hand of the game
            game.hands.create()
            partners = {}
            partners['type'] = 'partners'
            partners['hakkam'] = ["spades", "diams", "clubs", "hearts"][hakkam]
            partners['value'] = game.winning_bid
            partners['next'] = player_selecting.handle
            partners['partner1value'] = ["A", "K", "Q"][partner1value]
            partners['partner1suit'] = ["spades", "diams", "clubs", "hearts"][partner1suit]
            if room.players.count() == 7:
                partners['partner2value'] = ["A", "K", "Q"][partner2value]
                partners['partner2suit'] = ["spades", "diams", "clubs", "hearts"][partner2suit]
            Group('chat-'+label, channel_layer=message.channel_layer).send({'text': json.dumps(partners)})


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
                    game.winning_bid = game.current_bid
                    game.bid_winner = winner
                    game.save()
                    bid = {}
                    bid['next'] = next_player.handle
                    bid['handle'] = data['handle']
                    bid['value'] = game.current_bid
                    bid['type'] = 'bid'
                    bid['winner'] = winner.handle
                    if room.players.count() == 5:
                        bid['partners'] = 1
                    else:
                        bid['partners'] = 2
                    Group('chat-'+label, channel_layer=message.channel_layer).send({'text': json.dumps(bid)})
                    m = room.messages.create(handle='blackqueen', message=winner.handle +' has won the bid. Waiting on deciding partners and hakkam.')
                    Group('chat-'+label, channel_layer=message.channel_layer).send({'text': json.dumps(m.as_dict())})
            else:
                message.reply_channel.send({'text': json.dumps({'type': 'alert', 'message': 'Not your turn to bid'})})




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
                game = room.games.create(cards=json.dumps(cards))
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
                message.reply_channel.send({'text': json.dumps(room.as_dict())})
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
                message.reply_channel.send({'text': json.dumps({'type': 'alert', 'message': 'handle already used in room, please choose another'})})
        if data['type'] == 'dm':
            m = room.messages.create(handle=data['handle'], message=data['message'])
            Group('chat-'+label, channel_layer=message.channel_layer).send({'text': json.dumps(m.as_dict())})
        if data['type'] == 'beat':
            message.reply_channel.send({'text': json.dumps({'ping': 'pong'})})

@channel_session
def ws_disconnect(message):
    try:
        label = message.channel_session['room']
        room = Room.objects.get(label=label)
        Group('chat-'+label, channel_layer=message.channel_layer).discard(message.reply_channel)
    except (KeyError, Room.DoesNotExist):
        pass
