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

