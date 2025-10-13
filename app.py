from flask import Flask, render_template, request, jsonify, send_file
import sqlite3
import os
import json
from datetime import datetime
import uuid

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DATABASE'] = 'bills.db'

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def init_database():
    """Initialize the SQLite database"""
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    
    # Create bills table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bills (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            total_amount REAL NOT NULL,
            participants INTEGER NOT NULL,
            items INTEGER NOT NULL,
            split_details TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/history')
def history():
    return render_template('bill_history.html')

@app.route('/api/bill-history')
def get_bill_history():
    """API endpoint to get bill history"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all bills ordered by creation date (newest first)
        cursor.execute('''
            SELECT id, filename, total_amount, participants, items, created_at 
            FROM bills 
            ORDER BY created_at DESC
        ''')
        
        bills = cursor.fetchall()
        conn.close()
        
        # Convert to list of dictionaries
        bill_list = []
        for bill in bills:
            bill_list.append({
                'id': bill['id'],
                'filename': bill['filename'],
                'total_amount': bill['total_amount'],
                'participants': bill['participants'],
                'items': bill['items'],
                'created_at': bill['created_at']
            })
        
        return jsonify({'bills': bill_list})
        
    except Exception as e:
        print(f"Error fetching bill history: {e}")
        return jsonify({'error': 'Failed to load bill history'}), 500

@app.route('/api/save-bill', methods=['POST'])
def save_bill():
    """Save bill data to database"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Generate unique ID for the bill
        bill_id = str(uuid.uuid4())
        
        # Extract data from request
        filename = data.get('filename', 'Unknown Bill')
        total_amount = float(data.get('total_amount', 0))
        participants = int(data.get('participants', 0))
        items = int(data.get('items', 0))
        split_details = json.dumps(data.get('split_details', {}))
        
        # Save file if provided
        file_path = ""
        if 'file_content' in data:
            file_extension = os.path.splitext(filename)[1] if '.' in filename else '.txt'
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{bill_id}{file_extension}")
            with open(file_path, 'w') as f:
                f.write(data['file_content'])
        
        # Save to database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO bills (id, filename, file_path, total_amount, participants, items, split_details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (bill_id, filename, file_path, total_amount, participants, items, split_details))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'bill_id': bill_id,
            'message': 'Bill saved successfully'
        })
        
    except Exception as e:
        print(f"Error saving bill: {e}")
        return jsonify({'error': 'Failed to save bill'}), 500

@app.route('/api/delete-bill/<bill_id>', methods=['DELETE'])
def delete_bill(bill_id):
    """Delete a bill from history"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First get file path to delete the file
        cursor.execute('SELECT file_path FROM bills WHERE id = ?', (bill_id,))
        bill = cursor.fetchone()
        
        if bill:
            file_path = bill['file_path']
            # Delete file if it exists
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            
            # Delete from database
            cursor.execute('DELETE FROM bills WHERE id = ?', (bill_id,))
            conn.commit()
        
        conn.close()
        
        return jsonify({'success': True, 'message': 'Bill deleted successfully'})
        
    except Exception as e:
        print(f"Error deleting bill: {e}")
        return jsonify({'error': 'Failed to delete bill'}), 500

@app.route('/bill-details/<bill_id>')
def bill_details(bill_id):
    """Page to view bill details"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM bills WHERE id = ?', (bill_id,))
        bill = cursor.fetchone()
        conn.close()
        
        if bill:
            return render_template('bill_details.html', bill=bill)
        else:
            return "Bill not found", 404
            
    except Exception as e:
        print(f"Error loading bill details: {e}")
        return "Error loading bill details", 500

@app.route('/api/bill-details/<bill_id>')
def get_bill_details(bill_id):
    """API endpoint to get bill details"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM bills WHERE id = ?', (bill_id,))
        bill = cursor.fetchone()
        conn.close()
        
        if bill:
            bill_dict = dict(bill)
            bill_dict['split_details'] = json.loads(bill_dict['split_details'])
            return jsonify(bill_dict)
        else:
            return jsonify({'error': 'Bill not found'}), 404
            
    except Exception as e:
        print(f"Error fetching bill details: {e}")
        return jsonify({'error': 'Failed to load bill details'}), 500

# Your existing bill splitting routes...
@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and bill splitting"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Save the uploaded file
        filename = file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Process the bill (your existing bill splitting logic)
        # This is where you would add your OCR and bill splitting code
        split_result = process_bill(file_path)
        
        # Save the bill to history
        save_result = save_bill_to_history(filename, file_path, split_result)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'split_result': split_result,
            'bill_id': save_result.get('bill_id')
        })
        
    except Exception as e:
        print(f"Error processing bill: {e}")
        return jsonify({'error': 'Failed to process bill'}), 500

def process_bill(file_path):
    """Mock bill processing function - replace with your actual implementation"""
    # This should contain your OCR and bill splitting logic
    # For now, return mock data
    return {
        'total_amount': 150.75,
        'participants': 4,
        'items': 12,
        'split_details': {
            'Alice': 45.25,
            'Bob': 35.50,
            'Charlie': 40.00,
            'Diana': 30.00
        }
    }

def save_bill_to_history(filename, file_path, split_result):
    """Save bill to history database"""
    try:
        bill_id = str(uuid.uuid4())
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO bills (id, filename, file_path, total_amount, participants, items, split_details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            bill_id,
            filename,
            file_path,
            split_result['total_amount'],
            split_result['participants'],
            split_result['items'],
            json.dumps(split_result['split_details'])
        ))
        
        conn.commit()
        conn.close()
        
        return {'success': True, 'bill_id': bill_id}
        
    except Exception as e:
        print(f"Error saving bill to history: {e}")
        return {'success': False, 'error': str(e)}

if __name__ == '__main__':
    init_database()
    app.run(debug=True, port=5000)