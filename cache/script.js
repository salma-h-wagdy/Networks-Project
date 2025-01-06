async function fetchData() {
    const username = prompt("Enter username:");
    const password = prompt("Enter password:");
    const nonce = await getNonce(username, password);

    if (!nonce) {
        document.getElementById('response').innerText = 'Failed to get nonce.';
        return;
    }
    console.log("Nonce received: ", nonce);
    const credentials = btoa(`${username}:${password}`);
    const hash = await sha256(`${username}:${password}:${nonce}`);

    const headers = new Headers();
    headers.append('Authorization', `${credentials}:${hash}`);

    const response = await fetch('/authenticate', {
        method: 'GET',
        headers: headers
    });

    if (response.status === 401) {
        document.getElementById('response').innerText = 'Authentication failed.';
    } else {
        const text = await response.text();
        console.log("Username received: ", username);
        window.location.href = `welcome.html?username=${encodeURIComponent(username)}`;
    }
}

async function getNonce(username, password) {
    console.log("getNonce called");
    try {
        const response = await fetch('https://localhost:8443/authenticate', {
            method: 'GET',
            headers: {
                'Authorization': 'Basic ' + btoa(`${username}:${password}`)
            }
        });
        console.log("Fetch response: ", response);
        // if (!response.ok) {
        //     throw new Error('Network response was not ok');
        // }

        const authHeader = response.headers.get('www-authenticate');
        console.log("www-Authenticate header: ", authHeader);

        if (authHeader) {
            const nonceMatch = authHeader.match(/nonce="([^"]+)"/);
            if (nonceMatch) {
                const nonce = nonceMatch[1];
                console.log("Nonce: ", nonce);
                return nonce;
            } else {
                throw new Error('Nonce not found in WWW-Authenticate header');
            }
        } else {
            throw new Error('WWW-Authenticate header not found');
        }
    } catch (error) {
        console.error('Error getting nonce:', error);
    }
}

async function sha256(message) {
    const msgBuffer = new TextEncoder().encode(message);
    const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    return hashHex;
}

function getQueryParam(param) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(param);
}

function goBack() {
    window.location.href = '/';
}

document.addEventListener('DOMContentLoaded', () => {
    const username = getQueryParam('username');
    if (username) {
        document.getElementById('welcomeMessage').innerText = `Authenticated Successfully! Welcome, ${username} :D`;
    } else {
        document.getElementById('welcomeMessage').innerText = 'Welcome!';
    }
});