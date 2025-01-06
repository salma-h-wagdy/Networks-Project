import socket
import threading
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledText
import Server
import logging
import logs

class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("HTTP/2 Server GUI")
        self.root.geometry("900x600")

        # Set the window and taskbar icon
        icon_path = "http2-logo.ico"  # Replace with your icon file name
        try:
            self.root.iconbitmap(icon_path)  # Use iconbitmap for .ico files
        except Exception as e:
            logging.error(f"Failed to set icon: {e}")

        # Frame for Control Buttons
        self.frame_top = ttk.Frame(root, padding=10)
        self.frame_top.pack(fill=X, pady=10)

        # Server Status
        self.status_label = ttk.Label(self.frame_top, text="Server Status: Stopped", font=("Georgia", 14),
                                      style="danger.TLabel")
        self.status_label.pack(side=LEFT, padx=10)

        # Control Buttons
        self.start_button = ttk.Button(self.frame_top, text="Start Server", style="success.TButton",
                                       command=self.start_server)
        self.start_button.pack(side=LEFT, padx=10)

        self.stop_button = ttk.Button(self.frame_top, text="Stop Server", style="danger.TButton",
                                      command=self.stop_server, state=DISABLED)
        self.stop_button.pack(side=LEFT, padx=10)

        # Tabs for Logs
        self.notebook = ttk.Notebook(root, padding=10)
        self.notebook.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # Create Tabs
        self.tabs = {
            "Connection Status": self.create_log_tab("Connection Status"),
            "Requests": self.create_log_tab("Requests"),
            "Responses": self.create_log_tab("Responses"),
            "Errors": self.create_log_tab("Errors and Exceptions"),
            "Frames Sent": self.create_log_tab("Frames Sent"),
            "Frames Received": self.create_log_tab("Frames Received"),
        }

        # Server State
        self.server_socket = None
        self.server_thread = None
        self.running = False

        # Logger
        logging.basicConfig(level=logging.DEBUG, handlers=[self.GUIHandler(self)])

    class GUIHandler(logging.Handler):
        """Custom logging handler to redirect logs to the GUI."""

        def __init__(self, gui):
            super().__init__()
            self.gui = gui

        def emit(self, record):
            msg = self.format(record)
            # Schedule log message insertion on the main thread
            self.gui.root.after(0, self.gui.log_message, msg)
            if "frame" in msg.lower():
                self.gui.log_message("Frames Sent", msg)
            elif "error" in msg.lower() or "exception" in msg.lower():
                self.gui.log_message("Errors", msg)

    def create_log_tab(self, title):
        """Create a new tab with a ScrolledText widget."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=title)
        log_area = ScrolledText(frame, height=20, autohide=True)
        log_area.pack(fill=BOTH, expand=True, padx=5, pady=5)
        log_area.text.configure(state='disabled')  # Disable editing
        return log_area

    def log_message(self, tab_name, message):
        """Log messages to the specified tab."""
        log_area = self.tabs[tab_name].text
        log_area.configure(state='normal')  # Enable editing temporarily
        log_area.insert("end", message + "\n" + "-" * 50 + "\n\n")
        log_area.configure(state='disabled')  # Disable editing again
        log_area.see("end")  # Scroll to the end

    def start_server(self):
        if self.running:
            self.log_message("Errors", "Server is already running.")
            return

        # Register the GUI's log_message function as a callback
        logs.register_gui_callback(self.log_message)

        self.running = True
        self.status_label.config(text="Server Status: Running", style="success.TLabel")
        self.start_button.config(state=DISABLED)
        self.stop_button.config(state=NORMAL)

        # Start server thread
        self.server_thread = threading.Thread(target=self.run_server, daemon=True)
        self.server_thread.start()
        self.log_message("Connection Status", "Server started.")

    def stop_server(self):
        if not self.running:
            self.log_message("Errors", "Server is not running.")
            return

        self.running = False
        if self.server_socket:
            self.server_socket.close()

        self.status_label.config(text="Server Status: Stopped", style="danger.TLabel")
        self.start_button.config(state=NORMAL)
        self.stop_button.config(state=DISABLED)
        self.log_message("Connection Status", "Server stopped.")

    def run_server(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', 8443))
            self.server_socket.listen(5)
            self.log_message("Connection Status", "HTTP/2 server listening on port 8443")

            # Start server status thread
            status_thread = threading.Thread(target=Server.server_status, daemon=True)
            status_thread.start()

            while self.running:
                try:
                    client_socket, addr = self.server_socket.accept()
                    client_ip, client_port = addr
                    self.log_message("Connection Status", f"Connection from {client_ip}:{client_port}")

                    # Handle client in a separate thread
                    client_handler = threading.Thread(
                        target=Server.handle_client,
                        args=(client_socket,),
                        daemon=True
                    )
                    client_handler.start()
                except OSError:
                    break  # Socket closed

        except Exception as e:
            self.log_message("Errors", f"Error: {e}")
        finally:
            self.stop_server()

def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', 8443))
    server_socket.listen(5)
    print("HTTP/2 server listening on port 8443")
    
    status_thread = threading.Thread(target=Server.server_status)
    status_thread.daemon = True
    status_thread.start() 
    
    while True:
        client_socket, addr = server_socket.accept()
        client_ip, client_port = addr
        print(f"Connection from {client_ip}:{client_port}")
        # print(f"Connection from {addr}")
        Server.handle_client(client_socket)
        client_handler = threading.Thread(target=Server.handle_client, args=(client_socket,))
        client_handler.start()


if __name__ == "__main__":
    root = ttk.Window(themename="darkly")  # Choose a theme
    gui = ServerGUI(root)
    root.mainloop()
