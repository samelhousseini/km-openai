var socket = io();

/* Set the width of the sidebar to 250px and the left margin of the page content to 250px */
function openNav() {
    document.getElementById("mySidebar").style.width = "250px";
    document.getElementById("main").style.marginLeft = "250px";
}

/* Set the width of the sidebar to 0 and the left margin of the page content to 0 */
function closeNav() {
    document.getElementById("mySidebar").style.width = "0";
    document.getElementById("main").style.marginLeft = "0";
}


document.getElementById("send-button").addEventListener("click", function () {
    let message = document.getElementById("input-message").value.trim();

    if (message) {
        // Append human message
        let humanBubble = document.createElement("div");
        humanBubble.classList.add("chat-bubble", "human");
        humanBubble.innerText = message;
        document.getElementById("chat-container").appendChild(humanBubble);
        
        socket.emit('message', message);

        // Clear input field
        document.getElementById("input-message").value = "";
    }
});

socket.on('message', (message) => {
    document.getElementById("chat-container").lastChild.innerHTML   = document.getElementById("chat-container").lastChild.innerHTML  + '<br>' + message + '<br><br>';
});

socket.on('new_message', (message) => {
    console.log("Created new response bubble " + message)
    let aiBubble = document.createElement("div");
    aiBubble.classList.add("chat-bubble", "ai");
    aiBubble.innerText = ''
    document.getElementById("chat-container").appendChild(aiBubble);
    document.getElementById("chat-container").scrollTop = document.getElementById("chat-container").scrollHeight;
});

socket.on('token', (message) => {
    console.log(message)
    document.getElementById("chat-container").lastChild.innerHTML  = document.getElementById("chat-container").lastChild.innerHTML + message;
});

socket.on('connect', function() {
    console.log('Im connected!');
});

// Send message with Enter key
document.getElementById("input-message").addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
        event.preventDefault();
        document.getElementById("send-button").click();
    }
});