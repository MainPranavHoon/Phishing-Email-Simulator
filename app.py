import io
from flask import Flask, render_template, request, redirect, session, url_for, flash , Response ,send_file
#session stores data for a specific user between requests
#Flash is used to display one-time messages like errors, success, or warnings.
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash,check_password_hash
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from models import db, UserEmail, Campaign, MailLog, ClickLog, AwarenessLog , EmailTemplate , AdminLogin , UserEmail
from flask_migrate import Migrate


app =Flask(__name__)
app.secret_key = 'f@keK3y_123456!#secure' 
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "mssql+pyodbc://PRANAV\\SQLEXPRESS/db"
    "?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config["MAIL_SERVER"]="sandbox.smtp.mailtrap.io"
app.config["MAIL_PORT"]=2525
app.config["MAIL_USERNAME"]="540e6fda4925e0"
app.config["MAIL_PASSWORD"]="c096715f3a9157"
app.config["MAIL_USE_TLS"]=True
app.config["MAIL_USE_SSL"]=False

mail=Mail(app)
db.init_app(app)
migrate = Migrate(app, db)
#login
@app.route("/login",methods=["POST","GET"])
def login():
    if request.method=="POST":
        username = request.form['username']#Gets the value from the text input.
        password = request.form['password']#Gets the value from the text input.

        admin=AdminLogin.query.filter_by(username=username).first()

        if not admin:
            flash("Invalid username or password")
        elif not admin.verify_password(password):
            flash("Invalid username or password")
        else:
            session['admin_id'] = admin.id 
            session['username'] = admin.username
            return redirect("/dashboard")
            

    return render_template("login.html")

#dashboard
@app.route("/dashboard")
def dashboard():
    if "admin_id" not in session:
        return redirect("/login")

    # Global metrics
    total_email = MailLog.query.count()
    total_clicks = ClickLog.query.count()
    total_awareness = AwarenessLog.query.count()
    
    # Calculate global awareness delivery rate
    global_awareness_rate = (total_awareness / total_clicks * 100) if total_clicks > 0 else 0

    # Get campaigns for this admin with enhanced metrics
    campaigns = Campaign.query.filter_by(admin_id=session["admin_id"]).all()

    for campaign in campaigns:
        # Basic metrics
        campaign.total_emails = MailLog.query.filter_by(campaign_id=campaign.campaign_id).count()
        
        # Get all clicks for this campaign
        campaign_clicks = db.session.query(ClickLog).join(MailLog).filter(
            MailLog.campaign_id == campaign.campaign_id
        ).all()
        campaign.total_clicks = len(campaign_clicks)
        
        # Get awareness logs for this campaign
        campaign_awareness = db.session.query(AwarenessLog).join(ClickLog).join(MailLog).filter(
            MailLog.campaign_id == campaign.campaign_id
        ).count()
        campaign.total_awareness = campaign_awareness
        
        # Calculate rates
        campaign.click_rate = (campaign.total_clicks / campaign.total_emails * 100) if campaign.total_emails else 0
        campaign.awareness_rate = (campaign.total_awareness / campaign.total_clicks * 100) if campaign.total_clicks else 0
        
        # Count unique users who opened emails (clicked tracking links)
        opened_count = db.session.query(MailLog).filter(
            MailLog.campaign_id == campaign.campaign_id,
            MailLog.opened_at.isnot(None)
        ).count()
        campaign.opened_count = opened_count
        campaign.open_rate = (opened_count / campaign.total_emails * 100) if campaign.total_emails else 0

    return render_template(
        "dashboard.html",
        total_email=total_email,
        total_clicks=total_clicks,
        total_awareness=total_awareness,
        global_awareness_rate=global_awareness_rate,
        campaigns=campaigns,
        username=session.get("username", "Admin")  # Added fallback for username
    )

#logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

#send emails
@app.route("/send")
def send():
    message=Message(
        subject="Hello",
        recipients=["test.mailtrap123@gmail.com"],
        sender="pranav@mailtrap.club"
    )
    message.body="Fake email"
    mail.send(message)

    return "Message sent"

#For creating campaigns
@app.route("/create_campaign", methods=["POST", "GET"])
def create_campaign():
    if "admin_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    if request.method == "POST":
        try:
            campaign_name = request.form.get('campaign_name', '').strip()
            recipient_ids = request.form.getlist('recipients[]')
            email_subject = request.form.get("email_subject", '').strip()
            email_body = request.form.get("email_body", '').strip()
            template_id = request.form.get("template_id")

            # Debug: Print received data
            print(f"Campaign Name: '{campaign_name}'")
            print(f"Recipient IDs raw: {recipient_ids}")
            print(f"Email Subject: '{email_subject}'")
            print(f"Template ID: {template_id}")

            # Validate required fields
            if not campaign_name:
                flash("Campaign name is required.", "error")
                raise ValueError("Missing campaign name")
            
            if not email_subject:
                flash("Email subject is required.", "error")
                raise ValueError("Missing email subject")
                
            if not email_body:
                flash("Email body is required.", "error")
                raise ValueError("Missing email body")

            # Validate and clean recipient IDs
            if not recipient_ids:
                flash("Please select at least one recipient.", "error")
                raise ValueError("No recipients selected")

            # Clean recipient IDs (remove empty strings and convert to int)
            clean_recipient_ids = []
            for uid in recipient_ids:
                uid_str = str(uid).strip()
                if uid_str and uid_str.isdigit():
                    clean_recipient_ids.append(int(uid_str))
            
            if not clean_recipient_ids:
                flash("No valid recipients selected.", "error")
                raise ValueError("No valid recipients")

            print(f"Clean Recipient IDs: {clean_recipient_ids}")

            # Verify all users exist before creating campaign
            existing_users = UserEmail.query.filter(UserEmail.user_id.in_(clean_recipient_ids)).all()
            existing_user_ids = [user.user_id for user in existing_users]
            
            if len(existing_user_ids) != len(clean_recipient_ids):
                missing_ids = set(clean_recipient_ids) - set(existing_user_ids)
                flash(f"Some selected users don't exist: {missing_ids}", "error")
                raise ValueError("Invalid user IDs")

            print(f"Verified users exist: {existing_user_ids}")

            # Create campaign
            campaign = Campaign(
                campaign_name=campaign_name,
                admin_id=session["admin_id"],
                email_subject=email_subject,
                email_body=email_body,
                template_id=int(template_id) if template_id and template_id.strip() else None
            )
            db.session.add(campaign)
            db.session.flush()  # Get campaign_id without full commit
            
            print(f"Created campaign with ID: {campaign.campaign_id}")

            # Add MailLog entries for each recipient
            mail_logs_created = 0
            for user_id in existing_user_ids:
                mail_log = MailLog(
                    campaign_id=campaign.campaign_id,
                    user_id=user_id,
                    sent_at=None  # Will be set when actually sent
                )
                db.session.add(mail_log)
                db.session.flush()  # ensure mail_log.mail_id exists

                # Generate tracking URL
                mail_log.tracking_url = url_for('track_click', mail_id=mail_log.mail_id, _external=True)
                mail_logs_created += 1
                print(f"Created mail_log for user_id {user_id}, mail_id: {mail_log.mail_id}")

            db.session.commit()
            
            print(f"Total mail logs created: {mail_logs_created}")
            flash(f"Campaign '{campaign_name}' created successfully with {mail_logs_created} recipients! ✅", "success")
            return redirect(url_for('dashboard'))  # Redirect to dashboard to see the new campaign

        except Exception as e:
            db.session.rollback()
            print(f"Error creating campaign: {str(e)}")
            flash(f"Error creating campaign: {str(e)}", "error")
            # Fall through to GET request handling

    # GET request or error fallback
    users = UserEmail.query.all()
    templates = EmailTemplate.query.all()
    
    # Debug: Print user data
    print(f"Available users count: {len(users)}")
    for user in users[:5]:  # Print first 5 users
        print(f"User ID: {user.user_id}, Email: {user.email}")
    
    return render_template("create_campaign.html", users=users, templates=templates)


#For viewing all campaigns created
@app.route("/campaign")
def view_campaign():
    campaigns = Campaign.query.all()
    return render_template("view_campaign.html",campaigns=campaigns)


#For deleting campaigns
@app.route('/delete_campaign/<int:campaign_id>', methods=['POST'])
def delete_campaign(campaign_id):
    try:
        campaign = Campaign.query.get_or_404(campaign_id)
        
        # Get all mail_log records for this campaign
        mail_logs = MailLog.query.filter_by(campaign_id=campaign_id).all()
        mail_log_ids = [log.mail_id for log in mail_logs]
        
        # Step 1: Delete awareness_logs that reference click_logs
        if mail_log_ids:
            # Delete awareness logs first (they reference click_logs)
            awareness_to_delete = db.session.query(AwarenessLog).join(ClickLog).filter(
                ClickLog.mail_id.in_(mail_log_ids)
            ).all()
            for awareness in awareness_to_delete:
                db.session.delete(awareness)
            
            # Step 2: Delete click_logs that reference mail_logs
            clicks_to_delete = ClickLog.query.filter(ClickLog.mail_id.in_(mail_log_ids)).all()
            for click in clicks_to_delete:
                db.session.delete(click)
        
        # Step 3: Delete mail_logs
        for mail_log in mail_logs:
            db.session.delete(mail_log)
        
        # Step 4: Finally delete the campaign
        db.session.delete(campaign)
        db.session.commit()
        
        flash(f"Campaign '{campaign.campaign_name}' deleted successfully.", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting campaign: {str(e)}", "error")
        
    return redirect(url_for('dashboard')) 

#For previewing a single campaign
@app.route("/preview_campaign/<int:campaign_id>")
def preview_campaign(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    recipients=[]
    for log in campaign.mail_logs:
        recipients.append(log.user) #creates a list of all users for that campaign
    return render_template("preview_campaign.html",campaign=campaign,recipients=recipients)    

#Send campaigns 
@app.route("/send_campaign/<int:campaign_id>", methods=["POST"])
def send_campaign(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    recipients = campaign.mail_logs  # MailLog entries for this campaign

    sent_count = 0
    failed_recipients = []

    for logs in recipients:
        user = logs.user
        tracking_url = url_for('track_click', mail_id=logs.mail_id, _external=True)

        html_body = f"""
        <p>{campaign.email_body or 'No Body'}</p>
        <p><a href="{tracking_url}">Click here to view details</a></p>
        """
        plain_body = f"{campaign.email_body or 'No Body'}\n\nClick here: {tracking_url}"

        msg = Message(
            subject=campaign.email_subject or "No Subject",
            sender="pranav@mailtrap.club",
            recipients=[user.email],
        )
        msg.body = plain_body
        msg.html = html_body

        try:
            mail.send(msg)
            sent_count += 1
            logs.sent_at = datetime.utcnow()  # mark as sent
            db.session.commit()
            print(f"✅ Sent to {user.email}")
        except Exception as e:
            failed_recipients.append(user.email)
            print(f"❌ Failed to send to {user.email}: {e}")

    if failed_recipients:
        flash(f"Failed to send to: {', '.join(failed_recipients)}", "danger")
    if sent_count:
        flash(f"Successfully sent {sent_count} email(s) ✅", "success")

    return redirect(url_for('view_campaign'))



#for tracking clicks
#for tracking clicks
@app.route('/track/<int:mail_id>')
def track_click(mail_id):
    mail_log = MailLog.query.get_or_404(mail_id)

    # Log click info
    click_log = ClickLog(
        mail_id=mail_id,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    db.session.add(click_log)
    db.session.flush()  # Get the click_id immediately

    # Update mail_log.opened_at if first time
    if not mail_log.opened_at:
        mail_log.opened_at = datetime.utcnow()

    db.session.commit()

    # Send awareness email after click
    user_email = mail_log.user.email
    campaign = mail_log.campaign
    
    # Awareness material URL
    awareness_material_url = "https://www.microsoft.com/en-us/security/blog/2020/02/20/how-to-protect-yourself-from-phishing-attacks/"

    awareness_msg = Message(
        subject=f"Security Awareness: {campaign.campaign_name}",
        sender="pranav@mailtrap.club",
        recipients=[user_email]
    )
    
    # Customize the awareness content
    awareness_msg.body = f"""
Hi {mail_log.user.full_name or mail_log.user.email},

You recently clicked on a link in a simulated phishing email titled "{campaign.campaign_name}".

This was part of a security awareness exercise to help you recognize phishing attempts.

🚨 IMPORTANT SECURITY TIPS:
• Always verify sender identity before clicking links
• Look for suspicious URLs or domains
• When in doubt, contact IT support
• Never enter credentials on suspicious websites

Learn more about phishing protection: {awareness_material_url}

Stay safe!
Security Team
    """

    awareness_msg.html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #d9534f;">🚨 Security Awareness Notice</h2>
        
        <p>Hi {mail_log.user.full_name or mail_log.user.email},</p>
        
        <p>You recently clicked on a link in a simulated phishing email titled "<strong>{campaign.campaign_name}</strong>".</p>
        
        <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #d9534f; margin: 20px 0;">
            <p><strong>This was part of a security awareness exercise</strong> to help you recognize phishing attempts.</p>
        </div>
        
        <h3 style="color: #333;">🛡️ Important Security Tips:</h3>
        <ul style="color: #555;">
            <li>Always verify sender identity before clicking links</li>
            <li>Look for suspicious URLs or domains</li>
            <li>When in doubt, contact IT support</li>
            <li>Never enter credentials on suspicious websites</li>
        </ul>
        
        <p><a href="{awareness_material_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Learn More About Phishing Protection</a></p>
        
        <p style="color: #666; font-size: 14px;">Stay safe!<br>Security Team</p>
    </div>
    """

    # Send the awareness email and log it
    try:
        mail.send(awareness_msg)
        print(f"✅ Awareness material sent to {user_email}")
        
        # 🎯 THIS IS THE KEY FIX: Log the awareness email in AwarenessLog
        awareness_log = AwarenessLog(
            click_id=click_log.click_id,  # Link to the click that triggered this
            material_link=awareness_material_url,
            sent_at=datetime.utcnow()
        )
        db.session.add(awareness_log)
        db.session.commit()
        
        print(f"Awareness log created with ID: {awareness_log.awareness_id}")
        
    except Exception as e:
        print(f"Failed to send awareness email to {user_email}: {e}")


    # Redirect the user to a confirmation or awareness landing page
    return redirect(url_for('awareness_landing'))


# to get the templates
@app.route("/get_template/<int:template_id>")
def get_template(template_id):
    template = EmailTemplate.query.get_or_404(template_id)
    return {
        "subject": template.subject,
        "body": template.body
    }


#to list all the templates
@app.route("/templates")
def list_templates():
    templates = EmailTemplate.query.all()
    return render_template("templates/list.html", templates=templates)


#to create new templates
@app.route("/templates/new", methods=["GET", "POST"])
def new_template():
    if request.method == "POST":
        name = request.form["name"]
        subject = request.form["subject"]
        body = request.form["body"]
        description = request.form.get("description")

        template = EmailTemplate(name=name, subject=subject, body=body, description=description)
        db.session.add(template)
        db.session.commit()
        return redirect(url_for("list_templates"))
    return render_template("templates/new.html")



#to edit templates
@app.route("/templates/<int:id>/edit", methods=["GET", "POST"])
def edit_template(id):
    template = EmailTemplate.query.get_or_404(id)
    if request.method == "POST":
        template.name = request.form["name"]
        template.subject = request.form["subject"]
        template.body = request.form["body"]
        template.description = request.form.get("description")
        db.session.commit()
        return redirect(url_for("list_templates"))
    return render_template("templates/edit.html", template=template)


# to delete templates
@app.route("/templates/<int:id>/delete", methods=["POST"])
def delete_template(id):
    template = EmailTemplate.query.get_or_404(id)
    db.session.delete(template)
    db.session.commit()
    return redirect(url_for("list_templates"))

@app.route("/awareness")
def awareness_landing():
    return render_template("awareness.html")

@app.route('/tables')
def create_tables():
    db.create_all()
    return "All tables created!"

@app.route("/")
def home():
    return redirect("/login")


if __name__=="__main__":
    app.run(debug=True)



# for creating default templates
# @app.route("/seed_templates")
# def seed_templates():
#     default_templates = [
#         {
#             "name": "Password Reset Scam",
#             "subject": "Reset your password immediately",
#             "body": "Your account has been flagged for unusual activity. Click the link below to reset your password:\n\nhttp://malicious-link.com"
#         },
#         {
#             "name": "Account Suspension Warning",
#             "subject": "Your account will be suspended",
#             "body": "We noticed suspicious activity. To keep your account active, please verify your identity:\n\nhttp://fake-link.com"
#         },
#         {
#             "name": "Free Gift Card Offer",
#             "subject": "Claim your free $100 Gift Card",
#             "body": "Congratulations! You are eligible for a $100 Gift Card. Click below to claim:\n\nhttp://phishy-offer.com"
#         },
#     ]

#     for t in default_templates:
#         exists = EmailTemplate.query.filter_by(name=t["name"]).first()
#         if not exists:
#             template = EmailTemplate(
#                 name=t["name"],
#                 subject=t["subject"],
#                 body=t["body"]
#             )
#             db.session.add(template)

#     db.session.commit()
#     return "Default templates seeded!"


