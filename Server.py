from flask import Flask, request, jsonify, make_response , render_template_string , render_template , redirect , url_for, session
import Authentication


app = Flask(__name__)
app.secret_key = 'supersecretkey'

# connected_clients = []

@app.route('/')
def home():
    if 'nonce' not in session:
        # Generate nonce for the client
        nonce = Authentication.generate_nonce()
        session['nonce'] = nonce
        print(f"Generated nonce: {nonce}")
    else:
        nonce = session['nonce']
    
    return render_template('Auth.html', nonce=nonce)
      
@app.route('/authenticate', methods=['GET','POST'])
def authenticate():
    
    username = request.form['username']
    password = request.form['password']
    client_hash = request.form['hash']
    nonce = request.form['nonce']  # Retrieve nonce from the form
    
    print(f"Received nonce: {nonce}")  # Debugging line to confirm nonce is being passed
    
    # Assuming users are stored in Authentication.users
    stored_password = Authentication.users.get(username)
    if stored_password:
        print(f"Hashing string: {username}:{stored_password}:{nonce}")
        server_hash = Authentication.sha256_hash(f"{username}:{stored_password}:{nonce}")
    
        # Compare the client hash with the server hash
        if client_hash == server_hash:
            return redirect(url_for('success'))
        else:
            return jsonify({'message': 'Authentication failed'}), 401
    else:
        return jsonify({'message': 'Authentication failed: invalid username/password'}), 401
    
@app.route('/success')
def success():
    return render_template('success.html')

# def parse_http_request(request):
#     headers, body = request.split('\r\n\r\n', 1)
#     header_lines = headers.split('\r\n')
#     method, path, _ = header_lines[0].split()
#     headers_dict = {}
#     for line in header_lines[1:]:
#         key, value = line.split(': ', 1)
#         headers_dict[key] = value
#     return method, path, headers_dict, body

# def handle_client(client_socket):
#     if not Authentication.authenticate(client_socket):
#         client_socket.close()
#         return

#     connected_clients.append(client_socket)
#     try:
#         while True:
#             #receive data from the client
#             request = client_socket.recv(1024).decode('utf-8')
#             if not request:
#                 break
            
#             method, path, headers, body = parse_http_request(request)
            
#             #send a response back 
#             if method == 'POST' and path == '/message':
#                 print(f"Received: {body}")
#                 # Send a response back to the client
#                 response = f"HTTP/1.1 200 OK\r\nContent-Length: {len(body) + 6}\r\n\r\nEcho: {body}\n"
#                 client_socket.send(response.encode('utf-8'))
                
#     except ConnectionResetError:
#         print("Client disconnected")
#     finally:
#         connected_clients.remove(client_socket)
#         client_socket.close()