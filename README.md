# Implementing a Server Agent using HTTP Protocol

## Table of Contents
- [Overview](#overview)
- [Installation](#installation)
- [How to Run](#how-to-run)
  - [Running the Server](#running-the-server)
  - [Using the Browser Client](#using-the-browser-client)
- [Testing Stream Prioritization](#testing-stream-prioritization)
- [Testing Authentication](#testing-authentication)
- [Testing Methods](#testing-methods)
- [Known Issues and Troubleshooting](#known-issues-and-troubleshooting)
- [Debugging and Logs](#debugging-and-logs)
- [Contribution](#contribution)
- [License](#license)

## Overview
This project aims to deliver a fully functional HTTP/2 server agent that integrates seamlessly with existing web technologies. The server agent will strictly adhere to specified behaviors, scenarios, message formats, and sequences, ensuring robust performance and appropriate error handling.

The following Python libraries are needed:
- `h2`
- `hpack`
- `ttkbootstrap`

Install the required libraries using pip:
```sh
python -m pip install h2 hpack ttkbootstrap
```
## How to Run

### Running the Server

Before running the server, you need to generate your own SSL certificates. Follow these steps to create a self-signed certificate:

1. Generate a private key:
```sh
openssl genpkey -algorithm RSA -out server.key
```
2. Generate a certificate signing request (CSR):
```sh
openssl req -new -key server.key -out server.csr
```
3. Generate a self-signed certificate:
```sh
openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.crt
```

After generating the certificates, you can run the server:

1. Open a terminal and navigate to the directory containing `main.py`.
2. Ensure you have the SSL certificate and key files \(server.crt and server.key\) in the same directory.
3. Execute the following command to start the server:
```sh
    python main.py
```
### Using the Browser Client

1. Open a web browser.
2. Navigate to the URL where the server is running. For example:
    ```sh
    https://localhost:8443
    ```
3. You should see the authentication page. Click the "Authenticate" button and follow the prompts to enter your username and password.


## Testing Stream Prioritization

You can test server push using curl :

```sh
curl -v --http2 --insecure https://localhost:8443/ --output index.html 
```

You can test stream prioritization using curl:

High Priority Request

```sh
curl -v --http2 --insecure https://localhost:8443/high-priority --output high.html
```
Low Priority Requests 

```sh
curl -v --http2 --insecure https://localhost:8443/low-priority --output low.html
```
### Simultaneous Requests to Test Prioritization
#### Using h2load on Linux:

install required library :

```sh
sudo apt install nghttp2
```

then run command :

```sh
h2load -n 6 -c 3 -m 3 https://localhost:8443/low-priority https://localhost:8443/high-priority

```
where :
- -n 6: Total number of requests to perform.
- -c 3: Number of concurrent clients.
- -m 3: Maximum number of streams per connection.

#### Using h2load on Windows:
1. Install WSL (Windows Subsystem for Linux) and a Linux distribution (e.g., Ubuntu).
2. Open the WSL terminal and install nghttp2:
```sh
sudo apt update
sudo apt install nghttp2
```
3. Run the h2load command:
```sh 
h2load -n 6 -c 3 -m 3 https://localhost:8443/low-priority https://localhost:8443/high-priority
```

    

## Testing Authentication
You can test authentication using curl:

```sh
curl -v --http2 --insecure -u username:password https://localhost:8443/authenticate
```

## Testing Methods 
1. After starting the server , open a terminal and navigate to the directory containing `test_methods.py`.
2. Execute the following command to start the tests:
```sh
    python test methods.py
```
## Known Issues and Troubleshooting
- SSL Certificate Issues: If you encounter issues with SSL certificates, ensure that the `server.crt` and `server.key` files are correctly generated and placed in the same directory as `main.py`.

## Debugging and Logs
The server logs detailed information about the events and flow control. You can view the logs in the terminal where the server is running to debug and verify the server's behavior.



## Contribution
- Salma Yousef
- Menna Ayman
- Fatma Ayman
- Salma Hisham
 
<!-- ##Project Structure

.
├── main.py                # Main server script
├── server.py              # Server functionalities
├── client.py              # Client script
├── README.md              # Project description and documentation -->
