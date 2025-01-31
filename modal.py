# # from app import db

# # class Product(db.Model):
# #     id = db.Column(db.Integer, primary_key=True)  
# #     name = db.Column(db.String(100), nullable=False)
# #     price = db.Column(db.Float, nullable=False)  
# #     description = db.Column(db.Text, nullable=True) 
# #     rating = db.Column(db.Float, nullable=True) 
# #     in_stock = db.Column(db.Boolean, default=True)

# #     def __repr__(self)->str:
# #         return f"{self.name}-{self.price}{self.in_stock}"
# from app import db
# from datetime import datetime

# class Product(db.Model):
#     id = db.Column(db.Integer, primary_key=True)  
#     name = db.Column(db.String(100), nullable=False)
#     price = db.Column(db.Float, nullable=False)  
#     description = db.Column(db.Text, nullable=True) 
#     rating = db.Column(db.Float, nullable=True) 
#     image_url = db.Column(db.String(200), nullable=True)
#     in_stock = db.Column(db.Boolean, default=True)

#     def __repr__(self)->str:
#         return f"{self.name}-{self.price}{self.in_stock}"

# class PestPrediction(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     image_path = db.Column(db.String(255), nullable=False)
#     pest_type = db.Column(db.String(100), nullable=False)
#     confidence_score = db.Column(db.Float, nullable=False)
#     timestamp = db.Column(db.DateTime, default=datetime.utcnow)
#     location = db.Column(db.String(100), nullable=True)
#     farmer_id = db.Column(db.Integer, nullable=True)

#     def __repr__(self):
#         return f"Prediction({self.pest_type} - {self.confidence_score}%)"