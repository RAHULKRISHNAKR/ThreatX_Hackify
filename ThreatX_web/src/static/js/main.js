document.addEventListener("DOMContentLoaded", function() {
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const chatOutput = document.getElementById("chat-output");

    chatForm.addEventListener("submit", function(event) {
        event.preventDefault();
        const userInput = chatInput.value;
        chatInput.value = "";

        appendMessage("You: " + userInput);

        fetch("/api/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ message: userInput })
        })
        .then(response => response.json())
        .then(data => {
            appendMessage("Bot: " + data.response);
        })
        .catch(error => {
            console.error("Error:", error);
            appendMessage("Bot: Sorry, there was an error.");
        });
    });

    function appendMessage(message) {
        const messageElement = document.createElement("div");
        messageElement.textContent = message;
        chatOutput.appendChild(messageElement);
    }
});