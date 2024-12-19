# Implementing a Server Agent using HTTP Protocol
## Overview
This project aims to deliver a fully functional HTTP/2 server agent that integrates seamlessly with existing web technologies. The server agent will strictly adhere to specified behaviors, scenarios, message formats, and sequences, ensuring robust performance and appropriate error handling.

## Prerequirements
The `h2` Python library is needed.

```sh
python -m pip install h2
```

## How to Run

### Running the Server

1. Open a terminal and navigate to the directory containing `main.py`.
2. Execute the following command to start the server:
```sh
    python main.py
```
### Using the Browser Client

1. Open a web browser.
2. Navigate to the URL where the server is running. For example:
    ```
    https://localhost:8443
    ```
3. You should see the authentication page. Click the "Authenticate" button and follow the prompts to enter your username and password.


## Testing Stream Prioritization

You can test server push using curl :

```
the curl -v --http2 --insecure https://localhost:8443/ --output index.html 
```

You can test stream prioritization using curl:

High Priority Request

```
curl -v --http2 --insecure https://localhost:8443/high-priority --output high.html
```
Low Priority Requests 

```
curl -v --http2 --insecure https://localhost:8443/low-priority --output low.html
```

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
