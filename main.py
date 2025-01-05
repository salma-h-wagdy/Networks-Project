import socket
import threading
import tkinter as tk
from tkinter import scrolledtext
import Server


class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("HTTP/2 Server GUI")

        # Server status
        self.status_label = tk.Label(root, text="Server Status: Stopped", fg="red")
        self.status_label.pack(pady=5)

        # Log output
        self.log_area = scrolledtext.ScrolledText(root, width=60, height=20, state='disabled')
        self.log_area.pack(padx=10, pady=5)

        # Start/Stop button
        self.start_button = tk.Button(root, text="Start Server", command=self.start_server)
        self.start_button.pack(side=tk.LEFT, padx=10, pady=10)

        self.stop_button = tk.Button(root, text="Stop Server", command=self.stop_server, state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=10, pady=10)

        self.server_socket = None
        self.server_thread = None
        self.running = False

    def log_message(self, message):
        self.log_area.configure(state='normal')
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.configure(state='disabled')
        self.log_area.see(tk.END)

    def start_server(self):
        if self.running:
            self.log_message("Server is already running.")
            return

        self.running = True
        self.status_label.config(text="Server Status: Running", fg="green")
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')

        # Start server thread
        self.server_thread = threading.Thread(target=self.run_server, daemon=True)
        self.server_thread.start()
        self.log_message("Server started.")

    def stop_server(self):
        if not self.running:
            self.log_message("Server is not running.")
            return

        self.running = False
        if self.server_socket:
            self.server_socket.close()

        self.status_label.config(text="Server Status: Stopped", fg="red")
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.log_message("Server stopped.")

    def run_server(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', 8443))
            self.server_socket.listen(5)
            self.log_message("HTTP/2 server listening on port 8443")

            # Start server status thread
            status_thread = threading.Thread(target=Server.server_status, daemon=True)
            status_thread.start()

            while self.running:
                try:
                    client_socket, addr = self.server_socket.accept()
                    client_ip, client_port = addr
                    self.log_message(f"Connection from {client_ip}:{client_port}")
                    client_handler = threading.Thread(target=Server.handle_client, args=(client_socket,), daemon=True)
                    client_handler.start()
                except OSError:
                    break  # Socket closed

        except Exception as e:
            self.log_message(f"Error: {e}")
        finally:
            self.stop_server()


if __name__ == "__main__":
    root = tk.Tk()
    gui = ServerGUI(root)
    root.mainloop()
