from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
from werkzeug.utils import secure_filename
from aws_script import extract_text_from_bill
import json
from mongo_db import db_instance
from datetime import datetime, timezone
from bson import ObjectId
from datetime import datetime, timezone, timedelta

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ========== AUTHENTICATION ROUTES ==========

@app.route('/')
def landing():
    """Landing page for non-logged in users"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard after login"""
    return render_template('index.html', username=session.get('username'))

@app.route('/home')
def home():
    """Alias for dashboard"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('landing'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = db_instance.authenticate_user(email, password)
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('signup.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('signup.html')
        
        user_id, message = db_instance.create_user(username, email, password)
        
        if user_id:
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'error')
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('landing'))

# ========== BILL HISTORY ROUTES ==========

@app.route('/history')
@login_required
def history():
    """Main history page - FIXED timezone issue"""
    try:
        db = db_instance.get_db()
        user_id = session['user_id']
        
        print(f"🔍 Fetching history for user: {user_id}")
        
        # Get all bills for the user
        bills_cursor = db.bill_history.find({'user_id': user_id}).sort('bill_date', -1)
        bills = list(bills_cursor)
        
        print(f"📄 Found {len(bills)} bills in database")
        
        # Process each bill to match template expectations
        processed_bills = []
        for bill in bills:
            # Convert ObjectId to string
            bill['_id'] = str(bill['_id'])
            
            # FIXED: Simple timezone conversion for IST
            if 'bill_date' in bill and isinstance(bill['bill_date'], datetime):
                # Add 5 hours 30 minutes to convert UTC to IST
                utc_date = bill['bill_date']
                ist_date = utc_date + timedelta(hours=5, minutes=30)
                bill['bill_date'] = ist_date.strftime('%Y-%m-%d %H:%M')
            else:
                bill['bill_date'] = 'Unknown date'
            
            # Ensure all fields match template expectations
            bill_data = {
                '_id': bill['_id'],
                'bill_date': bill['bill_date'],
                'restaurant_name': bill.get('restaurant_name', 'Unknown Restaurant'),
                'total_amount': float(bill.get('total_amount', 0)),
                'split_among': int(bill.get('split_among', 0)),
                'image_path': bill.get('image_path', '')
            }
            
            # Get split details for this bill
            split_details = list(db.split_details.find({'bill_id': ObjectId(bill['_id'])}))
            processed_split_details = []
            
            for detail in split_details:
                # Create a new dictionary to avoid method conflicts
                processed_detail = {
                    '_id': str(detail['_id']),
                    'payee_name': detail.get('payee_name', 'Unknown'),
                    'amount': float(detail.get('amount', 0))
                }
                
                # FIX: Handle items field carefully - rename to avoid conflict
                items_data = detail.get('items')
                if isinstance(items_data, list) and items_data:
                    # Convert all items to strings and store as 'item_list'
                    processed_detail['item_list'] = [str(item) for item in items_data]
                else:
                    processed_detail['item_list'] = []
                
                processed_split_details.append(processed_detail)
            
            bill_data['split_details'] = processed_split_details
            processed_bills.append(bill_data)
        
        print(f"✅ Processed {len(processed_bills)} bills for display")
        return render_template('history.html', bills=processed_bills)
        
    except Exception as e:
        print(f"❌ Error fetching history: {e}")
        import traceback
        traceback.print_exc()
        flash('Error loading history. Please try again.', 'error')
        return render_template('history.html', bills=[])

@app.route('/api/bill-history')
@login_required
def get_bill_history():
    """API endpoint to get bill history as JSON - FIXED timezone issue"""
    try:
        db = db_instance.get_db()
        user_id = session['user_id']
        
        print(f"🔍 Fetching history for user: {user_id}")
        
        # Get all bills for the current user
        bills_cursor = db.bill_history.find({'user_id': user_id}).sort('bill_date', -1)
        bills_list = list(bills_cursor)
        
        print(f"📄 Found {len(bills_list)} bills in database")
        
        # Format the bills for the frontend
        formatted_bills = []
        for bill in bills_list:
            # Get split details for this bill to count participants
            split_details = list(db.split_details.find({'bill_id': bill['_id']}))
            
            # Count total items from split details
            total_items = 0
            for detail in split_details:
                if 'items' in detail:
                    total_items += len(detail['items'])
            
            # FIXED: Simple timezone conversion for IST
            bill_date = bill.get('bill_date', datetime.now(timezone.utc))
            if isinstance(bill_date, datetime):
                # Add 5 hours 30 minutes to convert UTC to IST
                ist_date = bill_date + timedelta(hours=5, minutes=30)
                created_at = ist_date.strftime('%Y-%m-%d %H:%M')
            else:
                created_at = 'Unknown date'
            
            formatted_bill = {
                'id': str(bill['_id']),
                'filename': bill.get('restaurant_name', 'Unknown Restaurant'),
                'total_amount': float(bill.get('total_amount', 0)),
                'participants': len(split_details),
                'items': total_items,
                'created_at': created_at,
                'image_path': bill.get('image_path', '')
            }
            formatted_bills.append(formatted_bill)
        
        print(f"✅ Sending {len(formatted_bills)} bills to frontend")
        return jsonify({'bills': formatted_bills})
        
    except Exception as e:
        print(f"❌ Error fetching history: {e}")
        return jsonify({'error': 'Failed to load bill history'}), 500
    
@app.route('/api/save-bill', methods=['POST'])
@login_required
def save_bill():
    """Save bill to history after splitting"""
    try:
        data = request.get_json()
        user_id = session['user_id']
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        db = db_instance.get_db()
        
        # Save to bill_history collection
        bill_data = {
            'user_id': user_id,
            'restaurant_name': data.get('restaurant_name', 'Unknown Restaurant'),
            'total_amount': float(data.get('total_amount', 0)),
            'split_among': int(data.get('participants', 0)),
            'bill_date': datetime.now(timezone.utc),
            'image_path': data.get('image_path', '')
        }
        
        bill_result = db.bill_history.insert_one(bill_data)
        bill_id = bill_result.inserted_id
        
        print(f"✅ Bill saved to history with ID: {bill_id}")
        
        return jsonify({
            'success': True,
            'bill_id': str(bill_id),
            'message': 'Bill saved to history successfully'
        })
        
    except Exception as e:
        print(f"❌ Error saving bill: {e}")
        return jsonify({'error': 'Failed to save bill to history'}), 500

@app.route('/api/delete-bill/<bill_id>', methods=['DELETE'])
@login_required
def delete_bill(bill_id):
    """Delete a bill from history"""
    try:
        db = db_instance.get_db()
        user_id = session['user_id']
        
        # Verify the bill belongs to the user
        bill = db.bill_history.find_one({'_id': ObjectId(bill_id), 'user_id': user_id})
        if not bill:
            return jsonify({'error': 'Bill not found'}), 404
        
        # Delete related split details
        db.split_details.delete_many({'bill_id': ObjectId(bill_id)})
        
        # Delete the bill
        db.bill_history.delete_one({'_id': ObjectId(bill_id)})
        
        return jsonify({'success': True, 'message': 'Bill deleted successfully'})
        
    except Exception as e:
        print(f"❌ Error deleting bill: {e}")
        return jsonify({'error': 'Failed to delete bill'}), 500

# ========== BILL UPLOAD & PROCESSING ROUTES ==========

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """Handle file upload and processing"""
    try:
        if 'bill' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('dashboard'))
        
        file = request.files['bill']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('dashboard'))
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            print(f"📸 Processing image: {filepath}")
            
            try:
                extracted_data = extract_text_from_bill(filepath)

                if not isinstance(extracted_data, dict):
                    extracted_data = {
                        'restaurant_name': 'Restaurant',
                        'items': [],
                        'taxes': [],
                        'subtotal': 0,
                        'total': 0
                    }
                
                print("✅ Bill extracted successfully")
                print("--- Extracted Data ---")
                print(json.dumps(extracted_data, indent=2))
                print("---------------------")
                
                # FIX: Use the correct image URL path
                return render_template(
                    'split.html',
                    restaurant=extracted_data.get('restaurant_name', 'Restaurant'),
                    items=extracted_data.get('items', []),
                    taxes=extracted_data.get('taxes', []),
                    subtotal=extracted_data.get('subtotal', 0),
                    total=extracted_data.get('total', 0),
                    image_url=f'/static/uploads/{filename}'  # FIXED: Added leading slash
                )
                
            except Exception as e:
                # Clean up the uploaded file if processing fails
                if os.path.exists(filepath):
                    os.remove(filepath)
                print(f"❌ Error processing file: {str(e)}")
                flash(f'Error processing file: {str(e)}', 'error')
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid file type. Allowed: PNG, JPG, JPEG, WEBP', 'error')
            return redirect(url_for('dashboard'))
            
    except Exception as e:
        print(f"❌ Error in upload route: {e}")
        flash('Error uploading file', 'error')
        return redirect(url_for('dashboard'))

@app.route('/calculate', methods=['POST'])
@login_required
def calculate_shares():
    """Calculate bill shares and save to history"""
    try:
        user_id = session['user_id']
        current_username = session['username']
        people_count = int(request.form.get('peopleCount', 2))
        
        # Get form data
        restaurant_name = request.form.get('restaurant_name', 'Unknown Restaurant')
        total_amount = float(request.form.get('total', 0))
        image_url = request.form.get('image_url', '')
        
        print(f"🔢 Calculating shares for {people_count} people, total: {total_amount}")
        print(f"👤 Current user: {current_username} (ID: {user_id})")
        
        # Process people and items
        people = []
        for i in range(1, people_count + 1):
            name = request.form.get(f'person_{i}_name', f'Person {i}')
            people.append({
                'name': name,
                'items': [],
                'total': 0.0
            })
        
        # Process items
        all_items_data = {}
        item_index = 0
        while True:
            item_name_key = f'item_{item_index}_name'
            item_price_key = f'item_{item_index}_price'
            
            item_name = request.form.get(item_name_key)
            item_price_str = request.form.get(item_price_key)

            if item_name is None:
                break
            
            try:
                item_price = float(item_price_str) if item_price_str else 0.0
            except (ValueError, TypeError):
                item_price = 0.0 
            
            all_items_data[item_index] = {'name': item_name, 'price': item_price}
            item_index += 1

        print(f"📦 Processing {len(all_items_data)} items")

        # Calculate shares
        for person_idx in range(1, people_count + 1):
            for item_idx in range(len(all_items_data)):
                checkbox_name = f'person_{person_idx}_item_{item_idx}'
                if request.form.get(checkbox_name) == 'on': 
                    item = all_items_data.get(item_idx)
                    if item:
                        people[person_idx - 1]['items'].append({
                            'name': item['name'],
                            'price': item['price']
                        })
                        people[person_idx - 1]['total'] += item['price']

        # Calculate remaining total and distribute
        items_total_assigned = sum(p['total'] for p in people)
        remaining_total = total_amount - items_total_assigned
        
        print(f"💰 Items total: {items_total_assigned}, Remaining: {remaining_total}")
        
        if people_count > 0 and remaining_total > 0:
            share_of_remaining = remaining_total / people_count
            for person in people:
                person['total'] += share_of_remaining
                person['formatted_total'] = "{:.2f}".format(person['total'])
        else:
            for person in people:
                person['formatted_total'] = "{:.2f}".format(person['total'])

        grand_total_calculated = sum(person['total'] for person in people)

        # ========== SAVE TO DATABASE ==========
        db = db_instance.get_db()
        
        # 1. Save to bill_history
        bill_data = {
            'user_id': user_id,
            'restaurant_name': restaurant_name,
            'total_amount': total_amount,
            'split_among': people_count,
            'bill_date': datetime.now(timezone.utc),
            'image_path': image_url
        }
        
        bill_result = db.bill_history.insert_one(bill_data)
        bill_id = bill_result.inserted_id
        
        print(f"✅ Bill saved to history with ID: {bill_id}")
        
        # 2. Save split details (NOTIFICATION PART REMOVED)
        for person in people:
            split_data = {
                'bill_id': bill_id,
                'payer_id': user_id,
                'payee_name': person['name'],
                'amount': person['total'],
                'items': [item['name'] for item in person['items']]
            }
            db.split_details.insert_one(split_data)
        
        flash('Bill split and saved to history successfully!', 'success')
        
        return render_template(
            'results.html',
            people=people,
            grand_total="{:.2f}".format(grand_total_calculated),
            original_total="{:.2f}".format(total_amount),
            edited_total="{:.2f}".format(total_amount),
            receipt_path=image_url.replace('/static/', '')  # Fix for results page image
        )
        
    except Exception as e:
        print(f"❌ Error in calculate_shares: {e}")
        import traceback
        traceback.print_exc()
        flash('Error processing bill split', 'error')
        return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)