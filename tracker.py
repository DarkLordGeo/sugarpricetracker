"""
price_watch.py

Scrapes a product's price/title from 2nabiji.ge and sends a styled
HTML email via Gmail with the current price.

SETUP (one-time):
1. Go to https://myaccount.google.com/apppasswords
   (Requires 2-Step Verification enabled on your Google account.)
2. Generate an "App Password" for "Mail".
3. Set GMAIL_ADDRESS / GMAIL_APP_PASSWORD / TO_ADDRESS as environment
   variables (see .env.example) — never hardcode real credentials here.

INSTALL:
    pip install requests beautifulsoup4 python-dotenv
    (smtplib, email, re, os are all in Python's standard library)

RUN:
    python3 price_watch.py
"""

import os
import bs4
import requests
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Loads variables from a local .env file if python-dotenv is installed and
# a .env file is present. In GitHub Actions, secrets are already injected
# as real environment variables, so this is a no-op there — harmless either way.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ---------------------------------------------------------------------------
# CONFIG — read from environment variables (see .env.example)
# ---------------------------------------------------------------------------
GMAIL_ADDRESS = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
TO_ADDRESS = os.environ["TO_ADDRESS"]

PRODUCT_URL = "https://2nabiji.ge/ge/product/shaqari-zoge"


# ---------------------------------------------------------------------------
# SCRAPING
# ---------------------------------------------------------------------------
def fetchPrices(url: str = PRODUCT_URL) -> dict:
    """Scrapes title, price, and image URL for a 2nabiji.ge product page.

    Returns a dict: {"title": str, "price": float, "image_url": str, "url": str}
    """
    page_html = requests.get(url)
    soup = bs4.BeautifulSoup(page_html.text, "html.parser")
    next_data_script = soup.find("script", id="__NEXT_DATA__").string

    # Product name (title)
    title_match = re.search(r'"title"\s*:\s*"((?:[^"\\]|\\.)*)"', next_data_script)
    title = title_match.group(1).replace('\\"', '"') if title_match else None

    # Price (from "stock": {..., "price": X})
    price_match = re.search(r'"stock"\s*:\s*\{[^}]*?"price"\s*:\s*([\d.]+)', next_data_script)
    price = float(price_match.group(1)) if price_match else None

    # Image URL (from og:image meta tag)
    image_url = None
    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        image_url = og_image["content"]

    result = {"title": title, "price": price, "image_url": image_url, "url": url}
    print(result)
    return result


# ---------------------------------------------------------------------------
# EMAIL BUILDING
# ---------------------------------------------------------------------------
def build_html_email(product_name: str, price: float, url: str, image_url: str = "") -> str:
    """Returns a fully self-contained, email-client-friendly HTML string.

    Table-based layout with inline styles is used (not <style> blocks /
    flexbox) since that's what actually renders consistently across
    Gmail, Outlook, Apple Mail, etc.
    """
    image_block = (
        f'<img src="{image_url}" alt="{product_name}" '
        f'style="width:100%;max-width:560px;border-radius:12px 12px 0 0;display:block;" />'
        if image_url else ""
    )

    html = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Price Update: {product_name}</title>
</head>
<body style="margin:0; padding:0; background-color:#f2f4f6; font-family:'Segoe UI', Helvetica, Arial, sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f2f4f6; padding:32px 0;">
    <tr>
      <td align="center">
        <table role="presentation" width="560" cellpadding="0" cellspacing="0"
               style="background-color:#ffffff; border-radius:12px; overflow:hidden; box-shadow:0 4px 16px rgba(0,0,0,0.08);">

          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#11A149,#0d7a37); padding:24px 32px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="color:#ffffff; font-size:22px; font-weight:700; letter-spacing:0.3px;">
                    🛒 Price Watch
                  </td>
                  <td align="right" style="color:#d9f4e6; font-size:13px;">
                    2NABIJI
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Product image -->
          {"<tr><td>" + image_block + "</td></tr>" if image_block else ""}

          <!-- Body -->
          <tr>
            <td style="padding:32px;">
              <p style="margin:0 0 8px 0; font-size:13px; color:#8a94a6; text-transform:uppercase; letter-spacing:0.6px;">
                Product
              </p>
              <h1 style="margin:0 0 20px 0; font-size:22px; color:#1c1f26; line-height:1.3;">
                {product_name}
              </h1>

              <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                     style="background-color:#f7f9fa; border-radius:10px; padding:20px; margin-bottom:24px;">
                <tr>
                  <td style="padding:0 20px;">
                    <p style="margin:0; font-size:13px; color:#8a94a6;">Current price</p>
                    <p style="margin:4px 0 0 0; font-size:32px; font-weight:700; color:#11A149;">
                      {price:.2f} ₾
                    </p>
                  </td>
                </tr>
              </table>

              <table role="presentation" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="border-radius:8px; background-color:#11A149;">
                    <a href="{url}" target="_blank"
                       style="display:inline-block; padding:14px 28px; font-size:15px; font-weight:600;
                              color:#ffffff; text-decoration:none; border-radius:8px;">
                      View Product →
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:20px 32px; background-color:#f7f9fa; border-top:1px solid #eceef1;">
              <p style="margin:0; font-size:12px; color:#9aa4b2; line-height:1.5;">
                You're receiving this because you're tracking this product's price.
                <br />
                Sent automatically — no reply needed.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
    return html


# ---------------------------------------------------------------------------
# EMAIL SENDING
# ---------------------------------------------------------------------------
def send_html_email(to_address: str, subject: str, html_content: str, plain_fallback: str = ""):
    """Sends an HTML email via Gmail SMTP (SSL, port 465)."""
    msg = MIMEMultipart("alternative")
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to_address
    msg["Subject"] = subject

    if not plain_fallback:
        plain_fallback = "This email requires HTML support to view properly."
    msg.attach(MIMEText(plain_fallback, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, to_address, msg.as_string())

    print(f"✅ Email sent to {to_address}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    data = fetchPrices(PRODUCT_URL)

    if data["price"] is None or data["title"] is None:
        print("⚠️ Could not extract price/title — skipping email.")
        return

    html = build_html_email(
        product_name=data["title"],
        price=data["price"],
        url=data["url"],
        image_url=data["image_url"] or "",
    )

    send_html_email(
        to_address=TO_ADDRESS,
        subject=f"🛒 Price Update: {data['title']}",
        html_content=html,
        plain_fallback=f"{data['title']} is now {data['price']:.2f} GEL. View: {data['url']}",
    )


if __name__ == "__main__":
    main()