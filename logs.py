
import logging


logging.basicConfig(level=logging.DEBUG)

gui_callback = None  # Global variable to store the GUI's callback function

def register_gui_callback(callback):
    """Register the GUI's logging function."""
    global gui_callback
    if callable(callback):
        gui_callback = callback
        logging.info("GUI callback registered successfully.")
    else:
        logging.error("Failed to register GUI callback. Provided object is not callable.")

def log_frame_sent(frame_data):
    """Log frame data and send it to the GUI, if registered."""
    logging.info(f"Frame sent: {frame_data}")
    if callable(gui_callback):  # Check if gui_callback is callable
        gui_callback("Frames Sent", f"Frame sent: {frame_data}")
    else:
        logging.warning("GUI callback is not set or is not callable.")

def log_responses(response):
    message = f"Response: {response}"
    logging.info(message)
    if callable(gui_callback):
        gui_callback("Responses", message)
    else:
        logging.warning("GUI callback is not set or is not callable.")

def log_event_received(event):
    """Log events data and send it to the appropriate GUI tab, if registered."""
    message = f"Event: {event}"
    logging.info(message)

    if callable(gui_callback):  # Ensure the callback is registered
        # Determine the appropriate tab based on event type
        if "RequestReceived" in str(event):
            gui_callback("Requests", message)
        else:
            gui_callback("Frames Received", message)
    else:
        logging.warning("GUI callback is not set or is not callable.")

def log_error_exception(error):
    """Log errors and exceptions to the GUI, if registered."""
    message = f"Error: {error}"
    logging.error(message)
    if callable(gui_callback):
        gui_callback("Errors", message)
    else:
        logging.warning("GUI callback is not set or is not callable.")