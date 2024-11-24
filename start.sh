#!/bin/bash

# Start the dbus service
dbus-daemon --system --fork

# Set the VNC password and start the VNC server
vncserver :1 -geometry 1280x720 -depth 24  # Reduced size to 1280x720

# Export the display for all GUI applications
export DISPLAY=:1

# Start the noVNC server
websockify --web=/usr/share/novnc/ --wrap-mode=ignore 8080 localhost:5901 &

# Start the Flask app
python app.py
