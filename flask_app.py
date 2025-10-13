from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
from werkzeug.utils import secure_filename
from aws_script import extract_text_from_bill
import json
from mongo_db import db_instance
from datetime import datetime
from bson import ObjectId

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

# ========== PROTECTED ROUTES (REQUIRE LOGIN) ==========

@app.route('/upload', methods=['POST'])
@login_required
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

            if not isinstance(extracted_data, dict):
                extracted_data = {
                    'restaurant_name': 'Extraction Failed',
                    'items': [],
                    'taxes': [],
                    'subtotal': None,
                    'total': None
                }
            
            print("--- Extracted Data for split.html ---")
            print(json.dumps(extracted_data, indent=4))
            print("-------------------------------------")

            return render_template(
                'split.html',
                restaurant=extracted_data.get('restaurant_name', 'Restaurant'),
                items=extracted_data.get('items', []),
                taxes=extracted_data.get('taxes', []),
                subtotal=extracted_data.get('subtotal'),
                total=extracted_data.get('total'),
                image_url=f'uploads/{filename}'
            )
            
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            print(f"Error processing file in Flask: {str(e)}")
            return f"Error processing file: {str(e)}", 500
    
    return "Invalid file type. Allowed: PNG, JPG, JPEG, WEBP", 400

@app.route('/calculate', methods=['POST'])
@login_required
def calculate_shares():
    user_id = session['user_id']
    people_count = int(request.form.get('peopleCount', 2))
    
    people = []
    for i in range(1, people_count + 1):
        name = request.form.get(f'person_{i}_name', f'Person {i}')
        people.append({
            'name': name,
            'items': [],
            'total': 0.0
        })
    
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
            item_price = float(item_price_str)
        except (ValueError, TypeError):
            item_price = 0.0 
        
        all_items_data[item_index] = {'name': item_name, 'price': item_price}
        item_index += 1

    hidden_subtotal = float(request.form.get('hidden_subtotal', 0.0))
    hidden_total = float(request.form.get('hidden_total', 0.0))
    taxes_json = request.form.get('hidden_taxes', '[]')
    try:
        hidden_taxes = json.loads(taxes_json)
    except json.JSONDecodeError:
        hidden_taxes = []

    subtotal_str = request.form.get('subtotal')
    try:
        subtotal = float(subtotal_str) if subtotal_str else hidden_subtotal
    except ValueError:
        subtotal = hidden_subtotal

    total_str = request.form.get('total')
    try:
        total = float(total_str) if total_str else hidden_total
    except ValueError:
        total = hidden_total

    taxes = []
    i = 1
    while True:
        amount_key = f"tax_amount_{i}"
        perc_key = f"tax_percentage_{i}"
        tax_amount_str = request.form.get(amount_key)
        if tax_amount_str is None:
            break
        try:
            tax_amount = float(tax_amount_str)
        except ValueError:
            tax_amount = 0.0
        tax_percentage_str = request.form.get(perc_key)
        tax_percentage = None
        if tax_percentage_str:
            try:
                tax_percentage = float(tax_percentage_str)
            except ValueError:
                pass
        taxes.append({
            "type": f"Tax {i}",
            "amount": tax_amount,
            "percentage": tax_percentage
        })
        i += 1

    for person_idx_one_based in range(1, people_count + 1):
        for item_idx in range(len(all_items_data)):
            checkbox_name = f'person_{person_idx_one_based}_item_{item_idx}'
            if request.form.get(checkbox_name) == 'on': 
                item = all_items_data.get(item_idx)
                if item:
                    people[person_idx_one_based - 1]['items'].append({
                        'name': item['name'],
                        'price': item['price']
                    })
                    people[person_idx_one_based - 1]['total'] += item['price']
    

    items_total_assigned = sum(p['total'] for p in people)
    remaining_total = total - items_total_assigned
    
    if people_count > 0:
        share_of_remaining = remaining_total / people_count
        for person in people:
            person['total'] += share_of_remaining
            person['formatted_total'] = "{:.2f}".format(person['total'])
    else:
        for person in people:
            person['formatted_total'] = "{:.2f}".format(person['total'])

    grand_total_calculated = sum(person['total'] for person in people)

    # Save to MongoDB
    try:
        db = db_instance.get_db()
        
        # Save bill history
        bill_data = {
            'user_id': user_id,
            'restaurant_name': request.form.get('restaurant_name', 'Unknown Restaurant'),
            'total_amount': total,
            'split_among': people_count,
            'bill_date': datetime.utcnow(),
            'image_path': request.form.get('image_url', '')
        }
        
        bill_result = db.bill_history.insert_one(bill_data)
        bill_id = bill_result.inserted_id
        
        # Save split details for ALL people (including yourself)
        for person in people:
            split_data = {
                'bill_id': bill_id,
                'payer_id': user_id,
                'payee_name': person['name'],
                'amount': person['total'],
                'items': [item['name'] for item in person['items']],
                'notified': False
            }
            db.split_details.insert_one(split_data)
            
            # Create notification only for other people (not yourself)
            if person['name'] != session['username']:
                notification_data = {
                    'user_id': user_id,
                    'message': f"{session['username']} split a bill with you. Your share: ₹{person['formatted_total']}",
                    'bill_id': bill_id,
                    'is_read': False,
                    'created_at': datetime.utcnow()
                }
                db.notifications.insert_one(notification_data)
        
        flash('Bill split saved successfully!', 'success')
        
    except Exception as e:
        print(f"Error saving to database: {e}")
        flash('Error saving bill history', 'error')

    return render_template(
        'results.html',
        people=people,
        grand_total="{:.2f}".format(grand_total_calculated),
        original_total="{:.2f}".format(hidden_total),
        edited_total="{:.2f}".format(total),
        original_taxes=hidden_taxes,
        edited_taxes=taxes
    )

@app.route('/history')
@login_required
def history():
    try:
        db = db_instance.get_db()
        user_id = session['user_id']
        
        # Get all bills for the user
        bills = list(db.bill_history.find({'user_id': user_id}).sort('bill_date', -1))
        
        # Get split details for each bill
        for bill in bills:
            bill['_id'] = str(bill['_id'])
            bill['bill_date'] = bill['bill_date'].strftime('%Y-%m-%d %H:%M')
            
            # Get split details for this bill
            split_details = list(db.split_details.find({'bill_id': ObjectId(bill['_id'])}))
            for detail in split_details:
                detail['_id'] = str(detail['_id'])
                if 'items' in detail and isinstance(detail['items'], list):
                    detail['items'] = [str(item) for item in detail['items']]
                else:
                    detail['items'] = []
            bill['split_details'] = split_details
        
        return render_template('history.html', bills=bills)
    except Exception as e:
        print(f"Error fetching history: {e}")
        flash('Error loading history', 'error')
        return render_template('history.html', bills=[])

@app.route('/notifications')
@login_required
def notifications():
    try:
        db = db_instance.get_db()
        user_id = session['user_id']
        
        notifications_list = list(db.notifications.find({'user_id': user_id}).sort('created_at', -1))
        
        for notification in notifications_list:
            notification['_id'] = str(notification['_id'])
            notification['created_at'] = notification['created_at'].strftime('%Y-%m-%d %H:%M')
        
        return render_template('notifications.html', notifications=notifications_list)
    except Exception as e:
        print(f"Error fetching notifications: {e}")
        flash('Error loading notifications', 'error')
        return render_template('notifications.html', notifications=[])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)