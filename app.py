
import os
import re
import smtplib
from flask import Flask, render_template, request, send_file
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import requests
import pdfkit

app = Flask(__name__)

def extract_schema_data(soup):
    schema_tags = soup.find_all("script", type="application/ld+json")
    if not schema_tags:
        return "N/A"
    schema_content = []
    for tag in schema_tags:
        content = tag.get_text(strip=True)
        if content:
            schema_content.append(content)
    return "

".join(schema_content) if schema_content else "N/A"

def get_domain_name(url):
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        return re.sub(r"^www\.", "", domain)
    except Exception:
        return ""

def scrape_page(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "lxml")

    title_tag = soup.find("title")
    title = title_tag.text.strip() if title_tag else "N/A"

    meta_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    meta_description = meta_tag["content"].strip() if meta_tag and meta_tag.has_attr("content") else "N/A"

    headings = {}
    for tag in ["h1", "h2", "h3", "h4"]:
        headings[tag.upper()] = [h.get_text(strip=True) for h in soup.find_all(tag)]

    schema = extract_schema_data(soup)

    suggestions = []
    if not headings["H1"]:
        suggestions.append("Your page is missing a main headline (H1). Add a clear, descriptive title near the top.")
    if meta_description == "N/A":
        suggestions.append("Add a meta description to help search engines and users understand your page.")

    return {
        "url": url,
        "title": title,
        "meta_description": meta_description,
        "headings": headings,
        "schema": schema,
        "suggestions": suggestions,
    }

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/scrape", methods=["POST"])
def scrape():
    data = request.form
    urls = []

    if "urls" in data and data["urls"]:
        urls.extend([url.strip() for url in data["urls"].split("\n") if url.strip()])

    if "sitemap" in request.files:
        sitemap_file = request.files["sitemap"]
        if sitemap_file.filename:
            sitemap_content = sitemap_file.read().decode("utf-8")
            sitemap_soup = BeautifulSoup(sitemap_content, "xml")
            sitemap_urls = [loc.text for loc in sitemap_soup.find_all("loc")]
            urls.extend(sitemap_urls)

    if not urls:
        return "No valid URLs provided.", 400

    results = [scrape_page(url) for url in urls]

    return render_template("results.html", data=results)

@app.route("/download_pdf", methods=["POST"])
def download_pdf():
    html = request.form["html"]
    pdf_path = "/tmp/seo_report.pdf"
    pdfkit.from_string(html, pdf_path)
    return send_file(pdf_path, as_attachment=True, download_name="SEO_Report.pdf")

if __name__ == "__main__":
    app.run(debug=True)
