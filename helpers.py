from datetime import datetime, timedelta, timezone
import imghdr
import os
from functools import wraps
from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    send_from_directory,
    session,
    url_for,
)
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy import select
from werkzeug.utils import secure_filename

from models import User, db, Message


def not_found():
    return render_template("not-found.html")


# Login required
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


# Logout required
def logout_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if session.get("user_id"):
            flash("You are already authenticated.", "info")
            return redirect(url_for("index"))
        return func(*args, **kwargs)

    return decorated_function


# """ EMAIL VERIFICATION """
# def generate_token(email):
#     serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
#     return serializer.dumps(email, salt=current_app.config["SECURITY_PASSWORD_SALT"])


# def confirm_token(token, expiration=3600):
#     serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
#     try:
#         email = serializer.loads(
#             token, salt=current_app.config["SECURITY_PASSWORD_SALT"], max_age=expiration
#         )
#         return email
#     except Exception:
#         return False

# def send_email(to, subject, template):
#     from app import mail
#     msg = Message(
#         subject,
#         recipients=[to],
#         html=template,
#         sender=current_app.config["MAIL_DEFAULT_SENDER"],
#     )
#     mail.send(msg)


def array_to_str(array):
    return ",".join(array)


def validate_image(stream):
    header = stream.read(512)
    stream.seek(0)
    format = imghdr.what(None, header)
    if not format:
        return None
    return "." + (format if format != "jpeg" else "jpg")


# Upload an image
def upload(image):
    filename = secure_filename(image.filename)

    # check if file exists
    if filename != "":
        file_ext = os.path.splitext(filename)[1]
        if file_ext not in current_app.config[
            "UPLOAD_EXTENSIONS"
        ] or file_ext != validate_image(image.stream):
            flash("Please only upload an allowed image format.", "error")
            return redirect("/file")
        image.save(os.path.join("static/avatars", str(session.get("user_id")) + file_ext))

        return f"/{current_app.config["UPLOAD_AVATAR_PATH"]}/{str(session.get("user_id")) + file_ext}"
    else:
        for ext in current_app.config["UPLOAD_EXTENSIONS"]:
            existing_file = (
                f"{current_app.config["UPLOAD_AVATAR_PATH"]}/{session.get("user_id")}{ext}"
            )
            if os.path.exists(existing_file):
                os.remove(existing_file)
                flash("Your profile picture was deleted.", "success")
        return None


# TODO: Remove images on user delete
# def remove_image():


# By ChatGPT
def format_time_ago(dt: datetime):
    now = datetime.utcnow()
    diff = now - dt

    # Display minutes ago if less than 1 hours
    if diff < timedelta(minutes=60):
        minutes = diff.seconds // 60
        return f"{minutes}m" if minutes > 1 else "just now"

    # Display hours ago if less than 24 hours
    elif diff < timedelta(hours=24):
        hours = diff.seconds // 3600
        return f"{hours}h"

    # Display days ago if within the last 7 days
    elif diff < timedelta(days=7):
        days = diff.days
        return f"{days}d"

    # Display as mm-dd-yyyy if older than 7 days
    else:
        return dt.strftime("%m-%d-%Y")


def format_message_time(dt: datetime):
    now = datetime.utcnow()
    diff = now - dt

    # Display minutes ago if less than 1 hours
    if diff < timedelta(minutes=60):
        minutes = diff.seconds // 60
        return f"{minutes} mins ago" if minutes > 1 else "Just now"

    # Display hours ago if less than 24 hours
    elif diff < timedelta(hours=24):
        hours = diff.seconds // 3600
        return f"{hours} hours ago"

    # Display days ago if within the last 7 days
    elif diff < timedelta(days=7):
        days = diff.days
        return f"{days} days ago" if days > 1 else "Yesterday"

    # Display as 'Month Day'
    elif diff < timedelta(days=365):
        return dt.strftime("%b %d")

    # Display as mm-dd-yyyy if older than 7 days
    else:
        return dt.strftime("%b %d, %Y")


# Return unread messages
def has_unread_messages(user_id):
    # Count the unread messages for the current user
    unread_count = db.session.execute(
        select(Message.id).where(
            (Message.recipient_id == user_id) & (Message.is_read == False)
        )
    ).scalar() or 0

    return unread_count > 0
