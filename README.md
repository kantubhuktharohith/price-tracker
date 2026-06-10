# Price Tracker

A Flask-based price tracking web app that lets users register, log in, and track product prices over time. The app stores products and price history in SQLite, scrapes current prices from product URLs, and supports email alerts when prices drop below a target.

## Features

- User registration and login with `Flask-Login`
- Product tracking by URL and target price
- Price history charting for tracked products
- Background price scraper using `requests` and `BeautifulSoup`
- Email alert support for price drops
- Optional Chrome extension UI in `chrome_extension/`

## Project Structure

- `app.py` - Flask web application and API routes
- `models.py` - SQLAlchemy models for users, products, and price history
- `price.py` - scraping logic, background worker, and email alert helper
- `templates/` - Flask templates for dashboard and authentication
- `static/` - CSS and client-side resources
- `chrome_extension/` - extension manifest and popup UI files
- `requirements.txt` - Python dependencies

## Requirements

- Python 3.10+ (recommended)
- `pip`
- `Flask`
- `Flask-SQLAlchemy`
- `Flask-Login`
- `requests`
- `beautifulsoup4`
- `python-dotenv`

## Setup

1. Create a virtual environment:

   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root with these values:

   ```env
   SENDER_EMAIL=your-email@example.com
   SENDER_APP_PASSWORD=your-email-app-password
   RECEIVER_EMAIL=your-notification-email@example.com
   ```

4. Run the Flask app:

   ```bash
   python app.py
   ```

5. Open the app in your browser:

   ```text
   http://127.0.0.1:5050
   ```

## Running the Price Checker

The scraper in `price.py` can be run as a background process to update price history and send email alerts.

```bash
python price.py
```

It will use `pulse.db` from the project root and check tracked products in intervals defined by `CHECK_INTERVAL_SECONDS`.

## Notes

- The app uses `sqlite:///pulse.db` by default and creates the database automatically on first run.
- If you plan to deploy publicly, change the `SECRET_KEY` and secure `.env` values.
- Scraping logic is tailored for Amazon-style product pages and may need updates if the target site changes.

## Chrome Extension

The `chrome_extension/` folder contains a simple extension manifest and popup UI that can be adapted to integrate with the tracker.

## License

This project does not include a license file. Add one if you want to make usage terms explicit.
