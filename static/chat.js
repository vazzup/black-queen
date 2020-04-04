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
        if(data.type == 'collect'){
            // we need to collect our own cards by making a websocket call
            //hide some elements while at it
            //
            $('#players').hide();
            $('#joingame').hide();
            $('#toppart').hide();
            $('#bids_header').attr('hidden', false);
            $('#cards_header').attr('hidden', false);
            $('#bids_table').attr('hidden', false);
            $('#bid-'+data['start']).html('150 (Minimum)');
            $('#bid-'+data['next']).html('(*)');

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
            $('bids_header').attr("hidden", false);
            $('bids_header').html(data['next'] + ' : ' + data['value'] + ' points. Partners : ' + '<a class="card rank-'+data['partner1value'].toLowerCase() + ' ' + data['partner1suit'] + '"><span class="rank">' + data['partner1value'] + '</span><span class="suit">&' + data['player1suit'] + '</span></a>')
            if('partner2value' in data){
                $('bids_header').append($('<a class="card rank-'+data['partner1value'].toLowerCase() + ' ' + data['partner1suit'] + '"><span class="rank">' + data['partner1value'] + '</span><span class="suit">&' + data['player1suit'] + '</span></a>'))
            }
        }
    };
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
    $("#joingame").on("submit", function(event) {
        if($('#handle').val()){
            $("#handle").prop("readonly", true);
            var message = {
                handle: $('#handle').val(),
                type: 'join',
            }
            chatsock.send(JSON.stringify(message));
        }
        else{
            alert("Please enter a handle.");
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
