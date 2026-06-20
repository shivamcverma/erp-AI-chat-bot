function saveChat() {
    localStorage.setItem(
        "erp_chat_history",
        document.getElementById("chat-box").innerHTML
    );

    localStorage.setItem(
        "erp_chat_time",
        Date.now()
    );
}

async function sendMessage() {

    let input = document.getElementById("message");
    let message = input.value;

    if (!message.trim()) return;

    let chatBox = document.getElementById("chat-box");

    // User message
    chatBox.innerHTML += `<div class="user">You: ${message}</div>`;
    saveChat();

    input.value = "";

    // Thinking message
    let thinkingId = "thinking_" + Date.now();

    chatBox.innerHTML += `
        <div class="bot" id="${thinkingId}">
            🤖 Thinking...
        </div>
    `;

    chatBox.scrollTop = chatBox.scrollHeight;

    try {

        let response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: message
            })
        });

        let data = await response.json();

        console.log("DEBUG:", data);

        setTimeout(() => {

            let thinkingDiv = document.getElementById(thinkingId);

            if (data.source === "knowledge_base") {

                thinkingDiv.innerHTML = data.answer;

                saveChat();

                if (data.steps && data.steps.length > 0) {

                    let stepHtml = "<ul>";

                    data.steps.forEach(step => {
                        stepHtml += `<li>${step}</li>`;
                    });

                    stepHtml += "</ul>";

                    chatBox.innerHTML += `
                        <div class="steps">
                            <b>Steps:</b>
                            ${stepHtml}
                        </div>
                    `;

                    saveChat();
                }

            } else {

                let reply = data.reply || "No response";

                thinkingDiv.innerHTML = reply;

                saveChat();
            }

            chatBox.scrollTop = chatBox.scrollHeight;

        }, 1500);

    } catch (error) {

        console.log(error);

        let thinkingDiv = document.getElementById(thinkingId);

        if (thinkingDiv) {
            thinkingDiv.innerHTML = "Server Error";
        }

        saveChat();
    }
}
window.onload = function () {

    let savedChat = localStorage.getItem("erp_chat_history");
    let savedTime = localStorage.getItem("erp_chat_time");

    if (savedChat && savedTime) {

        let age = Date.now() - parseInt(savedTime);

        // 24 hours
        if (age < 24 * 60 * 60 * 1000) {

            document.getElementById("chat-box").innerHTML = savedChat;

        } else {

            localStorage.removeItem("erp_chat_history");
            localStorage.removeItem("erp_chat_time");
        }
    }
};