$(function() {
    // When we're using HTTPS, use WSS too.
    var ws_scheme = window.location.protocol == "https:" ? "wss" : "ws";
    var chatsock = new ReconnectingWebSocket(ws_scheme + '://' + window.location.host + "/chat" + window.location.pathname);
    window.onbeforeunload = function() {
		return "Leaving this page will end your ongoing game for everyone.";
	};

    chatsock.onmessage = function(message) {
        var data = JSON.parse(message.data);
        console.log(data);
        if (data.type == 'alert'){
            alert(data.message)
        }
        if (data.type == 'dm'){
            var chat = $("#chat")
            var ele = $('<tr></tr>')

            ele.append(
                $("<td></td>").text(data.handle)
            )
            ele.append(
                $("<td></td>").text(data.message)
            )

            chat.append(ele)
        }
        if(data.type == 'player'){
            var players = $("#players")
            var ele = $('<tr></tr>')
            ele.append(
                $("<td></td>").text(data.handle)
            )
            players.append(ele)
            var bids = $("#bids_table")
            var elebid = $('<tr></tr>')
            elebid.append(
                $("<td></td>").text(data.handle)
            )
            elebid.append(
                $("<td id='bid-" + data.handle + "'></td>").text("")
            )
            bids.append(elebid)
            if(data.handle == $('#handle').val()){
                $("#join").attr("disabled","disabled");
            }
        }
        if(data.type == 'room'){
           if(data.locked){
               alert("Room has been locked")
           }
            else{
                alert("You need 5 or 7 players to start the game")
            }
        }
        if(data.type == 'play'){
           $(".table").children().unbind('click');
           if(data.success){
               $("#status").attr('hidden', true);
               if($('#handle').val() == data['player']){
                   // congrats you just got played
                    $('ul.table li.bqcard[value="' + data.value + '"]').first().remove();
               }
               // show that player played value card in the table
               if(data.clear_cards){
                    $('#played_cards ul').empty();
               }
               var card_val = data['value']
               var card_rank = Math.floor(card_val/4);
               var card_suit = card_val%4;
               var card_rank_string = ['a', 'k', 'q', 'j', '10', '9', '8', '7', '6', '5', '4', '3', '2'][card_rank]
               var card_suit_string = ['spades', 'diams', 'clubs','hearts'][card_suit]


               if('winner' in  data){
                    // We need to update the points table below
                   //winner row needs to be appended with point cards in column2 and sum column3 with points
                   //
                   var existing_points = parseInt($('#points_total_'+data['winner']).html())
                   existing_points += data.winner_points
                   $('#points_total_'+data['winner']).html(existing_points.toString());
                    for (index = 0; index < data.points_cards.length; index++) {
                       var pcard = data.points_cards[index];
                       var pcard_rank = Math.floor(pcard/4);
                       var pcard_suit = pcard%4;
                       var pcard_rank_string = ['a', 'k', 'q', 'j', '10', '9', '8', '7', '6', '5', '4', '3', '2'][pcard_rank]
                       var pcard_suit_string = ['spades', 'diams', 'clubs','hearts'][pcard_suit]

                       var ele = $('<li class="bqpointcard"><a class="card rank-'+pcard_rank_string+' '+pcard_suit_string+'"><span class="rank">'+pcard_rank_string.toUpperCase()+'</span><span class="suit">&'+pcard_suit_string+';</span></a></li>');
                        $('#points_'+data.winner).append(ele);
                    }

               }
               var ele = $('<div style="display: inline-block;padding-right: 10px;"><li class="bqplayedcard"><a class="card rank-'+card_rank_string+' '+card_suit_string+'"><span class="rank">'+card_rank_string.toUpperCase()+'</span><span class="suit">&'+card_suit_string+';</span></a></li><label style="font-size: 0.8em;"> '+data['player']+' </label></div>')
               $('#played_cards ul').append(ele);
           }
           else{
               alert(data.message);
           }
           if($('#handle').val() == data['next']){
               // congrats you're next
                $('#status').attr('hidden', false)
                $('#status').html('Your Turn, Please select card to play')
           }
            // TODO Add scorecard printing mantain this round scores until end.
            if('game_end' in data){
                $('#final').attr('hidden', false);
                $("#players tbody tr td").each(function() {
                    var player_name = $(this).html();
                    var elem = $('<tr> <td> '+player_name+' </td> <td> ' + data.scores[player_name] + '</td> </tr>');
                    $('#final').append(elem);

                });
                if(data.partners_won){
                    $('#bids_header').html('Game Over. Partners Won.');
                }
                else{
                    $('#bids_header').html('Game Over. Non-Partners Won.');
                }
                $('#status').html('Current Room Scores are :');
                if('#handle').val() == data.owner){
                    $('#new_game').attr('hidden', false)
                }
            }
        }
        if(data.type == 'collect'){
            // we need to collect our own cards by making a websocket call
            //hide some elements while at it
            //
            $('#players').attr('hidden', true);
            $('#newgame').attr('hidden', true);
			$("#players tbody tr td").each(function() {
			  // Within tr we find the last td child element and get content
				var player_name = $(this).html();
                $('#bid-'+player_name).html('');
            });
            $('#status').attr('hidden', true);
            $('#joingame').attr('hidden', true);
            $('#toppart').attr('hidden', true);
            $('#namediv').attr('hidden', true);
            $('#bids_header').attr('hidden', false);
            $('#cards_header').attr('hidden', false);
            $('#bids_table').attr('hidden', false);
            $('#bid-'+data['start']).html('150 (Minimum)');
            $('#bid-'+data['next']).html('(*)');
            // When you collect your cards
            // Clear the points table
            $('#points_table tbody').empty();
            $('#points_table').attr('hidden', false);
            $('#played_cards').attr('hidden', false);
            // Populate new rows for points table
			$("#players tbody tr td").each(function() {
			  // Within tr we find the last td child element and get content
				var player_name = $(this).html();
				var player_points = 0;
				var ele = $('<tr><td>'+player_name+'</td><td><div class="playingCards simpleCards inText" style="display:table;"><ul class="table" id="points_'+player_name+'"></ul></div></td><td id="points_total_'+player_name+'">0</td></tr>');
				$('#points_table').append(ele);
			});
            var cards = $("#hand")
            var mycards = data[$('#handle').val()]
            for (var i = 0; i < mycards.length; i++) {
                var card_val = mycards[i]
                var card_rank = Math.floor(card_val/4);
                var card_suit = card_val%4;
                if(card_rank == 0){
                    card_rank = 'a';
                }
                else if(card_rank == 1){
                    card_rank = 'k';
                }
                else if(card_rank == 2){
                    card_rank = 'q';
                }
                else if(card_rank == 3){
                    card_rank = 'j';
                }
                else if(card_rank > 3){
                    card_rank = 10 - (card_rank - 4);
                    card_rank = card_rank.toString();
                }
                if(card_suit == 0){
                    card_suit = "spades";
                }
                else if(card_suit == 1){
                    card_suit = "diams";
                }
                else if(card_suit == 2){
                    card_suit = "clubs";
                }
                else if(card_suit == 3){
                    card_suit = "hearts";
                }
                var card = $('<li class="bqcard" value="'+card_val.toString()+'"><a class="card rank-' + card_rank + ' ' + card_suit +'"><span class="rank">' + card_rank.toUpperCase() + '</span><span class="suit">&' + card_suit + ';</span></a></li>');
                cards.append(card)
            }

            // Notify the next bidder to bid
            // enable bidding view
            // make methods for the same
			if($('#handle').val() == data['next']){
                $('#bidview').attr("hidden", false)
            }
        }
        if(data.type == 'bid'){
            //new bid in town, update handle with bid
            $('#bid-'+data['handle']).html(data['value']);
            //update next
            $('#bid-'+data['next']).append('(*)');
            //unblock view if next
			if($('#handle').val() == data['next']){
                $('#bidview').attr("hidden", false)
            }
            if('winner' in data){
                $('#bidview').attr("hidden", true)

                $('#bids_header').html(data['winner'] + ' : ' + data['value'] + ' points. Selecting partners and Hakkam.');
                $('#bids_table').attr('hidden', true);
            }
            if(('winner' in data) && (data['winner'] == $('#handle').val())){
                $('#partner_view').attr('hidden', false);
				if(data['partners'] == 1){
					$('#partner2').attr('hidden', true);
				}

            }
        }
        if(data.type == 'partners'){
            $('#bids_header').attr("hidden", false);
            $('#hakkam_header').attr("hidden", false);
            $('#hakkam_header').html('Hakkam : ' + '<span class="suit">&' + data['hakkam'] + ';</span>' + '. Partners : ' + '<a class="card rank-'+data['partner1value'].toLowerCase() + ' ' + data['partner1suit'] + '"><span class="rank">' + data['partner1value'] + '</span><span class="suit">&' + data['partner1suit'] + ';</span></a>');
            $('#bids_header').html(data['next'] + ' : ' + data['value'] + ' points.')
            if('partner2value' in data){
                $('hakkam_header').append($('<a class="card rank-'+data['partner2value'].toLowerCase() + ' ' + data['partner2suit'] + '"><span class="rank">' + data['partner2value'] + '</span><span class="suit">&' + data['partner2suit'] + ';</span></a>'))
            }
            if($('#handle').val() == data['next']){
                $('#status').attr('hidden', false)
                $('#status').html('Your Turn, Please select card to play')
                // Add onclick for card and send message
            }

        }
    };

    $('ul.table').on('click', 'li.bqcard',function(){
        if($('#handle').val() && !($('#status').is(":hidden"))){
            $('#bidview').attr("hidden", true)
            $("#handle").prop("readonly", true);
            var message = {
                handle: $('#handle').val(),
                type: 'play',
                value: $(this).attr('value'),
            }
            chatsock.send(JSON.stringify(message));
            // wait for confirmation to hide the status, disable clicking while no confirmation
            $(".table").children().bind('click', function(){ return false; });
        }
        else{
            alert("Please wait for your turn.");
        }
        return false;
    });

    $( "#pass" ).click(function() {
      if($('#handle').val()){
            $('#bidview').attr("hidden", true)
            $("#handle").prop("readonly", true);
            var message = {
                handle: $('#handle').val(),
                type: 'bid',
                value: '0',
            }
            chatsock.send(JSON.stringify(message));
        }
        else{
            alert("Please enter a handle.");
        }
        return false;
    });
    $( "#select_partner" ).click(function() {
      if($('#handle').val()){
            $('#partner_view').attr("hidden", true)
            var message = {
                handle: $('#handle').val(),
                type: 'select_partner',
                hakkam: $('#hakkam').val(),
                partner1value: $('#partner1value').val(),
                partner1suit: $('#partner1suit').val(),
                partner2value: $('#partner2value').val(),
                partner2suit: $('#partner2suit').val(),
            }
            chatsock.send(JSON.stringify(message));
        }
        else{
            alert("Please enter a handle.");
        }
        return false;
    });
    $("#bidview").on("submit", function(event) {
        if($('#handle').val()){
            $('#bidview').attr("hidden", true)
            $("#handle").prop("readonly", true);
            var message = {
                handle: $('#handle').val(),
                type: 'bid',
                value: '5',
            }
            chatsock.send(JSON.stringify(message));
        }
        else{
            alert("Please enter a handle.");
        }
        return false;
    });

    $("#chatform").on("submit", function(event) {
        if($('#handle').val() && $('#message').val()){
            $("#handle").prop("readonly", true);
            var message = {
                handle: $('#handle').val(),
                message: $('#message').val(),
                type: 'dm',
            }
            chatsock.send(JSON.stringify(message));
            $("#message").val('').focus();
        }
        else{
            alert("Please enter a handle and message.");
        }
        return false;
    });

    $("#startgame").on("submit", function(event) {
        if($('#handle').val()){
            $("#handle").prop("readonly", true);
            var message = {
                handle: $('#handle').val(),
                type: 'start',
            }
            chatsock.send(JSON.stringify(message));
        }
        else{
            alert("Please enter a handle.");
        }
        return false;
    });
    $("#newgame").on("submit", function(event) {
        if($('#handle').val()){
            $("#handle").prop("readonly", true);
            var message = {
                handle: $('#handle').val(),
                type: 'newgame',
            }
            chatsock.send(JSON.stringify(message));
        }
        else{
            alert("Please enter a handle.");
        }
        return false;
    });
    $("#joingame").on("submit", function(event) {
        if($('#handle').val() || ($('#handle').val().indexOf(' ')>=0)){
            $("#handle").prop("readonly", true);
            var message = {
                handle: $('#handle').val(),
                type: 'join',
            }
            chatsock.send(JSON.stringify(message));
        }
        else{
            alert("Please enter a handle without spaces.");
        }
        return false;
    });
	function heartbeat() {
		var message = {
			type: 'beat',
            handle: 'beat',
		}
		chatsock.send(JSON.stringify(message));
	}
	setInterval(heartbeat, 39999);

});
