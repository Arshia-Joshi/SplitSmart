from flask import Flask, render_template, request, redirect, url_for,jsonify, session
import os
from werkzeug.utils import secure_filename
from aws_script import extract_text_from_bill
import json

# It seems your flask app file is named flask_app.py, adjust this if it's app.py
app = Flask(__name__)

# To use sessions, a secret key is required
app.secret_key = 'your_super_secret_key' # CHANGE THIS IN PRODUCTION

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

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
            
            if not isinstance(extracted_data, dict):
                print(f"Warning: extract_text_from_bill did not return a dict. Type: {type(extracted_data)}")
                extracted_data = {
                    'restaurant_name': 'Extraction Failed',
                    'items': [],
                    'taxes': [],
                    'subtotal': None,
                    'total': None
                }
            
            #print("--- Extracted Data for split.html ---")
           # print(json.dumps(extracted_data, indent=4))
           # print("-------------------------------------")

            return render_template('split.html',
                                   restaurant=extracted_data.get('restaurant_name', 'Restaurant'),
                                   items=extracted_data.get('items', []),
                                   taxes=extracted_data.get('taxes', []),
                                   subtotal=extracted_data.get('subtotal'),
                                   total=extracted_data.get('total'),
                                   image_url=f'uploads/{filename}')
            
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            print(f"Error processing file in Flask: {str(e)}")
            return f"Error processing file: {str(e)}", 500
    
    return "Invalid file type. Allowed: PNG, JPG, JPEG, WEBP", 400

# The /submit route is no longer needed since we're using /calculate directly.
# I've removed it for cleaner code.

@app.route('/calculate', methods=['POST'])
def calculate_shares():
    try:
        data = request.get_json()
        print(data)
        people_count = data.get('peopleCount', 0)
        people_data = data.get('people', [])
        bill_items = data.get('items', [])
        person_items_allocation = data.get('personItems', {})

        people = []
        for person_info in people_data:
            person_id = str(person_info.get('person_id'))
            person_total = 0.0
            person_items = []
            
            if person_id in person_items_allocation:
                allocated_item_names = person_items_allocation[person_id]
                for item_name in allocated_item_names:
                    item_found = next((item for item in bill_items if item.get('name') == item_name), None)
                    if item_found:
                        person_items.append(item_found)
                        person_total += item_found.get('price', 0.0)
            
            people.append({
                'name': person_info.get('name', f'Person {person_id}'),
                'items': person_items,
                'total': person_total
            })

        edited_total = sum(item.get('price', 0.0) for item in bill_items)
        items_total_assigned = sum(p['total'] for p in people)
        remaining_total = edited_total - items_total_assigned
        
        if people_count > 0:
            share_of_remaining = remaining_total / people_count
            for person in people:
                person['total'] += share_of_remaining
                person['formatted_total'] = "{:.2f}".format(person['total'])
        else:
            for person in people:
                person['formatted_total'] = "{:.2f}".format(person['total'])

        grand_total_calculated = sum(person['total'] for person in people)
        #print(f"people_count: {people_count}\n people_data:{people_data}\n bill_items:  {bill_items}\n person_items_allocation: {person_items_allocation} grand_total_calculated: {grand_total_calculated} ")
        # Store the calculated data in the session
        session['results'] = {
            'people': people,
            'grand_total': "{:.2f}".format(grand_total_calculated),
            'original_total': "{:.2f}".format(edited_total)
        }
       # return render_template('results.html',results=session['results'])
        return redirect(url_for('show_results'))
        # Return a success JSON response to the JavaScript
       # return jsonify({'status': 'success', 'message': 'Calculations complete.'})

    except Exception as e:
        print(f"Error in /calculate route: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/results')
def show_results():
    # Retrieve the results from the session
    results = session.get('results', None)
    
    if results is None:
        return redirect(url_for('home')) # Redirect if no data is found

    return render_template('results.html', **results) # Pass data to the template

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)