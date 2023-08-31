var socket = io();
let selectedOption = 'ccr';


function saveSelection() {
    const radioButtons = document.getElementsByName('search-method');

    for (let i = 0; i < radioButtons.length; i++) {
        if (radioButtons[i].checked) {
            selectedOption = radioButtons[i].value;
            break;
        }
    }

    if (selectedOption == 'os') {
        socket.emit('config', 'os');
    } 
    else if (selectedOption == 'ccr') {
        socket.emit('config', 'ccr');
    }
    else if (selectedOption == 'zs') {
        socket.emit('config', 'zs');
    }
    else {
        socket.emit('config', 'os');
    }

    console.log("New Config: " + selectedOption)

    closeNav();
}




/* Set the width of the sidebar to 250px and the left margin of the page content to 250px */
function openNav() {
    document.getElementById("mySidebar").style.width = "450px";
    document.getElementById("main").style.marginLeft = "450px";
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
    console.log(message)
    document.getElementById("chat-container").lastChild.innerHTML   = document.getElementById("chat-container").lastChild.innerHTML  + '<br>' + message + '<br><br>';
    document.getElementById("chat-container").scrollTop = document.getElementById("chat-container").scrollHeight;
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
    document.getElementById("chat-container").scrollTop = document.getElementById("chat-container").scrollHeight;
});

socket.on('connect', function() {
    console.log('Im connected! ' + selectedOption);
    socket.emit('config', selectedOption);
});

// Send message with Enter key
document.getElementById("input-message").addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
        event.preventDefault();
        document.getElementById("send-button").click();
    }
});