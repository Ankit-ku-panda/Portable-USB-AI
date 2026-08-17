"use strict";

/*
============================================================
 PORTABLE AI - COMPLETE FRONTEND
============================================================

Features:
- Send button works
- Enter sends message
- Shift+Enter creates new line
- New Chat works without refresh
- Chat history works
- Old chats can be opened
- Current chat gets a unique ID
- Chats are automatically saved
- Suggestions work
- Settings button works
- Model button works
- Mobile sidebar works
- Streaming llama.cpp responses
- No duplicate event listeners
============================================================
*/


// ============================================================
// API
// ============================================================

const API = {
    completions: "/v1/chat/completions",
    health: "/health",
    models: "/api/models",
    config: "/api/config",
    chats: "/api/chats",
    saveChat: "/api/save-chat"
};


// ============================================================
// DOM
// ============================================================

const setupScreen = document.getElementById("setupScreen");
const chatScreen = document.getElementById("chatScreen");

const sidebar = document.getElementById("sidebar");
const chatHistory = document.getElementById("chatHistory");

const newChatBtn = document.getElementById("newChatBtn");
const settingsBtn = document.getElementById("settingsBtn");
const modelButton = document.getElementById("modelButton");
const modelSelect = document.getElementById("modelSelect");
const providerSelect = document.getElementById("providerSelect");
const modelNameInput = document.getElementById("modelNameInput");
const apiKeyInput = document.getElementById("apiKeyInput");
const baseUrlInput = document.getElementById("baseUrlInput");
const saveConfigBtn = document.getElementById("saveConfigBtn");
const setupSubtitle = document.getElementById("setupSubtitle");

const menuBtn = document.getElementById("menuBtn");
const closeSidebarBtn = document.getElementById("closeSidebarBtn");

let sidebarOpen = true;

const chat = document.getElementById("chat");
const welcomeScreen = document.getElementById("welcomeScreen");

const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const attachButton = document.getElementById("attachButton");

const statusEl = document.getElementById("status");
const modelInfo = document.getElementById("modelInfo");

let receivedToken = false;
let streamTimedOut = false;


// ============================================================
// STATE
// ============================================================

let messages = [];

let config = {
    provider: "local",
    model: "",
    base_url: "",
    api_key: ""
};

let currentChatId = null;

let isSending = false;

let abortController = null;


// ============================================================
// HELPERS
// ============================================================

function generateChatId() {

    const now = new Date();

    const random = Math.random()
        .toString(36)
        .substring(2, 8);

    return (
        now.getFullYear() +
        String(now.getMonth() + 1).padStart(2, "0") +
        String(now.getDate()).padStart(2, "0") +
        "_" +
        String(now.getHours()).padStart(2, "0") +
        String(now.getMinutes()).padStart(2, "0") +
        String(now.getSeconds()).padStart(2, "0") +
        "_" +
        random
    );
}


function setStatus(text, color = "") {

    if (!statusEl) {
        return;
    }

    statusEl.textContent = text;

    if (color) {
        statusEl.style.color = color;
    }
}


function escapeHtml(text) {

    const div = document.createElement("div");

    div.textContent = text;

    return div.innerHTML;
}


function getChatTitle() {

    const firstUserMessage = messages.find(
        message => message.role === "user"
    );

    if (!firstUserMessage) {
        return "New chat";
    }

    let title = String(firstUserMessage.content || "")
        .replace(/\s+/g, " ")
        .trim();

    if (!title) {
        return "New chat";
    }

    if (title.length > 45) {
        title = title.substring(0, 45) + "...";
    }

    return title;
}


function resetSendButton() {
    isSending = false;
    sendButton.disabled = false;
    sendButton.classList.remove("sending");
}

function defaultProviderBaseUrl(provider) {
    const defaults = {
        openai: "https://api.openai.com/v1",
        gemini: "https://generativelanguage.googleapis.com/v1beta/openai",
        deepseek: "https://api.deepseek.com/v1",
        openrouter: "https://openrouter.ai/api/v1",
        custom: "https://api.openai.com/v1"
    };

    return defaults[provider] || "https://api.openai.com/v1";
}

function updateSetupForm() {
    const provider = (providerSelect?.value || "local").trim() || "local";
    const isLocal = provider === "local";

    const localGroup = document.querySelector(".model-local-group");
    const remoteGroup = document.querySelector(".model-remote-group");

    if (localGroup) {
        localGroup.style.display = isLocal ? "flex" : "none";
    }

    if (remoteGroup) {
        remoteGroup.style.display = isLocal ? "none" : "block";
    }

    if (setupSubtitle) {
        setupSubtitle.textContent = isLocal
            ? "Choose your local GGUF model"
            : "Choose your remote provider and model";
    }

    if (baseUrlInput && (!baseUrlInput.value || baseUrlInput.dataset.auto === "1")) {
        baseUrlInput.value = defaultProviderBaseUrl(provider);
        baseUrlInput.dataset.auto = "1";
    }

    if (!isLocal && modelNameInput && !modelNameInput.value) {
        modelNameInput.value = "gpt-4o-mini";
    }
}


// ============================================================
// NEW CHAT
// ============================================================

function createNewChat() {

    /*
     * Do not allow a new chat while the model
     * is generating a response.
     */

    if (isSending) {

        console.log(
            "Cannot create a new chat while generating."
        );

        return;
    }


    messages = [];

    currentChatId = generateChatId();


    /*
     * Clear visible messages.
     */

    if (chat) {

        chat.innerHTML = "";

        createWelcomeScreen();
    }


    /*
     * Clear input.
     */

    if (messageInput) {

        messageInput.value = "";

        messageInput.style.height = "auto";

        messageInput.focus();
    }


    /*
     * Close sidebar.
     */

    closeSidebar();


    /*
     * Refresh history.
     */

    loadChatHistory();


    console.log(
        "Created new chat:",
        currentChatId
    );
}


// ============================================================
// WELCOME SCREEN
// ============================================================

function createWelcomeScreen() {

    const welcome = document.createElement("div");

    welcome.className = "welcome-screen";

    welcome.innerHTML = `
        <div class="welcome-icon">P</div>

        <h1>How can I help you?</h1>

        <p>Ask Portable AI anything.</p>

        <div class="suggestion-grid">

            <button
                class="suggestion-card"
                data-prompt="Explain this code to me"
                type="button"
            >
                <strong>💻 Explain code</strong>
                <span>Understand code step by step</span>
            </button>

            <button
                class="suggestion-card"
                data-prompt="Help me debug this code"
                type="button"
            >
                <strong>🐛 Debug code</strong>
                <span>Find and fix programming problems</span>
            </button>

            <button
                class="suggestion-card"
                data-prompt="Give me a Python programming example"
                type="button"
            >
                <strong>🐍 Write Python</strong>
                <span>Create clean runnable Python code</span>
            </button>

            <button
                class="suggestion-card"
                data-prompt="Explain a difficult concept simply"
                type="button"
            >
                <strong>🧠 Learn something</strong>
                <span>Get a simple explanation</span>
            </button>

        </div>
    `;

    chat.appendChild(welcome);

    attachSuggestionEvents();
}


// ============================================================
// DISPLAY MESSAGE
// ============================================================

function addMessage(role, content) {

    const messageRow = document.createElement("div");

    messageRow.className = `message-row ${role}`;

    const messageDiv = document.createElement("div");

    messageDiv.className = `message ${role}`;

    messageDiv.textContent = content;

    messageRow.appendChild(messageDiv);

    chat.appendChild(messageRow);

    chat.scrollTop = chat.scrollHeight;

    return messageDiv;
}


// ============================================================
// RENDER EXISTING CHAT
// ============================================================

function renderMessages() {

    chat.innerHTML = "";

    if (!messages.length) {

        createWelcomeScreen();

        return;
    }


    for (const message of messages) {

        if (
            message.role !== "user" &&
            message.role !== "assistant"
        ) {
            continue;
        }

        addMessage(
            message.role,
            message.content || ""
        );
    }
}


// ============================================================
// LOAD MODELS
// ============================================================

async function loadModels() {

    try {

        const response = await fetch(
            API.models,
            {
                cache: "no-store"
            }
        );

        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );
        }

        const models = await response.json();

        modelSelect.innerHTML = "";


        if (
            !Array.isArray(models) ||
            models.length === 0
        ) {

            const option =
                document.createElement("option");

            option.value = "";

            option.textContent =
                "No GGUF models found";

            modelSelect.appendChild(option);

            return [];
        }


        for (const model of models) {

            const option =
                document.createElement("option");

            option.value = model;

            option.textContent = model;

            modelSelect.appendChild(option);
        }


        return models;

    } catch (error) {

        console.error(
            "Could not load models:",
            error
        );

        modelSelect.innerHTML =
            `<option value="">Unable to load models</option>`;

        return [];
    }
}


// ============================================================
// LOAD CONFIG
// ============================================================

async function loadConfig() {

    try {

        const response = await fetch(
            API.config,
            {
                cache: "no-store"
            }
        );

        if (!response.ok) {
            return;
        }

        const data = await response.json();

        config.provider = (data?.provider || "local").trim() || "local";
        config.model = data?.model || "";
        config.base_url = data?.base_url || "";
        config.api_key = data?.api_key || "";

        if (providerSelect) {
            providerSelect.value = config.provider;
        }

        if (modelSelect && config.model) {
            modelSelect.value = config.model;
        }

        if (modelNameInput) {
            modelNameInput.value = config.provider === "local" ? "" : (config.model || "gpt-4o-mini");
        }

        if (apiKeyInput) {
            apiKeyInput.value = config.api_key || "";
        }

        if (baseUrlInput) {
            baseUrlInput.value = config.base_url || defaultProviderBaseUrl(config.provider);
            baseUrlInput.dataset.auto = config.base_url ? "0" : "1";
        }

        updateSetupForm();

        const displayModel = config.provider === "local"
            ? (config.model || "Local model")
            : (config.model || "Remote model");

        const modelName = displayModel
            .replace(/\.gguf$/i, '')
            .split('-')
            .slice(0, 3)
            .join('-');

        modelInfo.textContent = modelName;

        if (modelButton) {
            modelButton.textContent = `📦 ${modelName}`;
        }

    } catch (error) {

        console.warn(
            "Could not load config:",
            error
        );
    }
}


// ============================================================
// SAVE CONFIG
// ============================================================

async function saveConfig() {

    const selectedProvider = (providerSelect?.value || "local").trim() || "local";
    const selectedModel = selectedProvider === "local"
        ? (modelSelect?.value || "").trim()
        : (modelNameInput?.value || "").trim();

    if (selectedProvider === "local" && !selectedModel) {
        alert("Please select a GGUF model.");
        return;
    }

    if (selectedProvider !== "local" && !selectedModel) {
        alert("Please enter a model name for this provider.");
        return;
    }

    if (selectedProvider !== "local" && !apiKeyInput?.value.trim()) {
        alert("Please enter an API key for this provider.");
        return;
    }

    const finalBaseUrl = (baseUrlInput?.value || "").trim() || defaultProviderBaseUrl(selectedProvider);

    try {

        const response = await fetch(
            API.config,
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    provider: selectedProvider,
                    model: selectedModel,
                    base_url: finalBaseUrl,
                    api_key: (apiKeyInput?.value || "").trim()
                })
            }
        );


        if (!response.ok) {

            const text =
                await response.text();

            throw new Error(
                `HTTP ${response.status}: ${text}`
            );
        }


        config.provider = selectedProvider;
        config.model = selectedModel;
        config.base_url = finalBaseUrl;
        config.api_key = (apiKeyInput?.value || "").trim();

        const modelName = selectedModel
            .replace(/\.gguf$/i, '')
            .split('-')
            .slice(0, 3)
            .join('-');

        modelInfo.textContent = modelName;

        if (modelButton) {
            modelButton.textContent = `📦 ${modelName}`;
        }

        setupScreen.style.display = "none";

        chatScreen.style.display = "flex";


        setStatus(
            "✓ Ready",
            "#8bc34a"
        );


        messageInput.focus();


    } catch (error) {

        console.error(
            "Save config failed:",
            error
        );

        alert(
            "Could not save model configuration.\n\n" +
            error.message
        );
    }
}


// ============================================================
// SHOW SETTINGS
// ============================================================

function showSettings() {

    setupScreen.style.display = "flex";

    chatScreen.style.display = "none";

    if (providerSelect) {
        providerSelect.value = config.provider || "local";
    }

    if (modelSelect && config.model) {
        modelSelect.value = config.model;
    }

    if (modelNameInput) {
        modelNameInput.value = config.provider === "local" ? "" : (config.model || "gpt-4o-mini");
    }

    if (apiKeyInput) {
        apiKeyInput.value = config.api_key || "";
    }

    if (baseUrlInput) {
        baseUrlInput.value = config.base_url || defaultProviderBaseUrl(config.provider || "local");
        baseUrlInput.dataset.auto = config.base_url ? "0" : "1";
    }

    updateSetupForm();
}


// ============================================================
// LOAD CHAT HISTORY
// ============================================================

async function loadChatHistory() {

    if (!chatHistory) {
        return;
    }


    try {

        const response = await fetch(
            API.chats,
            {
                cache: "no-store"
            }
        );


        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );
        }


        const chats = await response.json();


        /*
         * Keep history label.
         */

        chatHistory.innerHTML = `
            <div class="history-label">
                Your chats
            </div>
        `;


        if (
            !Array.isArray(chats) ||
            chats.length === 0
        ) {

            const empty =
                document.createElement("div");

            empty.className =
                "history-empty";

            empty.textContent =
                "No conversations yet";

            chatHistory.appendChild(empty);

            return;
        }


        for (const item of chats) {

            const itemWrap =
                document.createElement("div");

            itemWrap.className =
                "history-item-wrapper";

            if (
                item.id === currentChatId
            ) {

                itemWrap.classList.add(
                    "active"
                );
            }

            const button =
                document.createElement("button");

            button.type = "button";

            button.className =
                "history-item";

            button.dataset.chatId =
                item.id;

            button.innerHTML = `
                <span class="history-icon">💬</span>
                <span class="history-title">
                    ${escapeHtml(
                        item.title || "Untitled chat"
                    )}
                </span>
            `;

            button.addEventListener(
                "click",
                () => {
                    openChat(item.id);
                }
            );

            const deleteButton = document.createElement("button");
            deleteButton.type = "button";
            deleteButton.className = "delete-chat-btn";
            deleteButton.title = "Delete chat";
            deleteButton.setAttribute("aria-label", "Delete chat");
            deleteButton.textContent = "×";
            deleteButton.addEventListener("click", async (event) => {
                event.stopPropagation();
                await deleteChat(item.id);
            });

            itemWrap.appendChild(button);
            itemWrap.appendChild(deleteButton);
            chatHistory.appendChild(itemWrap);
        }


    } catch (error) {

        console.error(
            "Failed to load chat history:",
            error
        );
    }
}


// ============================================================
// OPEN OLD CHAT
// ============================================================

async function openChat(chatId) {

    if (!chatId) {
        return;
    }


    if (isSending) {

        console.log(
            "Cannot open another chat while generating."
        );

        return;
    }


    try {

        const response = await fetch(
            `/api/chat/${encodeURIComponent(chatId)}`,
            {
                cache: "no-store"
            }
        );


        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );
        }


        const data = await response.json();


        currentChatId =
            data.id || chatId;


        messages =
            Array.isArray(data.messages)
                ? data.messages
                : [];


        if (data.model) {

            config.model =
                data.model;

            modelSelect.value =
                data.model;

            const modelName = data.model
                .replace('.gguf', '')
                .split('-')
                .slice(0, 3)
                .join('-');

            modelInfo.textContent = modelName;

            if (modelButton) {
                modelButton.textContent = `📦 ${modelName}`;
            }
        }


        renderMessages();

        await loadChatHistory();


        closeSidebar();


    messageInput.focus();


        console.log(
            "Opened chat:",
            currentChatId
        );


    } catch (error) {

        console.error(
            "Failed to open chat:",
            error
        );

        alert(
            "Could not open this conversation.\n\n" +
            error.message
        );
    }
}


// ============================================================
// DELETE CHAT
// ============================================================

async function deleteChat(chatId) {

    if (!chatId) {
        return;
    }

    try {

        const response = await fetch(
            `/api/chat/${encodeURIComponent(chatId)}`,
            {
                method: "DELETE"
            }
        );

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        if (currentChatId === chatId) {
            currentChatId = null;
            messages = [];

            if (chat) {
                chat.innerHTML = "";
                createWelcomeScreen();
            }
        }

        await loadChatHistory();

    } catch (error) {
        console.error("Failed to delete chat:", error);
        alert("Could not delete this conversation.");
    }
}


// ============================================================
// SAVE CURRENT CHAT
// ============================================================

async function saveCurrentChat() {

    if (!messages.length) {
        return false;
    }


    /*
     * Make absolutely sure this chat has an ID.
     */

    if (!currentChatId) {

        currentChatId =
            generateChatId();
    }


    const chatData = {

        id: currentChatId,

        title: getChatTitle(),

        model: config.model,

        date: new Date().toISOString(),

        messages: messages
    };


    try {

        const response = await fetch(
            API.saveChat,
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify(
                    chatData
                )
            }
        );


        if (!response.ok) {

            const text =
                await response.text();

            throw new Error(
                `HTTP ${response.status}: ${text}`
            );
        }


        const result =
            await response.json();


        if (result.id) {

            currentChatId =
                result.id;
        }


        console.log(
            "Chat saved:",
            currentChatId
        );


        await loadChatHistory();


        return true;


    } catch (error) {

        console.error(
            "Chat save failed:",
            error
        );

        return false;
    }
}


// ============================================================
// SEND MESSAGE
// ============================================================

async function sendMessage() {

    /*
     * Prevent duplicate requests.
     */

    if (isSending) {

        console.log(
            "Already generating."
        );

        return;
    }


    const text =
        messageInput.value.trim();


    if (!text) {

        return;
    }


    if (!config.model) {

        alert(
            "No GGUF model is selected."
        );

        return;
    }


    /*
     * Make sure we have a chat ID.
     */

    if (!currentChatId) {

        currentChatId =
            generateChatId();
    }


    isSending = true;

    sendButton.disabled = true;

    sendButton.classList.add(
        "sending"
    );


    /*
     * Safety timeout: allow slower local models to finish,
     * but still reset if the request is genuinely stuck.
     */

    const emergencyTimeout = setTimeout(() => {

        console.error(
            "EMERGENCY: Force resetting button (180s timeout)"
        );

        isSending = false;

        sendButton.disabled = false;

        sendButton.classList.remove(
            "sending"
        );

        if (abortController) {

            abortController.abort();
        }

        if (assistantElement) {
            assistantElement.textContent =
                "The model is taking longer than expected. Please try a shorter prompt or re-run the request.";
        }

        setStatus("⚠ Slow response", "#ffb74d");

    }, 180000);


    /*
     * Clear input immediately.
     */

    messageInput.value = "";

    messageInput.style.height =
        "auto";


    /*
     * Hide welcome screen.
     */

    if (welcomeScreen) {

        welcomeScreen.style.display =
            "none";
    }


    /*
     * Add user message.
     */

    messages.push({

        role: "user",

        content: text
    });


    addMessage(
        "user",
        text
    );


    /*
     * Add assistant placeholder.
     */

    const assistantElement =
        addMessage(
            "assistant",
            "Thinking..."
        );


    let fullAnswer = "";


    /*
     * AbortController allows future cancellation.
     */

    abortController =
        new AbortController();


    try {

        setStatus("Generating…", "#d8b35c");

        const requestBody = {

            model: config.model,

            messages: messages,

            temperature: 0.1,

            max_tokens: 256,

            top_p: 0.9,

            frequency_penalty: 0.1,

            presence_penalty: 0.0,

            repeat_penalty: 1.1,

            stop: [
                "<|im_end|>",
                "<|end_of_text|>",
                "\n\nUser:",
                "\n\nHuman:"
            ],

            stream: true
        };


        console.log(
            "Sending request:",
            requestBody
        );


        const response = await Promise.race([
            fetch(
                API.completions,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json",

                        "Accept":
                            "text/event-stream"
                    },

                    body: JSON.stringify(
                        requestBody
                    ),

                    signal:
                        abortController.signal
                }
            ),

            new Promise((_, reject) =>
                setTimeout(
                    () => reject(
                        new Error(
                            "Request timed out after 75 seconds"
                        )
                    ),
                    75000
                )
            )
        ]);


        if (!response.ok) {

            const errorText =
                await response.text();

            throw new Error(
                `Server returned HTTP ${response.status}: ${errorText}`
            );
        }


        if (!response.body) {

            throw new Error(
                "Server returned no response body."
            );
        }


        /*
         * Remove "Thinking..."
         */

        assistantElement.textContent =
            "";


        const reader =
            response.body.getReader();


        const decoder =
            new TextDecoder(
                "utf-8"
            );


        let buffer = "";

        let timeoutId = null;
        const streamTimeoutMs = 180000;
        const thinkingWarningMs = 45000;
        let lastDataAt = Date.now();
        receivedToken = false;
        streamTimedOut = false;


        const updateThinkingState = () => {
            if (!receivedToken) {
                setStatus("Still thinking…", "#d8b35c");
            }
        };


        const resetTimeout = () => {

            if (timeoutId) {

                clearTimeout(timeoutId);
            }

            lastDataAt = Date.now();

            timeoutId = setTimeout(
                () => {

                    if (!receivedToken) {
                        updateThinkingState();
                    }

                    if (Date.now() - lastDataAt >= thinkingWarningMs) {
                        console.warn(
                            "Stream timeout: no data for 180 seconds"
                        );
                    }

                    if (Date.now() - lastDataAt >= streamTimeoutMs) {
                        streamTimedOut = true;
                        console.warn(
                            "Stream timeout: no data for 180 seconds"
                        );
                        reader.cancel();
                    }
                },
                thinkingWarningMs
            );
        };


        resetTimeout();


        while (true) {

            let result;

            try {
                result = await reader.read();
            } catch (error) {
                if (streamTimedOut) {
                    break;
                }
                throw error;
            }

            if (streamTimedOut) {
                break;
            }

            resetTimeout();


            if (result.done) {

                break;
            }


            if (result.value) {

                lastDataAt = Date.now();
                setStatus("Generating…", "#d8b35c");

                buffer += decoder.decode(
                    result.value,
                    {
                        stream: true
                    }
                );
            }


            /*
             * llama.cpp uses SSE.
             *
             * Events are separated by blank lines.
             */

            const events =
                buffer.split(/\r?\n\r?\n/);


            buffer =
                events.pop() || "";


            for (const event of events) {

                processSSEEvent(
                    event,
                    token => {

                        if (!token) {
                            return;
                        }

                        receivedToken = true;

                        fullAnswer += token;


                        assistantElement.textContent =
                            fullAnswer;


                        chat.scrollTop =
                            chat.scrollHeight;
                    }
                );
            }
        }


        if (timeoutId) {

            clearTimeout(timeoutId);
        }


        /*
         * Flush decoder.
         */

        buffer += decoder.decode();


        if (buffer.trim()) {

            processSSEEvent(
                buffer,
                token => {

                    if (!token) {
                        return;
                    }

                    receivedToken = true;

                    fullAnswer += token;


                    assistantElement.textContent =
                        fullAnswer;
                }
            );
        }


        /*
         * Empty response protection.
         */

        if (streamTimedOut) {

            assistantElement.textContent =
                "The model is taking longer than expected. Please try again.";

            console.warn(
                "Stream timed out before completion; skipping save and completion log."
            );

            resetSendButton();
            return;
        }


        if (!receivedToken && !fullAnswer.trim()) {

            assistantElement.textContent =
                "The model returned an empty response.";

            console.warn(
                "No assistant text received before stream completion."
            );

            /*
             * Remove the user message if
             * generation produced nothing.
             */

            messages.pop();
            resetSendButton();

            return;
        }


        /*
         * Save assistant response.
         */

        messages.push({

            role: "assistant",

            content: fullAnswer
        });

        resetSendButton();

        /*
         * Save chat immediately in the background.
         */

        await saveCurrentChat();


        console.log(
            "Response completed."
        );


    } catch (error) {

        console.error(
            "Send error:",
            error
        );


        if (
            error.name ===
            "AbortError"
        ) {

            if (streamTimedOut) {

                assistantElement.textContent =
                    "The model is taking longer than expected. Please try again.";

            } else {

                assistantElement.textContent =
                    "Generation stopped.";
            }

        } else {

            assistantElement.textContent =
                "Error: " +
                error.message;
        }

    } finally {

        clearTimeout(emergencyTimeout);
        if (timeoutId) {
            clearTimeout(timeoutId);
        }

        if (sendButton) {
            sendButton.disabled = false;
            sendButton.classList.remove("sending");
        }

        isSending = false;
        streamTimedOut = false;
        abortController = null;

        messageInput.focus();
    }
}


// ============================================================
// SSE PARSER
// ============================================================

function processSSEEvent(
    event,
    onToken
) {

    const lines =
        event.split(/\r?\n/);


    for (const rawLine of lines) {

        const line =
            rawLine.trim();


        if (!line) {
            continue;
        }


        if (
            !line.startsWith("data:")
        ) {

            continue;
        }


        const data =
            line.substring(5).trim();


        if (!data) {
            continue;
        }


        if (
            data === "[DONE]"
        ) {

            continue;
        }


        try {

            const json =
                JSON.parse(data);


            const choice =
                json.choices?.[0];


            if (!choice) {
                continue;
            }


            let token =
                choice.delta?.content;


            if (
                token === undefined ||
                token === null
            ) {

                token =
                    choice.text;
            }


            if (
                token === undefined ||
                token === null
            ) {

                const messageContent =
                    choice.message?.content;

                if (
                    typeof messageContent ===
                    "string"
                ) {

                    token = messageContent;

                } else if (
                    Array.isArray(
                        messageContent
                    )
                ) {

                    token = messageContent
                        .map(part => {
                            if (
                                typeof part === "string"
                            ) {
                                return part;
                            }

                            if (
                                part &&
                                typeof part === "object"
                            ) {
                                return part.text || "";
                            }

                            return "";
                        })
                        .join("");
                }
            }


            if (
                typeof token ===
                "string"
            ) {

                onToken(token);
            }


        } catch (error) {

            /*
             * Some llama.cpp responses can
             * contain non-JSON SSE lines.
             *
             * Ignore those safely.
             */

            console.debug(
                "Ignored SSE event:",
                data
            );
        }
    }
}


// ============================================================
// SUGGESTIONS
// ============================================================

function attachSuggestionEvents() {

    const suggestions =
        document.querySelectorAll(
            ".suggestion-card"
        );


    suggestions.forEach(
        button => {

            /*
             * Remove old listener by cloning.
             */

            const clone =
                button.cloneNode(true);


            button.replaceWith(
                clone
            );


            clone.addEventListener(
                "click",
                () => {

                    const prompt =
                        clone.dataset.prompt ||
                        "";


                    messageInput.value =
                        prompt;


                    messageInput.focus();


                    messageInput.dispatchEvent(
                        new Event(
                            "input"
                        )
                    );
                }
            );
        }
    );
}


// ============================================================
// ENTER KEY
// ============================================================

function handleInputKeyDown(event) {

    if (
        event.key === "Enter" &&
        !event.shiftKey
    ) {

        event.preventDefault();

        /*
         * Directly call the SAME function
         * used by the send button.
         */

        sendMessage();
    }
}


// ============================================================
// AUTO RESIZE
// ============================================================

function resizeInput() {

    messageInput.style.height =
        "auto";


    messageInput.style.height =
        Math.min(
            messageInput.scrollHeight,
            140
        ) + "px";
}


// ============================================================
// SERVER HEALTH
// ============================================================

async function checkServer() {

    try {

        const response =
            await fetch(
                API.health,
                {
                    cache: "no-store"
                }
            );


        if (response.ok) {

            setStatus(
                "✓ Ready",
                "#8bc34a"
            );

        } else {

            setStatus(
                "⚠ Loading",
                "#ff9800"
            );
        }


    } catch (error) {

        setStatus(
            "⚠ Offline",
            "#ff9800"
        );
    }
}


// ============================================================
// SIDEBAR STATE
// ============================================================

function closeSidebar() {

    if (!sidebar) {
        return;
    }

    sidebarOpen = false;
    sidebar.classList.remove("mobile-open");
    sidebar.classList.add("desktop-collapsed");

    if (chatScreen) {
        chatScreen.classList.add("sidebar-collapsed");
    }

    if (menuBtn) {
        menuBtn.style.display = "flex";
    }

    if (closeSidebarBtn) {
        closeSidebarBtn.style.display = "none";
    }
}


function openSidebar() {

    if (!sidebar) {
        return;
    }

    sidebarOpen = true;
    sidebar.classList.remove("desktop-collapsed");
    sidebar.classList.remove("mobile-open");

    if (chatScreen) {
        chatScreen.classList.remove("sidebar-collapsed");
    }

    if (window.innerWidth <= 768) {
        sidebar.classList.add("mobile-open");
        if (menuBtn) menuBtn.style.display = "flex";
        if (closeSidebarBtn) closeSidebarBtn.style.display = "none";
        return;
    }

    if (menuBtn) {
        menuBtn.style.display = "none";
    }

    if (closeSidebarBtn) {
        closeSidebarBtn.style.display = "flex";
    }
}


function syncSidebarState() {
    if (!sidebar) {
        return;
    }

    if (window.innerWidth <= 768) {
        sidebar.classList.remove("desktop-collapsed");
        if (sidebarOpen) {
            sidebar.classList.add("mobile-open");
        } else {
            sidebar.classList.remove("mobile-open");
        }
        if (chatScreen) {
            chatScreen.classList.remove("sidebar-collapsed");
        }
        if (menuBtn) menuBtn.style.display = "flex";
        if (closeSidebarBtn) closeSidebarBtn.style.display = "none";
        return;
    }

    sidebar.classList.remove("mobile-open");
    if (sidebarOpen) {
        openSidebar();
    } else {
        closeSidebar();
    }
}


function toggleSidebar() {

    if (!sidebar) {
        return;
    }

    if (window.innerWidth <= 768) {
        sidebarOpen = !sidebar.classList.contains("mobile-open");
        sidebar.classList.toggle("mobile-open");
        sidebar.classList.remove("desktop-collapsed");

        if (chatScreen) {
            chatScreen.classList.remove("sidebar-collapsed");
        }

        if (menuBtn) {
            menuBtn.style.display = "flex";
        }

        if (closeSidebarBtn) {
            closeSidebarBtn.style.display = "none";
        }

        return;
    }

    sidebarOpen = !sidebar.classList.contains("desktop-collapsed");
    if (sidebarOpen) {
        openSidebar();
    } else {
        closeSidebar();
    }
}


window.addEventListener("resize", syncSidebarState);


// ============================================================
// ATTACH BUTTON
// ============================================================

function handleAttach() {

    /*
     * File attachment is not implemented
     * yet. Do not make the button appear broken.
     */

    alert(
        "File attachments are not enabled yet."
    );
}


// ============================================================
// EVENT LISTENERS
// ============================================================

function setupEventListeners() {

    /*
     * NEW CHAT
     */

    if (newChatBtn) {

        newChatBtn.addEventListener(
            "click",
            createNewChat
        );
    }


    /*
     * SETTINGS
     */

    if (settingsBtn) {

        settingsBtn.addEventListener(
            "click",
            showSettings
        );
    }


    /*
     * MODEL BUTTON
     */

    if (modelButton) {

        modelButton.addEventListener(
            "click",
            showSettings
        );
    }


    /*
     * SAVE MODEL
     */

    if (saveConfigBtn) {

        saveConfigBtn.addEventListener(
            "click",
            saveConfig
        );
    }

    if (providerSelect) {
        providerSelect.addEventListener("change", updateSetupForm);
    }

    /*
     * SEND BUTTON
     *
     * IMPORTANT:
     * This is the only send-button listener.
     */

    if (sendButton) {

        sendButton.addEventListener(
            "click",
            function(event) {

                event.preventDefault();

                sendMessage();
            }
        );
    }


    /*
     * ENTER
     */

    if (messageInput) {

        messageInput.addEventListener(
            "keydown",
            handleInputKeyDown
        );


        messageInput.addEventListener(
            "input",
            resizeInput
        );
    }


    /*
     * ATTACH
     */

    if (attachButton) {

        attachButton.addEventListener(
            "click",
            handleAttach
        );
    }


    /*
     * MOBILE MENU
     */

    if (menuBtn) {

        menuBtn.addEventListener(
            "click",
            toggleSidebar
        );
    }

    if (closeSidebarBtn) {
        closeSidebarBtn.addEventListener(
            "click",
            closeSidebar
        );
    }


    /*
     * Initial suggestions
     */

    attachSuggestionEvents();
}


// ============================================================
// INITIALIZATION
// ============================================================

async function initialize() {

    console.log(
        "================================"
    );

    console.log(
        "Portable AI starting..."
    );

    console.log(
        "================================"
    );


    /*
     * Create initial empty chat.
     */

    currentChatId =
        generateChatId();


    /*
     * Set initial UI.
     */

    setupScreen.style.display =
        "none";

    chatScreen.style.display =
        "flex";


    setStatus(
        "● Connecting",
        "#ff9800"
    );


    /*
     * Attach listeners ONCE.
     */

    setupEventListeners();


    /*
     * Load model list.
     */

    const models =
        await loadModels();


    if (!models.length) {

        config.model = "";

        modelInfo.textContent =
            "No models available";

        modelButton.textContent = "📦 No models";

        setStatus(
            "⚠ No model",
            "#ff9800"
        );

        return;
    }

    if (providerSelect) {
        providerSelect.value = config.provider || "local";
    }

    /*
     * Load server configuration.
     */

    await loadConfig();


    /*
     * If no config was returned,
     * use first available model.
     */

    if (!config.model) {

        config.model =
            models[0];
        config.provider = "local";

        if (providerSelect) {
            providerSelect.value = "local";
        }

        if (modelSelect) {
            modelSelect.value = config.model;
        }

        modelInfo.textContent =
            `Model: ${config.model} (Local Offline)`;
    }

    updateSetupForm();


    /*
     * Load previous chats.
     */

    await loadChatHistory();


    /*
     * Check llama.cpp.
     */

    await checkServer();


    console.log(
        "Portable AI ready."
    );
}


// ============================================================
// START
// ============================================================

initialize();


// ============================================================
// HEALTH CHECK
// ============================================================

setInterval(
    checkServer,
    5000
);