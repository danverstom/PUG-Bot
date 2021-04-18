$(document).ready(function(){

    $("#send_message_button").click(function(){
    $("#send_message_button").addClass("is-loading");
    anime({
        targets: '#send_message_button',
        scale: 1.2,
        easing: "easeInOutBack"
    });
    var send_dict = {
    "channel_id": $("#channel_select").val(),
    "message": $("#message_textarea").val()
    }
    console.log(send_dict);
    $.ajax({
        type: "POST",
        url: send_message_url,
        data: JSON.stringify(send_dict),
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        success: function(data){
            if (data["success"]) {
                console.log("Sent message successfully");
                $("#message_textarea").val("");
                anime({
                    targets: '#send_message_button',
                    scale: 1,
                    easing: "easeInOutBack"
                });
                $("#send_message_button").removeClass("is-loading");
            } else {
                console.log("Could not send message")
                anime({
                    targets: '#send_message_button',
                    scale: 1,
                    easing: "easeInOutBack"
                });
                $("#send_message_button").removeClass("is-loading");
                console.log(data["error"]);
                alert(data["error"])
            }
        },
        error: function(jqXHR, exception){
            anime({
                    targets: '#send_message_button',
                    scale: 1,
                    easing: "easeInOutBack"
                });
                $("#send_message_button").removeClass("is-loading");
            console.log("Failure");
            alert(exception);
        }
        });
    });
});