
from flask import Flask, request, jsonify, send_file, render_template
from bs4 import BeautifulSoup
import requests
import pandas as pd
import xml.etree.ElementTree as ET
from urllib.parse import urljoin
import io
import re
import os

app = Flask(__name__)

def clean(text):
    if not text:
        return 'N/A'
    return text.replace('\n', ' ').replace('\r', '').replace(',', ';').strip()

def scrape_page(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        title = soup.title.string.strip() if soup.title else 'N/A'

        meta_desc = soup.find('meta', attrs={'name': re.compile('description', re.I)})
        meta_desc = meta_desc['content'].strip() if meta_desc and 'content' in meta_desc.attrs else 'N/A'

        headers_tags = {'h1': [], 'h2': [], 'h3': [], 'h4': []}
        for tag in soup.find_all(['h1', 'h2', 'h3', 'h4']):
            headers_tags[tag.name].append(tag.get_text(strip=True))

        return {
            'url': url,
            'title': clean(title),
            'meta_description': clean(meta_desc),
            'h1': clean('; '.join(headers_tags['h1'])),
            'h2': clean('; '.join(headers_tags['h2'])),
            'h3': clean('; '.join(headers_tags['h3'])),
            'h4': clean('; '.join(headers_tags['h4']))
        }
    except Exception as e:
        return {
            'url': url,
            'title': 'Error',
            'meta_description': clean(str(e)),
            'h1': 'N/A',
            'h2': 'N/A',
            'h3': 'N/A',
            'h4': 'N/A'
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
        return jsonify({'error': 'No valid URLs provided'}), 400

    results = []
    for url in urls:
        if url.startswith(('http://', 'https://')):
            results.append(scrape_page(url))

    df = pd.DataFrame(results)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)

    csv_buffer.seek(0)
    return send_file(
        io.BytesIO(csv_buffer.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='seo_scraped_data.csv'
    )

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
