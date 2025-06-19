# ... (everything else remains the same)

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
