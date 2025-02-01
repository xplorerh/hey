from flask import Flask,render_template,redirect, flash, jsonify, request, url_for, send_from_directory, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_required, current_user
import os
from pest_prediction import PestDetector
from flask_migrate import Migrate
from functools import wraps
from datetime import datetime
import pickle
import pandas as pd
from haversine import haversine, Unit
import csv

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_very_secret_and_random_key_here'
db = SQLAlchemy(app)

migrate = Migrate(app, db)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)  
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)  
    description = db.Column(db.Text, nullable=True) 
    rating = db.Column(db.Float, nullable=True) 
    image_url = db.Column(db.String(200), nullable=True)
    in_stock = db.Column(db.Boolean, default=True)

    def __repr__(self)->str:
        return f"{self.name}-{self.price}{self.in_stock}"

class PestPrediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_path = db.Column(db.String(255), nullable=False)
    pest_type = db.Column(db.String(100), nullable=False)
    confidence_score = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    location = db.Column(db.String(100), nullable=True)
    farmer_id = db.Column(db.Integer, nullable=True)

    def __repr__(self):
        return f"Prediction({self.pest_type} - {self.confidence_score}%)"

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)
    farm_name = db.Column(db.String(100), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    contact_number = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    profile_pic = db.Column(db.String(255), default='default.jpg')  # Store image filename

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class FarmInventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    crop_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    harvest_date = db.Column(db.DateTime, nullable=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg','csv'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_pest_remedy(pest_type):
    """
    Lookup remedy for a specific pest type from the CSV file
    """
    remedy_file_path = 'pest_remedy.csv'
    
    try:
        with open(remedy_file_path, 'r') as csvfile:
            csv_reader = csv.DictReader(csvfile)
            for row in csv_reader:
                if row['pestname'].lower() == pest_type.lower():
                    return row['remedy']
    except Exception as e:
        print(f"Error reading remedy CSV: {e}")
    
    return "No specific remedy found for this pest."

@app.route('/crop_pest_selection')
def crop_pest_selection():
    crops = [
        {
            'name': 'Jute',
            'image': 'static/images/jute-crop.jpg',
            'description': 'Pest Detection for Jute Crops',
            'active': True
        },
        {
            'name': 'Rice',
            'image': 'static/images/rice-crop.jpg',
            'description': 'Coming Soon',
            'active': False
        },
        {
            'name': 'Wheat',
            'image': 'static/images/wheat-crop.jpg',
            'description': 'Coming Soon',
            'active': False
        },
        {
            'name': 'Maize',
            'image': 'static/images/maize-crop.jpg',
            'description': 'Coming Soon',
            'active': False
        }
    ]
    return render_template("crop_pest_selection.html", crops=crops)

def login_required(user_types=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please login first')
                return redirect(url_for('login'))
            
            if user_types and session.get('user_type') not in user_types:
                flash('Unauthorized access')
                return redirect(url_for('Home'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'pestImage' not in request.files:
        flash('No file part')
        return redirect(url_for('pest'))
    
    file = request.files['pestImage']
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('pest'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        detector = PestDetector()
        prediction = detector.predict(filepath)

        remedy = get_pest_remedy(prediction['pest_type'])

        relative_filepath = os.path.join('uploads', filename)
        
        new_prediction = PestPrediction(
            image_path=filepath,
            pest_type=prediction['pest_type'],
            confidence_score=prediction['confidence']
        )
        db.session.add(new_prediction)
        db.session.commit()

        return render_template('pest.html', prediction=prediction, image_path=relative_filepath, remedy=remedy)

    return redirect(url_for('pest'))

@app.route('/static/uploads/<filename>')
def serve_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/update_settings', methods=['GET', 'POST'])
def update_settings():
    if request.method == 'POST':
        # Handle the form submission, for example:
        farm_name = request.form['farm_name']
        location = request.form['location']
        contact_number = request.form['contact_number']

        # Update user settings in your database here (not shown)
        
        # Redirect to the user profile after successful update
        return redirect(url_for('profile'))  # Replace 'profile' with the name of the profile route
    return render_template('update_settings.html')
has_run_before = False

@app.before_request
def before_request():
    global has_run_before
    if not has_run_before:
        db.create_all()  
        has_run_before = True 

@app.route('/')
def Home():
    return render_template("home.html",title="Home")

@app.route('/features')
def features():
    return render_template("features.html",title="features")

@app.route('/research_data')
def research_data():
    return render_template("frontpage.html",title="research_data")

@app.route('/student_zone')
def student_zone():
    return render_template("student.html",title="student_zone")

@app.route('/contact')
def contact():
    return render_template("contact.html",title="contact")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_type = request.form['user_type']
        
        user = User.query.filter_by(username=username, user_type=user_type).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_type'] = user.user_type
            
            if user_type == 'farmer':
                return redirect(url_for('farmer_dashboard'))
            elif user_type == 'customer':
                return redirect(url_for('customer_dashboard'))
            elif user_type == 'admin':
                return redirect(url_for('admin_dashboard'))
        
        flash('Invalid username or password')
    
    return render_template('login.html', title='Login')
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']  # This is the raw password from the form
        user_type = request.form['user_type']
        farm_name = request.form.get('farm_name', None)
        location = request.form.get('location', None)

        # Handle file upload
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
            else:
                filename = 'default.jpg'  # Default profile picture
        else:
            filename = 'default.jpg'

        # Create user instance WITHOUT the password field
        new_user = User(
            username=username,
            email=email,
            user_type=user_type,
            farm_name=farm_name,
            location=location,
            profile_pic=filename
        )

        # Hash and store the password
        new_user.set_password(password)  # Securely hash password before storing

        # Save user to database
        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully!", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# User loader function (modify as per your database)
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))  # Fetch user from database

@app.route('/profile')
@login_required  # Ensures only logged-in users can access profile
def profile():
    return render_template('profile.html', user=current_user)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('Home'))

@app.route('/forgot_password')
def forgot_password():
    return render_template("forgot_password.html",title="reset")

@app.route('/farmer/dashboard')
@login_required(user_types=['farmer'])
def farmer_dashboard():
    user = User.query.get(session['user_id'])
    inventories = FarmInventory.query.filter_by(farmer_id=user.id).all()
    return render_template('farmer_dashboard.html', user=user, inventories=inventories)

@app.route('/customer/dashboard')
@login_required(user_types=['customer'])
def customer_dashboard():
    user = User.query.get(session['user_id'])
    orders = Order.query.filter_by(customer_id=user.id).all()
    return render_template('customer_dashboard.html', user=user, orders=orders)

@app.route('/admin/dashboard')
@login_required(user_types=['admin'])
def admin_dashboard():
    users = User.query.all()
    farmers = User.query.filter_by(user_type='farmer').all()
    products = Product.query.all()
    pest_reports = PestPrediction.query.order_by(PestPrediction.timestamp.desc()).limit(10).all()
    
    return render_template(
        'admin_dashboard.html', 
        users=users, 
        farmers=farmers, 
        products=products,
        pest_reports=pest_reports
    )
@app.route('/marketplace', methods=['GET', 'POST'])
def marketplace():
    # Get the sort option from the request (default is None or 'featured')
    sort_option = request.args.get('sort', 'featured')

    # Determine the query to use for sorting
    if sort_option == 'Price: Low to High':
        products = Product.query.order_by(Product.price).all()
    elif sort_option == 'Price: High to Low':
        products = Product.query.order_by(Product.price.desc()).all()
    elif sort_option == 'Rating: Highest':
        products = Product.query.order_by(Product.rating.desc()).all()
    elif sort_option == 'Latest':
        products = Product.query.order_by(Product.id.desc()).all()
    else:
        # Default sorting: featured (or you can use some other default logic)
        products = Product.query.all()

    return render_template("marketplace.html", title="Marketplace", products=products)


@app.route('/pest')
def pest():
    return render_template("pest.html", title="pest")

@app.route('/warehouses', methods=['GET', 'POST'])
def warehouses():
    # Load prediction resources
    with open('warehouse_model.pkl', 'rb') as f:
        model_data = pickle.load(f)
        model = model_data['model']
        scaler = model_data['scaler']
        warehouses = model_data['warehouses']
    
    fixed_warehouse = pd.read_csv('fixed_warehouse.csv')
    show_prediction = False
    result_warehouses = []

    if request.method == 'POST':
        if 'inventory_file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['inventory_file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Process prediction
            new_data = pd.read_csv(filepath)
            merged_data = pd.merge(
                new_data,
                fixed_warehouse[['District', 'Latitude', 'Longitude']],
                on='District',
                how='left'
            )
            clean_data = merged_data.dropna(subset=['Latitude', 'Longitude']).copy()

            def calculate_distances(row):
                return [
                    haversine((row['Latitude'], row['Longitude']), 
                              (wh['Latitude'], wh['Longitude']), unit=Unit.KILOMETERS)
                    for _, wh in warehouses.iterrows()
                ]

            new_distances = clean_data.apply(calculate_distances, axis=1)
            distance_df = pd.DataFrame(
                new_distances.tolist(),
                columns=warehouses['District']
            )
            scaled_data = scaler.transform(distance_df)
            clean_data['Optimal Warehouse'] = [
                warehouses.iloc[cluster]['District'] 
                for cluster in model.predict(scaled_data)
            ]

            warehouse_counts = clean_data['Optimal Warehouse'].value_counts()
            threshold = warehouse_counts.quantile(0.75)
            significant_warehouses = warehouse_counts[warehouse_counts >= threshold].index.tolist()

            result_warehouses = []
            for warehouse_name in significant_warehouses:
                warehouse_info = fixed_warehouse[fixed_warehouse['District'] == warehouse_name].iloc[0]
                result_warehouses.append({
                    'district': warehouse_name,
                    'latitude': warehouse_info['Latitude'],
                    'longitude': warehouse_info['Longitude'],
                })

            show_prediction = True
            flash('Warehouse prediction completed successfully!', 'success')

    return render_template(
        'warehouses.html', 
        title="Warehouses", 
        warehouses=result_warehouses, 
        show_prediction=show_prediction,
        map_key='AIzaSyBUembZbrAbmni90Rqwbd3drj5xBkRsF50'  # Replace with your actual Google Maps API key
    )

# Complete list of 77 districts in Nepal
NEPAL_DISTRICTS = [
    # Provinces
    # Province 1
    "Bhojpur", "Dhankuta", "Ilam", "Jhapa", "Khotang", "Morang", "Okhaldunga", 
    "Panchthar", "Sankhuwasabha", "Solukhumbu", "Sunsari", "Taplejung", "Tehrathum", "Udayapur",
    
    # Province 2
    "Bara", "Dhanusa", "Mahottari", "Parsa", "Rautahat", "Sarlahi", "Saptari", "Siraha",
    
    # Province 3 (Bagmati)
    "Bhaktapur", "Dhading", "Kathmandu", "Kavrepalanchok", "Lalitpur", "Nuwakot", 
    "Rasuwa", "Sindhuli", "Sindhupalchok",
    
    # Province 4 (Gandaki)
    "Gorkha", "Kaski", "Lamjung", "Manang", "Mustang", "Myagdi", "Nawalpur", "Parbat", "Syangja", "Tanahun",
    
    # Province 5
    "Arghakhanchi", "Banke", "Bardiya", "Dang", "Gulmi", "Kapilvastu", "Parasi", 
    "Palpa", "Pyuthan", "Rolpa", "Rukum", "Rupandehi",
    
    # Province 6 (Karnali)
    "Dailekh", "Dolpa", "Humla", "Jajarkot", "Jumla", "Kalikot", "Mugu", "Rukum East", "Salyan", "Surkhet",
    
    # Province 7
    "Achham", "Baitadi", "Bajhang", "Bajura", "Dadeldhura", "Darchula", "Doti", 
    "Kailali", "Kanchanpur"
]


@app.route('/logistics', methods=['GET', 'POST'])
def item_tracking():
    # Comprehensive district coordinates (more accurate representation)
    DISTRICT_COORDINATES = {
        # Province 1
        "Bhojpur": (26.9302, 87.0372), "Dhankuta": (26.9862, 87.0919), 
        "Ilam": (26.9092, 88.0841), "Jhapa": (26.7271, 88.0845), 
        "Khotang": (27.1838, 86.7819), "Morang": (26.5333, 87.2667), 
        "Okhaldunga": (27.3175, 86.5314), "Panchthar": (27.0769, 87.9183), 
        "Sankhuwasabha": (27.2667, 87.2333), "Solukhumbu": (27.7900, 86.5400), 
        "Sunsari": (26.6276, 87.1822), "Taplejung": (27.3552, 87.6689), 
        "Tehrathum": (27.1831, 87.4269), "Udayapur": (26.8406, 86.8406),
        
        # Province 2
        "Bara": (26.7272, 85.9300), "Dhanusa": (26.8350, 86.0122), 
        "Mahottari": (26.7333, 86.0667), "Parsa": (27.0667, 84.8833), 
        "Rautahat": (26.6667, 86.1667), "Sarlahi": (26.7333, 85.8333), 
        "Saptari": (26.5667, 86.7333), "Siraha": (26.6667, 86.2167),
        
        # Province 3 (Bagmati)
        "Bhaktapur": (27.6712, 85.4298), "Dhading": (28.0833, 84.8833), 
        "Kathmandu": (27.7103, 85.3222), "Kavrepalanchok": (27.5333, 85.5333), 
        "Lalitpur": (27.6589, 85.3378), "Nuwakot": (28.1667, 85.2667), 
        "Rasuwa": (28.1667, 85.4167), "Sindhuli": (27.3333, 86.0333), 
        "Sindhupalchok": (27.8333, 85.7500),
        
        # Province 4 (Gandaki)
        "Gorkha": (27.9842, 84.6270), "Kaski": (28.2622, 84.0167), 
        "Lamjung": (28.2333, 84.3667), "Manang": (28.6667, 84.0333), 
        "Mustang": (28.8333, 83.7667), "Myagdi": (28.3667, 83.7667), 
        "Nawalpur": (27.7000, 84.4333), "Parbat": (28.2333, 83.9667), 
        "Syangja": (28.1167, 83.9000), "Tanahun": (28.0333, 84.3333),
        
        # Province 5
        "Arghakhanchi": (27.7500, 83.3833), "Banke": (28.1500, 81.7500), 
        "Bardiya": (28.2000, 81.4333), "Dang": (28.0833, 82.3000), 
        "Gulmi": (28.0833, 83.3000), "Kapilvastu": (27.5667, 83.0000), 
        "Parasi": (27.5333, 83.3789), "Palpa": (28.1500, 83.5167), 
        "Pyuthan": (28.1000, 82.8667), "Rolpa": (28.3816, 82.6483), 
        "Rukum": (28.3500, 82.2000), "Rupandehi": (27.5330, 83.3789),
        
        # Province 6 (Karnali)
        "Dailekh": (28.8500, 81.7000), "Dolpa": (29.0333, 82.8333), 
        "Humla": (29.9667, 81.8167), "Jajarkot": (28.6167, 81.6833), 
        "Jumla": (29.2889, 82.3018), "Kalikot": (28.8667, 81.6167), 
        "Mugu": (29.2500, 81.9833), "Rukum East": (28.3816, 82.6483), 
        "Salyan": (28.3500, 81.9667), "Surkhet": (28.6167, 81.6500),
        
        # Province 7
        "Achham": (29.0396, 81.2519), "Baitadi": (29.3333, 80.5833), 
        "Bajhang": (29.5167, 81.3000), "Bajura": (29.4833, 81.5167), 
        "Dadeldhura": (29.2188, 80.4994), "Darchula": (29.8667, 80.5667), 
        "Doti": (29.0000, 81.4000), "Kailali": (28.7000, 80.9667), 
        "Kanchanpur": (28.9333, 80.5667)
    }

    # Convert dictionary to list of district names
    districts = sorted(list(DISTRICT_COORDINATES.keys()))

    if request.method == 'POST':
        try:
            # Extract form data
            delivery_district = request.form.get('delivery_district')
            product_quantity = float(request.form.get('product_quantity', 0))
            product_weight = float(request.form.get('product_weight', 0))

            # Find nearest warehouse using comprehensive district coordinates
            def find_nearest_warehouse(target_district):
                target_lat, target_lng = DISTRICT_COORDINATES.get(
                    target_district, 
                    (27.7103, 85.3222)  # Default to Kathmandu if not found
                )

                # Calculate distances to all districts
                distances = {
                    district: haversine(
                        (target_lat, target_lng), 
                        DISTRICT_COORDINATES.get(district, (27.7103, 85.3222)), 
                        unit=Unit.KILOMETERS
                    )
                    for district in DISTRICT_COORDINATES.keys() 
                    if district != target_district
                }

                # Find nearest district
                nearest_district = min(distances, key=distances.get)
                nearest_lat, nearest_lng = DISTRICT_COORDINATES[nearest_district]

                return {
                    'District': nearest_district,
                    'Latitude': nearest_lat,
                    'Longitude': nearest_lng
                }, {
                    'District': target_district,
                    'Latitude': target_lat,
                    'Longitude': target_lng
                }

            # Get warehouse details
            nearest_warehouse, delivery_location = find_nearest_warehouse(delivery_district)

            # Comprehensive logistics calculations
            estimated_distance = haversine(
                (nearest_warehouse['Latitude'], nearest_warehouse['Longitude']), 
                (delivery_location['Latitude'], delivery_location['Longitude']), 
                unit=Unit.KILOMETERS
            )
            
            # Detailed cost calculations
            base_delivery_rate = 50  # NPR per km base rate
            weight_rate = 10  # Additional NPR per kg
            quantity_rate = 5  # Additional NPR per unit

            distance_cost = estimated_distance * base_delivery_rate
            weight_cost = product_weight * weight_rate
            quantity_cost = product_quantity * quantity_rate

            total_delivery_cost = distance_cost + weight_cost + quantity_cost

            # Estimated delivery time
            avg_speed = 40  # km/h considering Nepalese terrain
            estimated_time = estimated_distance / avg_speed

            # Prepare route visualization data
            route_details = {
                'origin': {
                    'lat': nearest_warehouse['Latitude'], 
                    'lng': nearest_warehouse['Longitude'],
                    'district': nearest_warehouse['District']
                },
                'destination': {
                    'lat': delivery_location['Latitude'], 
                    'lng': delivery_location['Longitude'],
                    'district': delivery_district
                }
            }

            return render_template('logistics.html', 
                districts=districts,
                map_key='AIzaSyBUembZbrAbmni90Rqwbd3drj5xBkRsF50',  # Your Google Maps API key
                result={
                    'nearest_warehouse': nearest_warehouse['District'],
                    'delivery_district': delivery_district,
                    'estimated_distance': round(estimated_distance, 2),
                    'estimated_time': round(estimated_time, 2),
                    'route_details': route_details,
                    'cost_breakdown': {
                        'distance_cost': round(distance_cost, 2),
                        'weight_cost': round(weight_cost, 2),
                        'quantity_cost': round(quantity_cost, 2),
                        'total_cost': round(total_delivery_cost, 2)
                    }
                })

        except Exception as e:
            flash(f'Error processing logistics: {str(e)}', 'danger')
            return render_template('logistics.html', districts=districts)

    return render_template('logistics.html', districts=districts)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)