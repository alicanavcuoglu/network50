from datetime import datetime, timedelta, timezone
import imghdr
import os
from functools import wraps
import re
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
from werkzeug.utils import secure_filename


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
        image.save(
            os.path.join("static/avatars", str(session.get("user_id")) + file_ext)
        )

        return f"/{current_app.config['UPLOAD_AVATAR_PATH']}/{str(session.get('user_id')) + file_ext}"
    else:
        for ext in current_app.config["UPLOAD_EXTENSIONS"]:
            existing_file = f"{current_app.config['UPLOAD_AVATAR_PATH']}/{session.get('user_id')}{ext}"
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


def create_notification_message(notification):
    sender_name = f"{notification.sender.name} {notification.sender.surname}"

    match notification.notification_type.value:
        case "friend_request":
            return f"{sender_name} sent you a friend request"
        case "friend_accepted":
            return f"{sender_name} accepted your friend request"
        case "post_like":
            return f"{sender_name} liked your post"
        case "post_comment":
            return f"{sender_name} commented on your post"
        case "post_share":
            return f"{sender_name} shared your post"
        case "comment_like":
            return f"{sender_name} liked your comment"
        case _:
            return f"New notification from {sender_name}"


def create_notification_link(notification):
    match notification.notification_type.value:
        case "friend_request":
            return "/friends/requests"
        case "friend_accepted":
            return f"/profiles/{notification.sender.username}"
        case "post_like":
            return f"/posts/{notification.post_id}"
        case "post_comment":
            return f"/posts/{notification.post_id}#comment-{notification.comment_id}"
        case "post_share":
            return f"/posts/{notification.post_id}"
        case "comment_like":
            return f"/posts/{notification.post_id}#comment-{notification.comment_id}"
        case _:
            return "#"


# Generated by Claude AI
def process_hashtags(text):
    """
    Process text to convert hashtags into clickable links.
    Hashtags must:
    - Start with #
    - Contain only letters and numbers
    - Not contain spaces or special characters

    Example:
    Input: "Hello #World this is a #greatpost!"
    Output: 'Hello <a href="/hashtag/world">#{world}</a> this is a #<a href="/hashtag/greatpost">#{greatpost}</a>!'
    """
    # Pattern matches # followed by letters/numbers only
    pattern = r"#([a-zA-Z0-9]+)"

    def replace_tag(match):
        tag = match.group(1)  # Get the tag without the #
        # Convert to lowercase for case-insensitive handling
        tag_lower = tag.lower()
        return f'<a href="/tags/{tag_lower}">#{tag}</a>'

    # Replace all hashtags with their link versions
    processed_text = re.sub(pattern, replace_tag, text)

    return processed_text

# Also generated by Claude AI
def process_urls(text):
    """
    Process text to convert URLs into clickable links.
    Matches URLs starting with http://, https://, or www.
    """
    # Pattern for URLs - matches http://, https://, or www.
    url_pattern = r'(https?://[^\s]+)|(www\.[^\s]+)'
    
    def replace_url(match):
        url = match.group(0)
        # Add https:// to www. urls if needed
        if url.startswith('www.'):
            full_url = 'https://' + url
        else:
            full_url = url
        return f'<a href="{full_url}" target="_blank">{url}</a>'
    
    # Replace URLs with clickable links
    processed_text = re.sub(url_pattern, replace_url, text)
    
    return processed_text

# Combined processor for both URLs and hashtags
def process_text(text):
    """Process text for both URLs and hashtags"""
    # First process URLs
    text = process_urls(text)
    # Then process hashtags
    text = process_hashtags(text)
    return text