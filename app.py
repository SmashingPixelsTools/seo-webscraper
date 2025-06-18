
from flask import Flask, request, render_template
from bs4 import BeautifulSoup
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urljoin
import re
import os

app = Flask(__name__)

def clean(text):
    if not text:
        return 'N/A'
    return text.replace('\n', ' ').replace('\r', '').replace(',', ';').strip()

def generate_suggestions(title, meta_desc, h1s, h2s):
    tips = []
    if not h1s:
        tips.append("❌ Your page is missing a main headline (H1). Add a clear, descriptive title near the top.")
    elif len(h1s) > 1:
        tips.append("⚠️ You have more than one H1 headline. It's best to use only one to define the page's main topic.")
    if meta_desc == 'N/A':
        tips.append("❌ Add a meta description to help search engines and users understand your page.")
    if title == 'N/A':
        tips.append("❌ Your page is missing a title tag. This appears in search engine results and browser tabs.")
    if not h2s:
        tips.append("ℹ️ Consider breaking up your content with subheadings (H2s) to make it easier to scan.")
    if len(title) > 60:
        tips.append("⚠️ Your title is quite long. Try keeping it under 60 characters to avoid getting cut off in search results.")
    if len(meta_desc) > 160:
        tips.append("⚠️ Your meta description is long. Try to keep it around 150–160 characters.")
    return tips

def scrape_page(url):
    try:
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
            'suggestions': ["⚠️ Could not reach or analyze the page. Please check the URL."]
        }

def parse_sitemap(file_content, base_url=None):
    urls = []
    try:
        root = ET.fromstring(file_content)
        namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        for url_elem in root.findall('.//sitemap:loc', namespace):
            url = url_elem.text.strip()
            if base_url and not url.startswith(('http://', 'https://')):
                url = urljoin(base_url, url)
            urls.append(url)
    except Exception as e:
        print(f"Error parsing sitemap: {e}")
    return urls

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

    results = []
    for url in urls:
        if url.startswith(('http://', 'https://')):
            results.append(scrape_page(url))

    return render_template('results.html', data=results)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
