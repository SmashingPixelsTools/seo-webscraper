# SEO Webscraper

A Flask-based tool to extract SEO-relevant content from web pages including:
- Page Title
- Meta Description
- Headings (H1–H4)

## Usage

You can input one or more URLs, or upload a sitemap.xml file. The app will output a downloadable CSV file containing the scraped data.

## Run Locally

```bash
pip install -r requirements.txt
python app.py
```

## Deployment

Compatible with Render.com. Use the provided `.render.yaml` to deploy directly from GitHub.
