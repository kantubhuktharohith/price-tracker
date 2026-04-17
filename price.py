import requests
from bs4 import BeautifulSoup
import smtplib
from email.message import EmailMessage
from datetime import datetime
import time
import re
import os
from dotenv import load_dotenv

# Load secrets from .env file (never commit .env to git!)
load_dotenv()

# Email Configuration (loaded from .env)
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_APP_PASSWORD = os.getenv("SENDER_APP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

# Settings
CHECK_INTERVAL_SECONDS = 60 * 60 * 12 # Checks every 12 hours

# Headers are crucial to prevent the website from blocking your script
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Referer": "https://www.amazon.in/"
}

BOT_DETECTION_MARKERS = [
    "captcha",
    "automated access",
    "unusual",
    "Sorry!",
    "Enter the characters you see below"
]

AMAZON_PRICE_SELECTORS = [
    "#priceblock_ourprice",
    "#priceblock_dealprice",
    "#priceblock_saleprice",
    "#price",
    ".a-price .a-offscreen",
    ".a-offscreen",
    ".a-price-whole"
]


def parse_price_from_soup(soup):
    for selector in AMAZON_PRICE_SELECTORS:
        element = soup.select_one(selector)
        if element and element.get_text(strip=True):
            price_text = element.get_text()
            clean = re.sub(r"[^\d.]", "", price_text)
            if clean:
                return float(clean)
    return None


def get_product_details(url):
    """Scrapes the webpage and extracts the product name and current price."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        page_text = response.text
        if any(marker.lower() in page_text.lower() for marker in BOT_DETECTION_MARKERS):
            print("Amazon appears to be returning a bot-detection page. Requests/BeautifulSoup may not work reliably.")
        
        soup = BeautifulSoup(page_text, "html.parser")
        
        title_element = soup.find(id="productTitle")
        title = title_element.get_text().strip() if title_element else "Unknown Product"
        
        current_price = parse_price_from_soup(soup)
        if current_price is None:
            print("Could not find the price element on the page. The website structure might have changed or requested a CAPTCHA.")
            return title, None

        return title, current_price

    except Exception as e:
        print(f"Error fetching product details: {e}")
        return None, None

def send_email_alert(title, current_price, target_price, url, user_email):
    """Sends an email notification when the price drops."""
    try:
        msg = EmailMessage()
        msg['Subject'] = f"🚨 PRICE DROP ALERT: {title}"
        msg['From'] = SENDER_EMAIL
        msg['To'] = user_email
        
        body = (
            f"Good news!\n\n"
            f"The price of '{title}' has dropped to ₹{current_price}.\n"
            f"Your target price was ₹{target_price}.\n\n"
            f"Buy it here: {url}\n"
        )
        msg.set_content(body)
        
        # Connect to Gmail's SMTP server
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
            smtp.send_message(msg)
            
        print(f"  Email alert sent to {user_email}!")
        
    except Exception as e:
        print(f"  Failed to send email: {e}")


def main():
    """Background worker that checks prices for ALL users' products using the database."""
    # Import here to avoid circular imports when app.py imports get_product_details
    from flask import Flask
    from models import db, Product, PriceHistory, User
    
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pulse.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    print("Starting Pulse Background Worker.\nPress Ctrl+C to stop.\n")
    
    while True:
        with app.app_context():
            # Fetch ALL products across ALL users
            products = Product.query.all()
            print(f"Starting check cycle. {len(products)} products across all users.\n")
            
            for product in products:
                print(f"  Checking: {product.name}...")
                title, current_price = get_product_details(product.url)
                
                display_title = title if title and title != "Unknown Product" else product.name
                
                # Update product name if we got a better one from scraping
                if title and title != "Unknown Product" and product.name == "New Tracked Product":
                    product.name = title
                
                if current_price is not None:
                    # 1. Save to database
                    entry = PriceHistory(
                        product_id=product.id,
                        price=current_price,
                        timestamp=datetime.utcnow()
                    )
                    db.session.add(entry)
                    db.session.commit()
                    print(f"  Saved: {display_title} → ₹{current_price}")
                    
                    # 2. Check for price drop
                    if current_price <= product.target_price:
                        print(f"  🚨 PRICE DROP! ₹{current_price} <= ₹{product.target_price}")
                        # Get the user's email
                        user = User.query.get(product.user_id)
                        if user and user.email:
                            send_email_alert(display_title, current_price, product.target_price, product.url, user.email)
                    else:
                        print(f"  Still above target (₹{current_price} > ₹{product.target_price})")
                else:
                    print(f"  Could not fetch price for {product.name}")
                
                # Brief pause between products
                time.sleep(5)
        
        print(f"\nCycle complete. Sleeping for {CHECK_INTERVAL_SECONDS / 3600} hours...\n")
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()