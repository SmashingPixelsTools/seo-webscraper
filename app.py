
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

        h1s = headers_tags['h1']
        suggestions = []
        if not h1s:
            suggestions.append("Missing H1 tag.")
        elif len(h1s) > 1:
            suggestions.append("Multiple H1 tags detected.")
        if meta_desc == 'N/A':
            suggestions.append("Missing meta description.")
        if title == 'N/A':
            suggestions.append("Missing title tag.")
        if not headers_tags['h2']:
            suggestions.append("Consider adding H2 subheadings.")

        return {
            'url': url,
            'title': clean(title),
            'meta_description': clean(meta_desc),
            'h1': clean('; '.join(h1s)),
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
            'suggestions': ["Page could not be reached or parsed."]
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
