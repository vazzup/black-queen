$(function() {
    // When we're using HTTPS, use WSS too.
    var ws_scheme = window.location.protocol == "https:" ? "wss" : "ws";
    var chatsock = new ReconnectingWebSocket(ws_scheme + '://' + window.location.host + "/chat" + window.location.pathname);

    chatsock.onmessage = function(message) {
        var data = JSON.parse(message.data);
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
                var card = $('<li><a class="card rank-' + card_rank + ' ' + card_suit +'"><span class="rank">' + card_rank.toUpperCase() + '</span><span class="suit">&' + card_suit + ';</span></a></li>');
                cards.append(card)
            }
        }
    };

    $("#chatform").on("submit", function(event) {
        if($('#handle').val()){
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
            alert("Please enter a handle.");
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
            $("#message").val('').focus();
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
            $("#message").val('').focus();
        }
        else{
            alert("Please enter a handle.");
        }
        return false;
    });

});
