const BASE_URL = "https://satriastegapibackend-281917766163.asia-southeast2.run.app/frontend";  // Empty string for single deployment

// Register
document.getElementById("register-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("register-email").value;
    const password = document.getElementById("register-password").value;

    const response = await fetch(`${BASE_URL}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
    });

    const result = await response.json();
    document.getElementById("register-result").innerText = result.message || result.detail;
});

// Login
document.getElementById("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;

    const response = await fetch(`${BASE_URL}/token`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
    });

    const result = await response.json();
    document.getElementById("login-result").innerText = result.access_token
        ? "Login successful!"
        : result.detail;

    if (result.access_token) {
        localStorage.setItem("access_token", result.access_token);
        localStorage.setItem("refresh_token", result.refresh_token);
        localStorage.setItem("api_key", result.api_key);
    }
});

// Function to refresh the access token using the refresh token
async function refreshAccessToken() {
    const refresh_token = localStorage.getItem("refresh_token");
    if (!refresh_token) return null;

    const response = await fetch(`${BASE_URL}/refresh-token`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token }),
    });

    const result = await response.json();
    if (result.access_token) {
        localStorage.setItem("access_token", result.access_token);
        return result.access_token;
    }
    return null;
}

// Function to handle API requests with automatic token refresh if needed
async function apiRequest(url, options) {
    let access_token = localStorage.getItem("access_token");

    // Attempt to make the request
    let response = await fetch(url, {
        ...options,
        headers: {
            ...options.headers,
            "Authorization": `Bearer ${access_token}`, // Add access token to request
        }
    });

    if (response.status === 401) {  // If the access token is expired (Unauthorized)
        access_token = await refreshAccessToken(); // Try to refresh the token
        if (access_token) {
            // Retry the request with the new access token
            response = await fetch(url, {
                ...options,
                headers: {
                    ...options.headers,
                    "Authorization": `Bearer ${access_token}`,
                }
            });
        }
    }
    return response;
}

// Hide Message
document.getElementById("hide-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const publicMessage = document.getElementById("public-message").value;
    const privateMessage = document.getElementById("private-message").value;

    const apiKey = localStorage.getItem("api_key");
    if (!apiKey) {
        alert("Please log in first.");
        return;
    }

    const response = await apiRequest(`${BASE_URL}/hide/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "x-api-key": apiKey,
        },
        body: JSON.stringify({ public: publicMessage, private: privateMessage })
    });

    const result = await response.json();
    document.getElementById("hide-result").innerText = result.hidden_message || result.detail;
});

// Reveal Message
document.getElementById("reveal-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const hiddenMessage = document.getElementById("hidden-message").value;

    const apiKey = localStorage.getItem("api_key");
    if (!apiKey) {
        alert("Please log in first.");
        return;
    }

    const response = await apiRequest(`${BASE_URL}/reveal/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "x-api-key": apiKey,
        },
        body: JSON.stringify({ public_with_hidden: hiddenMessage })
    });

    const result = await response.json();
    document.getElementById("reveal-result").innerText = result.revealed_message || result.detail;
});

// Encrypt Message
document.getElementById("encrypt-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const publicMessage = document.getElementById("public-message-encrypt").value;
    const privateMessage = document.getElementById("private-message-encrypt").value;
    const sensitivity = document.getElementById("sensitivity-encrypt").value;

    const apiKey = localStorage.getItem("api_key");
    if (!apiKey) {
        alert("Please log in first.");
        return;
    }

    const response = await apiRequest(`${BASE_URL}/stego/encrypt`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "x-api-key": apiKey,
        },
        body: JSON.stringify({ public: publicMessage, private: privateMessage, sensitivity: sensitivity })
    });

    const result = await response.json();
    document.getElementById("encrypt-result").innerHTML = `
    <strong>Key ID:</strong> ${result.key_id || 'N/A'}<br>
    <strong>Cipher Text:</strong> ${result.cipher_text || 'N/A'}<br>
    <strong>IV:</strong> ${result.iv || 'N/A'}
    `;
});

// Decrypt Message
document.getElementById("decrypt-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const keyId = document.getElementById("key-id-decrypt").value;
    const cipherText = document.getElementById("cipher-text-decrypt").value;
    const iv = document.getElementById("iv-decrypt").value;

    const apiKey = localStorage.getItem("api_key");
    if (!apiKey) {
        alert("Please log in first.");
        return;
    }

    const response = await apiRequest(`${BASE_URL}/stego/decrypt`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "x-api-key": apiKey,
        },
        body: JSON.stringify({ key_id: keyId, cipher_text: cipherText, iv: iv })
    });

    const result = await response.json();
    document.getElementById("decrypt-result").innerHTML = `
        <strong>Encrypted Cipher Text:</strong> ${result.encrypted_cipher_text || 'N/A'}<br>
        <strong>Revealed Message:</strong> ${result.revealed_public_with_hidden || 'N/A'}
    `;
});