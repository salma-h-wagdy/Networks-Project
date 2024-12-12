from flask import Flask, request, jsonify, make_response , render_template_string , render_template , redirect , url_for, session
import Authentication


app = Flask(__name__)
app.secret_key = 'supersecretkey'

# connected_clients = []

# @app.route('/')
# def home():
#     return render_template_string('''
#     <form action="/authenticate" method="POST">
#         <label for="username">Username:</label><br>
#         <input type="text" id="username" name="username"><br>
#         <label for="password">Password:</label><br>
#         <input type="password" id="password" name="password"><br><br>
#         <input type="submit" value="Submit">
#     </form>
#     ''')

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

# @app.route('/authenticate', methods=['POST'])
# def authenticate():
#     auth_header = request.headers.get('Authorization')
#     if not auth_header or not auth_header.startswith('Basic '):
#         return make_response('Authentication required', 401, {'WWW-Authenticate': 'Basic realm="Login required"'})

#     encoded_credentials = auth_header.split(' ')[1]
#     decoded_credentials = Authentication.base64.b64decode(encoded_credentials).decode('utf-8')
#     username, password = decoded_credentials.split(':')
    
#     nonce = Authentication.generate_nonce()
#     server_hash = Authentication.sha256_hash(f"{username}:{password}:{nonce}")

#     response = make_response(jsonify({'nonce': nonce, 'hash': server_hash}), 200)
#     response.headers['Content-Type'] = 'application/json'
#     return response

# @app.route('/validate', methods=['POST'])
# def validate():
#     data = request.json
#     username = data.get('username')
#     client_hash = data.get('hash')
#     nonce = data.get('nonce')

#     if username not in Authentication.users:
#         return jsonify({'message': 'Authentication failed'}), 401

#     password = Authentication.users[username]
#     server_hash = Authentication.sha256_hash(f"{username}:{password}:{nonce}")

#     if client_hash == server_hash:
#         return jsonify({'message': 'Authentication successful'}), 200
#     else:
#         return jsonify({'message': 'Authentication failed'}), 401
      
      
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
    
    # if request.method == 'GET':
    #     # Generate nonce for the client
    #     if 'nonce' not in session:
    #         nonce = Authentication.generate_nonce()
    #         session['nonce'] = nonce
    #         print(f"Generated nonce: {nonce}")  # Debug print to check the nonce
    #     else:
    #         nonce = session['nonce']
    #     return render_template('Auth.html', nonce=nonce)

    # if request.method == 'POST':
    #     # Get username and password from the form submission
    #     username = request.form['username']
    #     password = request.form['password']
    #     client_hash = request.form['hash']
        
    #     # Get the nonce from the session
    #     nonce = session.get('nonce')
        
    #     stored_password = Authentication.users.get(username)
    #     if stored_password:
    #         print(f"Hashing string: {username}:{stored_password}:{nonce}")
    #         server_hash = Authentication.sha256_hash(f"{username}:{stored_password}:{nonce}")
        
    #         # Compare the client hash with the server hash
    #         if client_hash == server_hash:
    #             return redirect(url_for('success'))
    #         else:
    #             return jsonify({'message': 'Authentication failed'}), 401
    #     else:
    #         return jsonify({'message': 'Authentication failed: invalid username/password'}), 401

# @app.route('/validate', methods=['GET','POST'])
# def validate():
#     if request.method == 'POST':
#         client_hash = request.form['hash']
#         nonce = session.get('nonce')
#         username = session.get('username')
#         server_hash = session.get('server_hash')

#         if not nonce or not username or not server_hash:
#             return jsonify({'message': 'Session expired. Please try again.'}), 401

#         if client_hash == server_hash:
#             return redirect(url_for('success'))
#         else:
#             return jsonify({'message': 'Authentication failed'}), 401
#     else:
#         nonce = session.get('nonce')
#         return render_template('validate.html', nonce=nonce)
    
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