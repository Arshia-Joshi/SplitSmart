from flask import Flask, render_template, request, redirect, url_for
import os
from werkzeug.utils import secure_filename
from aws_script import extract_text_from_bill
import json

app = Flask(__name__)

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
def calculate_shares():
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

    # Total
    total_str = request.form.get('total')
    try:
        total = float(total_str) if total_str else hidden_total
    except ValueError:
        total = hidden_total

    # Taxes
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

    print("\n--- Debugging 'people' data before rendering results.html ---")
    for idx, person_data in enumerate(people):
        print(f"Person {idx+1} Name: {person_data['name']}")
        print(f"  Items: {person_data['items']}")
        print(f"  Total: {person_data['total']}")
    print("--- End Debugging 'people' data ---")

    return render_template(
        'results.html',
        people=people,
        grand_total="{:.2f}".format(grand_total_calculated),
        original_total="{:.2f}".format(hidden_total),
        edited_total="{:.2f}".format(total),
        original_taxes=hidden_taxes,
        edited_taxes=taxes
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
