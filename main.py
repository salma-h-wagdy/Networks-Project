import socket
import threading
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledText
import Server


class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("HTTP/2 Server GUI")
        self.root.geometry("700x400")

        # Frame for Status and Control
        self.frame_top = ttk.Frame(root, padding=10)
        self.frame_top.pack(fill=X, pady=10)

        # Server Status
        self.status_label = ttk.Label(self.frame_top, text="Server Status: Stopped", font=("Helvetica", 14),
                                      style="danger.TLabel")
        self.status_label.pack(side=LEFT, padx=10)

        # Control Buttons
        self.start_button = ttk.Button(self.frame_top, text="Start Server", style="success.TButton",
                                       command=self.start_server)
        self.start_button.pack(side=LEFT, padx=10)

        self.stop_button = ttk.Button(self.frame_top, text="Stop Server", style="danger.TButton",
                                      command=self.stop_server, state=DISABLED)
        self.stop_button.pack(side=LEFT, padx=10)

        # Log Area
        self.log_area = ScrolledText(root, height=15, width=80)
        self.log_area.pack(padx=10, pady=10)
        self.log_area.text.configure(state='disabled')  # Disable editing initially

        self.server_socket = None
        self.server_thread = None
        self.running = False

    def log_message(self, message):
        """Safely log messages to the log area."""
        self.log_area.text.configure(state='normal')  # Enable editing temporarily
        self.log_area.text.insert("end", message + "\n")
        self.log_area.text.configure(state='disabled')  # Disable editing again
        self.log_area.text.see("end")  # Scr


    def start_server(self):
        if self.running:
            self.log_message("Server is already running.")
            return

        self.running = True
        self.status_label.config(text="Server Status: Running", style="success.TLabel")
        self.start_button.config(state=DISABLED)
        self.stop_button.config(state=NORMAL)

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

        self.status_label.config(text="Server Status: Stopped", style="danger.TLabel")
        self.start_button.config(state=NORMAL)
        self.stop_button.config(state=DISABLED)
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
    root = ttk.Window(themename="darkly")  # You can change the theme to 'darkly', 'journal', etc.
    gui = ServerGUI(root)
    root.mainloop()
