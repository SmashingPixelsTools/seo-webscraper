
from flask import Flask, request, render_template
from bs4 import BeautifulSoup
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse
import re
import os
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from collections import Counter
from jinja2 import Environment, FileSystemLoader
import pdfkit

app = Flask(__name__)
results_cache = []

def clean(text):
    if not text:
        return 'N/A'
    return text.replace('\n', ' ').replace('\r', '').replace(',', ';').strip()

def extract_keywords(text):
    return set(re.findall(r'\b\w{4,}\b', text.lower()))

def generate_suggestions(title, meta_desc, h1s, h2s):
    tips = []
    if not h1s:
        tips.append("❌ Your page is missing a main headline (H1). Add a clear, descriptive title near the top.")
    elif len(h1s) > 1:
        tips.append("⚠️ You have more than one H1 headline. It's best to use only one to define the page's main topic.")
    if meta_desc == 'N/A':
        tips.append("❌ Add a meta description to help search engines and users understand your page.")
    elif len(meta_desc.strip()) < 25:
        tips.append("⚠️ Your meta description is very short. Try writing a 1–2 sentence summary to help Google and users.")
    if title == 'N/A':
        tips.append("❌ Your page is missing a title tag. This appears in search engine results and browser tabs.")
    if not h2s:
        tips.append("ℹ️ Consider breaking up your content with subheadings (H2s) to make it easier to scan.")
    if len(title) > 60:
        tips.append("⚠️ Your title is quite long. Try keeping it under 60 characters to avoid getting cut off in search results.")
    if len(meta_desc) > 160:
        tips.append("⚠️ Your meta description is long. Try to keep it around 150–160 characters.")
    if h1s and title != 'N/A':
        h1_keywords = extract_keywords(' '.join(h1s))
        title_keywords = extract_keywords(title)
        if not h1_keywords.intersection(title_keywords):
            tips.append("⚠️ Your main headline (H1) doesn't reflect the page title. Align them for better SEO.")
    return tips

def scrape_page(url):
    try:
        if not isinstance(url, str):
            url = str(url)

        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        title = soup.title.string.strip() if soup.title else 'N/A'
        meta_desc_tag = soup.find('meta', attrs={'name': re.compile('description', re.I)})
        meta_desc = meta_desc_tag['content'].strip() if meta_desc_tag and 'content' in meta_desc_tag.attrs else 'N/A'

        headers_tags = {'h1': [], 'h2': [], 'h3': [], 'h4': []}
        for tag in soup.find_all(['h1', 'h2', 'h3', 'h4']):
            headers_tags[tag.name].append(tag.get_text(strip=True))

        suggestions = generate_suggestions(title, meta_desc, headers_tags['h1'], headers_tags['h2'])

        return {
            'url': url,
            'title': clean(title),
            'meta_description': clean(meta_desc),
            'h1': clean('; '.join(headers_tags['h1'])),
            'h2': clean('; '.join(headers_tags['h2'])),
            'h3': clean('; '.join(headers_tags['h3'])),
            'h4': clean('; '.join(headers_tags['h4'])),
            'raw_h1s': headers_tags['h1'],
            'suggestions': suggestions
        }
    except Exception as e:
        return {
            'url': url,
            'title': 'Error',
            'meta_description': clean(str(e)),
            'h1': 'N/A',
            'h2': 'N/A',
            'h3': 'N/A',
            'h4': 'N/A',
            'raw_h1s': [],
            'suggestions': ["⚠️ Could not reach or analyze the page. Please check the URL."]
        }

def parse_sitemap(file_content, base_url=None):
    urls = []
    try:
        root = ET.fromstring(file_content)
        namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        for url_elem in root.findall('.//sitemap:loc', namespace):
            text = url_elem.text.strip()
            if base_url and not text.startswith(('http://', 'https://')):
                text = urljoin(base_url, text)
            urls.append(str(text))
    except Exception as e:
        print(f"Error parsing sitemap: {e}")
    return urls

def generate_pdf_from_results(data):
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('pdf_template.html')
    html_content = template.render(data=data)
    pdf_file = pdfkit.from_string(html_content, False)
    return pdf_file

def get_domain_name(url):
    domain = urlparse(url).netloc
    domain = re.sub(r'^www\.', '', domain)
    domain = domain.split('.')[0]
    return re.sub(r'[^a-zA-Z0-9_-]', '', domain).capitalize()

def send_email_with_pdf(recipient_email, pdf_data, name=None, url=None):
    try:
        site_name = get_domain_name(url or '')
        filename = f"{site_name}-SEO-Report.pdf"

        msg = MIMEMultipart()
        msg['From'] = 'smashingpixelsservice@gmail.com'
        msg['To'] = recipient_email
        msg['Bcc'] = 'trevor@smashingpixels.ca'
        msg['Subject'] = 'Your Smashing Pixels SEO Report'

        body_text = f"Hi {name or 'there'},\n\nAttached is your SEO analysis report from Smashing Pixels.\n\nRegards,\nSmashing Pixels"
        msg.attach(MIMEText(body_text, 'plain'))

        part = MIMEApplication(pdf_data, Name=filename)
        part['Content-Disposition'] = f'attachment; filename="{filename}"'
        msg.attach(part)

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login('smashingpixelsservice@gmail.com', 'EMAIL_APP_PASSWORD')
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

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
        if sitemap_file.filename:
            sitemap_content = sitemap_file.read().decode('utf-8')
            urls.extend(parse_sitemap(sitemap_content))

    if not urls:
        return render_template('results.html', data=[{
            'url': 'N/A',
            'title': 'No URLs Submitted',
            'meta_description': 'N/A',
            'h1': 'N/A',
            'h2': 'N/A',
            'h3': 'N/A',
            'h4': 'N/A',
            'suggestions': ['Please enter at least one URL.']
        }])

    results = [scrape_page(url) for url in urls if isinstance(url, str) and url.startswith(('http://', 'https://'))]
    global results_cache
    results_cache = results

    all_h1s = [r['h1'] for r in results if r['h1'] != 'N/A']
    dupes = [item for item, count in Counter(all_h1s).items() if count > 1]
    if len(urls) > 1:
        for r in results:
            if r['h1'] in dupes:
                r['suggestions'].append("⚠️ This H1 appears on multiple pages. Try to make each page's main headline unique.")

    return render_template('results.html', data=results)

@app.route('/send_report', methods=['POST'])
def send_report():
    name = request.form.get('name')
    email = request.form.get('email')
    if not email or not name:
        return "Name and email are required", 400

    if not results_cache:
        return "No results available to send.", 400

    pdf_data = generate_pdf_from_results(results_cache)
    if send_email_with_pdf(email, pdf_data, name, results_cache[0]['url']):
        return render_template('results.html', data=results_cache, message="✅ Report sent to your email.")
    else:
        return render_template('results.html', data=results_cache, message="❌ Failed to send email. Try again later.")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
