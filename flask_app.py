from flask import Flask, render_template, request, redirect, url_for
import os
from werkzeug.utils import secure_filename
from aws_script import extract_text_from_bill
import json # <--- THIS LINE IS CRITICAL FOR JSON OPERATIONS

# It seems your flask app file is named flask_app.py, adjust this if it's app.py
app = Flask(__name__) # Use __name__ for Flask app creation

UPLOAD_FOLDER = 'static/uploads'
# Removed PDF for now, as it needs special handling (image conversion)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'} 

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    # Make sure index.html links to a file input named 'bill'
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
            
            # Ensure extracted_data is a dict as expected from aws_script.py
            if not isinstance(extracted_data, dict):
                print(f"Warning: extract_text_from_bill did not return a dict. Type: {type(extracted_data)}")
                # Fallback to a structured, but empty/default dictionary
                extracted_data = {
                    'restaurant_name': 'Extraction Failed',
                    'items': [],
                    'taxes': [],
                    'subtotal': None,
                    'total': None
                }
            
            # Print extracted data for debugging
            print("--- Extracted Data for split.html ---")
            print(json.dumps(extracted_data, indent=4))
            print("-------------------------------------")

            # Pass all extracted data to the template
            return render_template('split.html',
                                   restaurant=extracted_data.get('restaurant_name', 'Restaurant'),
                                   items=extracted_data.get('items', []),
                                   taxes=extracted_data.get('taxes', []),
                                   subtotal=extracted_data.get('subtotal'),
                                   total=extracted_data.get('total'),
                                   image_url=f'uploads/{filename}') # Passed for display on split.html
            
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            print(f"Error processing file in Flask: {str(e)}") # Log the error for debugging
            return f"Error processing file: {str(e)}", 500
    
    return "Invalid file type. Allowed: PNG, JPG, JPEG, WEBP", 400

# ... (rest of the imports and app setup) ...

# ... (rest of app.py code) ...

@app.route('/calculate', methods=['POST'])
def calculate_shares():
    # Keep the `try` and `except Exception as e:` block commented out for now,
    # so we keep getting full tracebacks if other errors pop up.
    
    # Get count of people from the form
    people_count = int(request.form.get('peopleCount', 2))
    
    people = []
    for i in range(1, people_count + 1):
        name = request.form.get(f'person_{i}_name', f'Person {i}')
        people.append({
            'name': name,
            'items': [], # Correctly initialized as an empty list
            'total': 0.0
        })
    
    # --- Retrieve all original item data passed from hidden inputs in split.html ---
    all_items_data = {}
    item_index = 0
    while True:
        item_name_key = f'item_{item_index}_name'
        item_price_key = f'item_{item_index}_price'
        
        item_name = request.form.get(item_name_key)
        item_price_str = request.form.get(item_price_key)

        if item_name is None: # No more items with this index
            break
        
        try:
            item_price = float(item_price_str)
        except (ValueError, TypeError):
            item_price = 0.0 
        
        all_items_data[item_index] = {'name': item_name, 'price': item_price}
        item_index += 1

    # --- Retrieve taxes and totals from hidden inputs ---
    subtotal = float(request.form.get('hidden_subtotal', 0.0))
    total = float(request.form.get('hidden_total', 0.0))
    
    taxes_json = request.form.get('hidden_taxes', '[]')
    try:
        taxes = json.loads(taxes_json)
    except json.JSONDecodeError:
        taxes = [] # Fallback if JSON is malformed

    # --- Assign items to people based on checked checkboxes ---
    for person_idx_one_based in range(1, people_count + 1):
        for item_idx in range(len(all_items_data)): # Iterate through all potential items
            checkbox_name = f'person_{person_idx_one_based}_item_{item_idx}'
            
            if request.form.get(checkbox_name) == 'on': 
                item = all_items_data.get(item_idx)
                if item: 
                    people[person_idx_one_based - 1]['items'].append({
                        'name': item['name'],
                        'price': item['price']
                    })
                    people[person_idx_one_based - 1]['total'] += item['price']
    
    # --- Calculate individual shares including taxes and remaining total ---
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

    # --- ADD THIS DEBUGGING LOOP AND CHECK RIGHT BEFORE RENDER_TEMPLATE ---
    print("\n--- Debugging 'people' data before rendering results.html ---")
    for idx, person_data in enumerate(people):
        print(f"Person {idx+1} Name: {person_data['name']}")
        print(f"  Type of person_data['items']: {type(person_data['items'])}")
        print(f"  Content of person_data['items']: {person_data['items']}")
        # This will convert it to a list if it somehow wasn't (shouldn't happen with current logic)
        if not isinstance(person_data['items'], list):
            print(f"  WARNING: person_data['items'] for '{person_data['name']}' was NOT a list! Forcing to empty list.")
            person_data['items'] = [] # Safely convert to an empty list to prevent template error
    print("--- End Debugging 'people' data ---")
    # --- END ADDITION ---
    
    return render_template('results.html',
                           people=people,
                           grand_total="{:.2f}".format(grand_total_calculated),
                           original_total="{:.2f}".format(total))
    
    # Original `except Exception as e:` block is still commented out.
if __name__ == '__main__':
    # Use 'flask_app' if your file is named flask_app.py, otherwise it's '__main__' or your file name without .py
    app.run(host='0.0.0.0', port=5000, debug=True)