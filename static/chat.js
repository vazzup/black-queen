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
            else if(data.handle == $('#handle').val()){
                alert("You need 5 or 7 players to start the game")
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
