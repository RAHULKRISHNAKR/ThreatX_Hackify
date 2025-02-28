document.addEventListener("DOMContentLoaded", function() {
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const chatOutput = document.getElementById("chat-output");

    if (!chatForm || !chatInput || !chatOutput) {
        console.error("Required elements not found!");
        return;
    }

    // Add initial greeting
    appendMessage("Assistant: Hello! I'm ThreatX AI. How can I assist you with cybersecurity today?", false);

    chatForm.addEventListener("submit", function(event) {
        event.preventDefault();
        const userInput = chatInput.value.trim();
        
        if (!userInput) return;
        
        // Disable input and show loading immediately
        chatInput.disabled = true;
        chatInput.value = "";

        // Show user message instantly
        appendMessage("Human: " + userInput, true);
        
        // Add loading animation
        const loadingMsg = appendMessage("Assistant: Analyzing response...", false);
        let dots = 0;
        const loadingInterval = setInterval(() => {
            dots = (dots + 1) % 4;
            loadingMsg.textContent = "Assistant: Analyzing response" + ".".repeat(dots);
        }, 300);

        fetch("/api/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ message: userInput })
        })
        .then(response => response.json())
        .then(data => {
            clearInterval(loadingInterval);
            loadingMsg.remove();
            appendMessage("Assistant: " + data.response, false);
        })
        .catch(error => {
            clearInterval(loadingInterval);
            loadingMsg.remove();
            appendMessage("Assistant: Sorry, there was an error processing your request.", false);
        })
        .finally(() => {
            chatInput.disabled = false;
            chatInput.focus();
        });
    });

    function appendMessage(message, isUser) {
        const messageElement = document.createElement("div");
        messageElement.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
        
        if (!isUser && message.startsWith("Assistant: ")) {
            const markdownText = message.replace("Assistant: ", "");
            try {
                messageElement.innerHTML = marked.parse(markdownText);
            } catch (e) {
                messageElement.textContent = message;
            }
        } else {
            messageElement.textContent = message;
        }
        
        chatOutput.appendChild(messageElement);
        chatOutput.scrollTop = chatOutput.scrollHeight;
        return messageElement;
    }

    // Focus input field on load
    chatInput.focus();
});