import os
import io
import csv
import re
import ssl
import smtplib
import pdfkit
import requests
import urllib.parse
from flask import Flask, render_template, request, send_file
from bs4 import BeautifulSoup
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

app = Flask(__name__)

EMAIL_ADDRESS = 'smashingpixelsservice@gmail.com'
EMAIL_PASSWORD = os.environ.get('EMAIL_APP_PASSWORD')
BCC_EMAIL = 'trevor@smashingpixels.ca'

# Extract the base domain for PDF naming
def get_domain_name(url):
    try:
        parsed_url = urllib.parse.urlparse(url)
        domain = parsed_url.netloc.replace('www.', '')
        return re.sub(r'[^a-zA-Z0-9_-]', '', domain)
    except:
        return "website"

# Improved Schema Detection
def extract_schema(soup):
    schema_data = []
    for script in soup.find_all("script", type="application/ld+json"):
        content = script.string or script.text
        if content:
            try:
                data = content.strip().replace('\n', '')
                if len(data) > 0:
                    schema_data.append(data)
            except Exception:
                continue
    return schema_data if schema_data else None

# Truncate with 'Show more'
def truncate_text(text, max_lines=5):
    lines = text.split('\n')
    if len(lines) > max_lines:
        visible = '\n'.join(lines[:max_lines])
        hidden = '\n'.join(lines[max_lines:])
        return f"<div class='truncate'>{visible}</div><div class='hidden'>{hidden}</div><a href='#' class='show-more'>Show more</a>"
    return text

def scrape_page(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'lxml')

        title = soup.title.string.strip() if soup.title else 'N/A'

        meta_desc_tag = soup.find("meta", attrs={"name": "description"})
        meta_desc = meta_desc_tag["content"].strip() if meta_desc_tag and "content" in meta_desc_tag.attrs else "N/A"

        headings = {}
        for tag in ['h1', 'h2', 'h3', 'h4']:
            tags = soup.find_all(tag)
            content = [t.get_text(strip=True) for t in tags]
            joined = '\n'.join(content)
            headings[tag.upper()] = truncate_text(joined)

        schema = extract_schema(soup)

        suggestions = []
        if not soup.find('h1'):
            suggestions.append("Your page is missing a main headline (H1). Add a clear, descriptive title near the top.")
        if not meta_desc or meta_desc == 'N/A':
            suggestions.append("Add a meta description to help search engines and users understand your page.")

        return {
            'url': url,
            'title': title,
            'meta_description': meta_desc,
            'headings': headings,
            'schema': schema,
            'suggestions': suggestions
        }
    except Exception as e:
        return {'url': url, 'error': str(e)}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.form
    urls = []
    if 'urls' in data and data['urls']:
        urls.extend([url.strip() for url in data['urls'].split('\n') if url.strip()])

    if 'sitemap' in request.files:
        sitemap_file = request.files['sitemap']
        if sitemap_file.filename.endswith('.xml'):
            sitemap_content = sitemap_file.read().decode('utf-8')
            sitemap_soup = BeautifulSoup(sitemap_content, 'xml')
            loc_tags = sitemap_soup.find_all('loc')
            urls.extend([tag.text.strip() for tag in loc_tags])

    if not urls:
        return "No URLs provided."

    results = [scrape_page(url) for url in urls]
    return render_template('results.html', results=results)

@app.route('/send_report', methods=['POST'])
def send_report():
    name = request.form.get('name')
    email = request.form.get('email')
    html = request.form.get('html')
    url = request.form.get('url')

    try:
        pdf = pdfkit.from_string(html, False)
        send_email_with_pdf(email, pdf, name, url)
        return {'status': 'success'}
    except Exception as e:
        return {'status': 'fail', 'error': str(e)}

def send_email_with_pdf(recipient_email, pdf_data, name=None, url=None):
    try:
        site_name = get_domain_name(url or '')
        filename = f"{site_name}_SEO-Report.pdf"

        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = recipient_email
        msg['Bcc'] = BCC_EMAIL
        msg['Subject'] = "Your Smashing Pixels SEO Report"

        body_text = f"Hi {name or 'there'},\n\nAttached is your SEO analysis report from Smashing Pixels.\n\nRegards,\nSmashing Pixels"
        msg.attach(MIMEText(body_text, 'plain'))

        part = MIMEApplication(pdf_data, Name=filename)
        part['Content-Disposition'] = f'attachment; filename=\"{filename}\"'
        msg.attach(part)

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)