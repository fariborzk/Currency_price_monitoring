# README for Currency Price Monitoring and Notification System

## Project Overview

The **Currency Price Monitoring and Notification System** is designed to continuously track currency prices from a web application and send notifications whenever a price change is detected. The system operates 24/7 on a **VPS** (Virtual Private Server), ensuring real-time monitoring and logging. Every time a price change occurs, the system logs the new price and sends a notification through a **Telegram bot**.

Key features include:
- **Real-time Monitoring**: The system continuously monitors the specified web pages for price changes.
- **Telegram Notifications**: When a price change is detected, a notification with the new price is sent to a Telegram bot.
- **CSV Logging**: All price changes are logged in a **CSV file** for historical analysis.
- **Daily Report**: At the end of each day, a summary report of all price changes is sent to the user.
  
## Key Components:
1. **Price Monitoring**: Tracks specific price parameters on the target web page.
2. **Logging**: Logs every price change with a timestamp in a **CSV file**.
3. **Telegram Bot Integration**: Sends notifications to a Telegram bot whenever a price change occurs.
4. **Daily Reports**: Sends a daily summary report of price changes to the user.

---

## Tools and Libraries
The following tools and libraries are used to run the project:

- **Python** programming language.
- Libraries:
  - `requests` - For sending HTTP requests and scraping data from web pages.
  - `beautifulsoup4` - For parsing HTML content.
  - `pandas` - For logging and storing price data.
  - `python-telegram-bot` - For sending Telegram notifications.
  
---

## Project Structure

SendCurrencyPrices/
│
├── .env # Environment configuration (e.g., Telegram token)
├── .idea # Project IDE files (JetBrains)
├── .venv # Virtual environment
├── requirements.txt # Project dependencies
├── telegram_notifier.py # Script to send notifications via Telegram
├── tgn_monitor.py # Main monitoring script
├── dump_pages.py # Script for scraping price data
├── probe_cell.py # Helper script for web scraping
└── price_page.html # Template for price page scraping

## How to Run

1. **Install dependencies**: 
   - First, create a virtual environment:
     ```bash
     python3 -m venv .venv
     ```
   - Activate the environment:
     ```bash
     source .venv/bin/activate
     ```
   - Install required libraries:
     ```bash
     pip install -r requirements.txt
     ```

2. **Configure the environment**:
   - Set up environment variables (e.g., Telegram bot token) in the `.env` file.

3. **Run the monitoring system**:
   - To start the system, run the following command:
     ```bash
     python tgn_monitor.py
     ```

4. The system will monitor the price pages and send notifications via Telegram whenever a price change is detected.

---

## Logs and Notifications

- **Price Changes**: Every price change is logged in a **CSV file** with the following columns:
  - Timestamp
  - Old Price
  - New Price
  - Price Change Percentage

- **Telegram Notifications**: Whenever a price changes, the bot sends a notification with the following message:
  - **Price Update**: New price details with a link to the web page.
  
---

## Daily Report

At the end of each day, a daily report is automatically generated and sent via the Telegram bot. The report includes:

- A summary of all price changes for the day.
- A link to the full price history in the **CSV file**.

---

## Conclusion

This system provides a reliable and automated solution for monitoring currency prices in real-time, logging changes, and sending notifications through Telegram. It ensures 24/7 monitoring and timely reporting of price fluctuations.

---

## References

- **Telegram Bot API**: [Telegram Bot API Documentation](https://core.telegram.org/bots/api)
- **BeautifulSoup Documentation**: [BeautifulSoup Documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- **Python Requests**: [Python Requests Library](https://requests.readthedocs.io/en/master/)
