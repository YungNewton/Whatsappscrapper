# Base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Set environment variables to disable Python buffering
ENV PYTHONUNBUFFERED=1

# Copy project files
COPY . .

# Install base dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg2 \
    software-properties-common \
    unzip \
    tigervnc-standalone-server \
    novnc \
    websockify \
    xfce4 \
    xfce4-terminal \
    libglib2.0-0 \
    libnss3 \
    libfontconfig1 \
    libxss1 \
    libappindicator3-1 \
    libgbm1 \
    libasound2 \
    fonts-liberation \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    xdg-utils \
    ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN apt-get update && apt-get install -y libvulkan1 libvulkan-dev && \
    curl -LO https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get install -y ./google-chrome-stable_current_amd64.deb && \
    rm google-chrome-stable_current_amd64.deb

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set up noVNC and websockify
RUN mkdir -p /opt/novnc/utils/websockify && \
    wget -qO- https://github.com/novnc/noVNC/archive/refs/tags/v1.3.0.tar.gz | tar xz -C /opt/novnc --strip-components=1 && \
    wget -qO- https://github.com/novnc/websockify/archive/refs/tags/v0.10.0.tar.gz | tar xz -C /opt/novnc/utils/websockify --strip-components=1 && \
    chmod +x /opt/novnc/utils/websockify/run

# Install dbus
RUN apt-get update && apt-get install -y \
    dbus-x11 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set up VNC password
RUN mkdir -p /root/.vnc && \
    echo "171002" | vncpasswd -f > /root/.vnc/passwd && \
    chmod 600 /root/.vnc/passwd

# Expose ports for Flask (5000) and noVNC (8080)
EXPOSE 5000 8080

# Add the startup script
COPY start.sh /opt/start.sh
RUN chmod +x /opt/start.sh

# Set the default command to start everything
CMD ["/opt/start.sh"]