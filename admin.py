from app import app, db, AdminLogin

with app.app_context():
    print("🌐 Seeding Admin User...")  

    existing = AdminLogin.query.filter_by(username="admin1").first()
    
    if existing:
        print("⚠️ Admin user 'admin1' already exists.")
    else:
        admin = AdminLogin(username="admin1")
        admin.password = "1234"
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin user 'admin1' created successfully!")
