# Base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install base dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg2 \
    software-properties-common \
    unzip \
    libglib2.0-0 \
    libnss3 \
    libfontconfig1 \
    libxss1 \
    libappindicator3-1 \
    libgbm1 \
    libasound2 \
    fonts-liberation \
    xdg-utils \
    libvulkan1 \
    ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN curl -LO https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get install -y ./google-chrome-stable_current_amd64.deb && \
    rm google-chrome-stable_current_amd64.deb

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (if Flask or similar app is used)
EXPOSE 5000

# Set default command to run your Python script
CMD ["python", "run_scraper.py"]
