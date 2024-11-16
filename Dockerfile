# Base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Chrome and ChromeDriver for Selenium
RUN apt-get update && apt-get install -y wget gnupg2 software-properties-common unzip libglib2.0-0 libnss3 libfontconfig1 libxss1 libappindicator3-1 libgbm1 && \
    wget -q -O google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    dpkg -i google-chrome.deb || apt-get -f install -y && \
    rm google-chrome.deb && \
    CHROME_VERSION=$(google-chrome --version | awk '{print $3}') && \
    wget -q "https://chromedriver.storage.googleapis.com/$CHROME_VERSION/chromedriver_linux64.zip" && \
    unzip chromedriver_linux64.zip -d /usr/local/bin && \
    rm chromedriver_linux64.zip


# Expose port (if Flask app is used)
EXPOSE 5000

# Default command to run the scraper
CMD ["python", "run_scraper.py"]
