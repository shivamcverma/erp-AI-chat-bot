async function sendMessage() {

    let input = document.getElementById("message");
    let message = input.value;

    if (!message.trim()) return;

    let chatBox = document.getElementById("chat-box");

    // User message
    chatBox.innerHTML += `<div class="user">You: ${message}</div>`;
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

        // Minimum 1.5 second thinking effect
        setTimeout(() => {

            let thinkingDiv = document.getElementById(thinkingId);

            if (data.source === "knowledge_base") {

                thinkingDiv.innerHTML = data.answer;

                // Steps
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
                }

            } else {

                let reply = data.reply || "No response";

                thinkingDiv.innerHTML = reply;
            }

            chatBox.scrollTop = chatBox.scrollHeight;

        }, 1500); // 1.5 second wait

    } catch (error) {

        console.log(error);

        let thinkingDiv = document.getElementById(thinkingId);

        if (thinkingDiv) {
            thinkingDiv.innerHTML = "Server Error";
        }
    }
}