from __future__ import annotations
from flask import Flask
from threading import Thread
import os

app = Flask(__name__)

@app.route('/')
def home() -> str:
    """Health check endpoint."""
    return "Bot is running!"

def run_flask_server() -> None:
    """Runs the Flask server in a separate thread."""
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive() -> None:
    """Starts the Flask server in a background thread."""
    t = Thread(target=run_flask_server)
    t.daemon = True # Allow main program to exit even if thread is still running
    t.start()
