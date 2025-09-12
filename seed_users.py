from app import app, db, UserEmail

with app.app_context():
    dummy_users = [
        UserEmail(full_name="Alice Sharma", email="alice.sim@example.com"),
        UserEmail(full_name="Bob Mehta", email="bob.fake@example.com"),
        UserEmail(full_name="Carol Rao", email="carol.test@example.com"),
        UserEmail(full_name="David Kapoor", email="david.phish@example.com"),
    ]
    db.session.bulk_save_objects(dummy_users)
    db.session.commit()
    print("✅ Dummy users added.")
