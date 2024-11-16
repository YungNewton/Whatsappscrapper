# Base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg2 \
    software-properties-common \
    unzip \
    libglib2.0-0 \
    libnss3 \
    libfontconfig1 \
    libxss1 \
    libappindicator3-1 \
    libgbm1 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN wget -q -O google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    dpkg -i google-chrome.deb || apt-get -f install -y && \
    rm google-chrome.deb

# Install ChromeDriver
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}') && \
    wget -q "https://chromedriver.storage.googleapis.com/$CHROME_VERSION/chromedriver_linux64.zip" && \
    unzip chromedriver_linux64.zip -d /usr/local/bin && \
    rm chromedriver_linux64.zip

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (optional)
EXPOSE 5000

# Default command
CMD ["python", "run_scraper.py"]
