from flask import Flask, render_template, request, redirect, url_for
import os
from werkzeug.utils import secure_filename
from aws_script import extract_text_from_bill

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'bill' not in request.files:
        return "No file selected", 400
    
    file = request.files['bill']
    
    if file.filename == '':
        return "No file selected", 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            extracted_data = extract_text_from_bill(filepath)
            return render_template('results.html',
                                filename=filename,
                                result=extracted_data,
                                image_url=f'uploads/{filename}')
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            return f"Error processing file: {str(e)}", 500
    
    return "Invalid file type. Allowed: PNG, JPG, JPEG, WEBP, PDF", 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)