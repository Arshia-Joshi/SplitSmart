from flask import Flask, render_template, request
import os
from aws_script import extract_text_from_bill  

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'bill' not in request.files:
        return "No file part", 400

    file = request.files['bill']
    if file.filename == '':
        return "No selected file", 400

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    result = extract_text_from_bill(file_path)
    return f"<pre>{result}</pre>"

if __name__ == '__main__':
    app.run(debug=True)
