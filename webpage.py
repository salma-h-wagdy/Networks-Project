# from flask import render_template_string
# import Server

# @Server.app.route('/')
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