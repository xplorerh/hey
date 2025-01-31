from flask import Flask,render_template,redirect, flash, jsonify, request, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
from pest_prediction import PestDetector
from flask_migrate import Migrate



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATION']=False
db=SQLAlchemy(app)
# migrate = Migrate(app, db)

from datetime import datetime

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

#for pest detection
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



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

@app.route('/login',methods=['GET','POST'])
def login():
    return render_template("login.html",title="login")


@app.route('/register',methods=['GET','POST'])
def register():
    return render_template("register.html",title="register")

@app.route('/resetuser')
def forgot_password():
    return render_template("register.html",title="reset")


@app.route('/marketplace')
def marketplace():
    products = Product.query.all()
    return render_template("marketplace.html",title="marketplace",products=products)

@app.route('/pest')
def pest():
    return render_template("pest.html", title="pest")

if __name__ == '__main__':
    app.run(debug=True)
