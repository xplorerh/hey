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

#for pest detection
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

        relative_filepath = os.path.join('uploads', filename)
        
        new_prediction = PestPrediction(
            image_path=filepath,
            pest_type=prediction['pest_type'],
            confidence_score=prediction['confidence']
        )
        db.session.add(new_prediction)
        db.session.commit()

        return render_template('pest.html', prediction=prediction, image_path=relative_filepath)

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
    return render_template("frontpage.html",title="student_zone")

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
        password = request.form['password']
        user_type = request.form['user_type']

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

        # Save user to database
        new_user = User(username=username, email=email, password=password, user_type=user_type, profile_pic=filename)
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
@app.route('/marketplace')
def marketplace():
    products = Product.query.all()
    return render_template("marketplace.html",title="marketplace",products=products)

@app.route('/pest')
def pest():
    return render_template("pest.html", title="pest")

if __name__ == '__main__':
    app.run(debug=True)