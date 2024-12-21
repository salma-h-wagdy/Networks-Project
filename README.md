# Implementing a Server Agent using HTTP Protocol
## Overview
This project aims to deliver a fully functional HTTP/2 server agent that integrates seamlessly with existing web technologies. The server agent will strictly adhere to specified behaviors, scenarios, message formats, and sequences, ensuring robust performance and appropriate error handling.
## How to Run
- Running the Server

  Open a terminal and navigate to the directory containing main.py.
  Execute the following command to start the server:
```
    python main.py
```
- Running the Client

  Open another terminal and navigate to the directory containing client.py.
  Execute the following command to start the client:
```
    python client.py
```

## Main Client Functionalities

- **GET Request**
  - The client sends a GET request to the server.
  - The server responds with a 200 OK status code and the requested file.
  - The client displays the file content.

- **POST Request**
  - The client sends a POST request to the server.
  - The server responds with a 200 OK status code and the received data.
  - The client displays the received data.

## Running the Client

- Running the GET Request
  After running the client, the user will be prompted to enter the request type (GET or POST or exit).
    To run the GET request, the user should enter "GET" and then the file name.
```
    GET /filename.html
```
- To display server status
```
    GET /status
```

- Running the POST Request
  After running the client, the user will be prompted to enter the request type (GET or POST or exit).
    To run the POST request, the user should enter "POST /submit" and then the required payload to send.
- Example
```
    POST /submit {"name": "Salma", "age": 22}
```
- To exit the client, the user should enter "exit".



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
