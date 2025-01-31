from app import app, db, Product  # Import the app, db, and Product model

# Create an application context
with app.app_context():
    # Create a new product instance
    new_product = Product(
        name="Fresh Baigan", 
        price=10, 
        description="Crisp, juicy, and sweet apples freshly picked from organic farms.", 
        rating=3,
        in_stock=True,
        image_url="https://media.naheed.pk/catalog/product/cache/ed9f5ebe2a117625f6cd6336daddd764/1/1/1168946-1.jpg"
    )

    # Add the product to the session
    db.session.add(new_product)

    # Commit the session to the database
    db.session.commit()

    print("Product added successfully!")
