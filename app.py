from datetime import datetime
import imghdr
import os
import uuid

import click
from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask.cli import with_appcontext
from flask_mail import Mail
from flask_migrate import Migrate
from markupsafe import escape
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from config import Config
from helpers import (
    array_to_str,
    format_time_ago,
    login_required,
    logout_required,
    not_found,
    upload,
    validate_image,
)
from models import Comment, Like, Post, User, db

load_dotenv()

app = Flask(__name__)
migrate = Migrate(app, db)

app.config.from_object(Config)

db.init_app(app)
mail = Mail(app)


""" CLEAR DATABASE """


# Make sure delete_all_data is correctly defined in this file.
def delete_all_data():
    db.session.query(User).delete()
    db.session.query(Comment).delete()
    db.session.query(Post).delete()
    db.session.commit()


@click.command(name="delete-db-data")
@with_appcontext
def delete_db_data_command():
    delete_all_data()
    click.echo("All data has been deleted from the database.")


app.cli.add_command(delete_db_data_command)


# Inject user variable to all pages
# https://flask.palletsprojects.com/en/3.0.x/templating/#context-processors
@app.context_processor
def inject_user():
    if "user_id" in session:
        user = User.query.get(session["user_id"])
        return dict(current_user=user)
    return dict(current_user=None)


@app.errorhandler(404)
def not_found_error(error):
    return render_template("not-found.html")


@app.errorhandler(413)
def too_large(e):
    return "File is too large", 413


# unauthorized
def unauthorized():
    return render_template("unauthorized.html")


# Register custom filter
@app.template_filter("time_ago")
def time_ago_filter(dt):
    return format_time_ago(dt)


# @app.route("/email")
# def email():
#     return os.getenv("EMAIL_PASSWORD")

# @app.route("/file/<filename>")
# def uploads(filename):
#     return send_from_directory("static/avatars", filename)


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/login", methods=["GET", "POST"])
@logout_required
def login():
    """Log user in"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user is None or not check_password_hash(user.password, password):
            flash("Invalid username or password!", "error")
            return redirect("/login")

        # Remember which user has logged in
        session["user_id"] = user.id

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/profiles")
def user_list():
    # Get all users
    users = User.query.all()
    return render_template("profiles/list.html", users=users)


@app.route("/register", methods=["GET", "POST"])
@logout_required
def register():
    if request.method == "POST":
        # Form values
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        confirmation = request.form["confirmation"]

        # Ensure fullname was submitted
        if not username or not email or not password or not confirmation:
            flash("Please fill all fields!", "error")
            return redirect("/register")

        # Check username
        if User.query.filter_by(username=username).first():
            flash("Username exists!", "error")
            return redirect("/register")

        # Check email
        if User.query.filter_by(email=email).first():
            flash("Email exists!", "error")
            return redirect("/register")

        # Check passwords
        if password != confirmation:
            flash("Passwords should match!", "error")
            return redirect("/register")

        # Check password for minimum length
        if len(password) < 8:
            flash("New password must be at least 8 characters long.", "error")
            return redirect("/register")

        # Generate hash password to ensure safety
        hashed_password = generate_password_hash(password)

        # User model
        user = User(username=username, email=email, password=hashed_password)

        db.session.add(user)
        db.session.commit()
        session["user_id"] = user.id

        # token = generate_token(email)
        # confirm_url = url_for("confirm_email", token=token, _external=True)
        # html = render_template("profiles/email_confirmation.html", confirm_url=confirm_url)
        # subject = "Please confirm your email"
        # send_email(user.email, subject, html)

        return redirect(url_for("complete_profile"))

    return render_template("register.html")


@app.route("/register/complete", methods=["GET", "POST"])
@login_required
def complete_profile():
    if request.method == "POST":
        # Ensure user exists
        user = db.get_or_404(User, session["user_id"])
        if not user:
            return redirect("/login")

        # Form values
        image = request.files["image"]
        name = request.form["name"]
        surname = request.form["surname"]
        location = request.form["location"]
        about = request.form["about-me"]
        working_on = request.form["working-on"]
        interests = array_to_str(request.form.getlist("interests[]"))
        classes = array_to_str(request.form.getlist("classes[]"))
        links = array_to_str(request.form.getlist("link[]"))

        # Check required fields exists
        if not name or not surname or not about:
            flash("Please fill the required fields!", "error")
            return redirect("/register/complete")

        image_path = upload(image)

        # Update user
        user.image = image_path
        user.name = name
        user.surname = surname
        user.location = location
        user.about = about
        user.working_on = working_on
        user.interests = interests
        user.classes = classes
        user.links = links
        user.is_completed = True

        # Save changes
        try:
            db.session.commit()
            flash("Successfully created an account.", "success")
            return redirect("/")
        except:
            db.session.rollback()
            flash("Something went wrong, try again.", "error")
            return redirect("/register/complete")

    return render_template("profiles/complete.html")


# # Email confirmation from https://www.freecodecamp.org/news/setup-email-verification-in-flask-app/
# @app.route("/confirm/<token>")
# @login_required
# def confirm_email(token):
#     current_user = User.query.get(session["user_id"])
#     if current_user.is_confirmed:
#         flash("Account already confirmed.", "success")
#         return redirect(url_for("index"))
#     email = confirm_token(token)
#     user = User.query.filter_by(email=current_user.email).first_or_404()
#     if user.email == email:
#         user.is_confirmed = True
#         user.confirmed_on = datetime.now()
#         db.session.add(user)
#         db.session.commit()
#         flash("You have confirmed your account. Thanks!", "success")
#     else:
#         flash("The confirmation link is invalid or has expired.", "error")
#     return redirect(url_for("index"))


@app.route("/profiles/<username>")
def user_profile(username):
    user = db.first_or_404(db.select(User).filter_by(username=username))

    return render_template("profiles/profile.html", user=user)


@app.route("/settings")
def settings():
    user = db.get_or_404(User, session["user_id"])

    return render_template("profiles/settings.html", user=user)


@app.route("/profiles/<int:id>/delete", methods=["POST"])
def user_delete(id):
    user = db.get_or_404(User, id)

    if user.id != session["user_id"]:
        return unauthorized()

    db.session.delete(user)
    db.session.commit()
    session.clear()
    return redirect(url_for("index"))


""" SETTINGS """


@app.route("/settings/general", methods=["POST"])
@login_required
def general_settings():
    image = request.files["image"]
    name = request.form["name"]
    surname = request.form["surname"]
    email = request.form["email"]

    # Get user
    current_user = db.get_or_404(User, session["user_id"])

    # If email exists don't change
    if email and email != current_user.email:
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash(
                "This email is already in use. Please use a different email.", "error"
            )
            return redirect(url_for("settings"))

    if name and name != current_user.name:
        current_user.name = name
    if surname and surname != current_user.surname:
        current_user.surname = surname
    if email and email != current_user.email:
        current_user.email = email

    image_path = upload(image)
    current_user.image = image_path

    # Save changes
    try:
        db.session.commit()
        flash("Your profile has been updated successfully!", "success")
    except:
        db.session.rollback()
        flash("Something went wrong, try again.", "error")

    return redirect(url_for("settings"))


@app.route("/settings/password", methods=["POST"])
@login_required
def password_settings():
    current_password = request.form["current-password"]
    new_password = request.form["new-password"]
    new_password_again = request.form["new-password-again"]

    # Get user
    user = db.get_or_404(User, session["user_id"])

    # Check if the current password is correct
    if not check_password_hash(user.password, current_password):
        flash("Current password is incorrect.", "error")
        return redirect(url_for("settings"))

    # Check if the new passwords match
    if new_password != new_password_again:
        flash("New passwords do not match.", "error")
        return redirect(url_for("settings"))

    # Check password for minimum length
    if len(new_password) < 8:
        flash("New password must be at least 8 characters long.", "error")
        return redirect(url_for("settings"))

    # Update the user's password
    user.password = generate_password_hash(new_password)
    db.session.commit()

    flash("Your password has been changed successfully!", "success")
    return redirect(url_for("settings"))


@app.route("/settings/info", methods=["POST"])
@login_required
def info_settings():
    # Get user
    user = db.get_or_404(User, session["user_id"])

    # Get form data
    location = request.form.get("location")
    about_me = request.form.get("about-me")
    working_on = request.form.get("working-on")
    interests = request.form.getlist("interests[]")

    # Convert array to string
    interests_string = array_to_str(interests)

    # Update user fields if they have changed
    if location != user.location:
        user.location = location

    if about_me != user.about:
        user.about = about_me

    if working_on != user.working_on:
        user.working_on = working_on

    # Update interests if changed
    if interests_string != user.interests:
        user.interests = interests_string

    # Commit the changes to the database
    db.session.commit()

    # Flash success message and redirect
    flash("Your information has been updated successfully.", "success")
    return redirect(url_for("settings"))


@app.route("/settings/classes", methods=["POST"])
@login_required
def classes_settings():
    selected_classes = request.form.getlist("classes[]")

    classes_string = array_to_str(selected_classes)

    # Get the user
    user = db.get_or_404(User, session["user_id"])

    # Update the user's classes field with the new values
    user.classes = classes_string

    # Save changes to the database
    db.session.commit()

    # Flash a success message and redirect to the settings page
    flash("Your classes have been updated successfully!", "success")
    return redirect(url_for("settings"))


@app.route("/settings/links", methods=["POST"])
@login_required
def links_settings():
    links = request.form.getlist("link[]")

    links_string = array_to_str(links)

    # Get the user
    user = db.get_or_404(User, session["user_id"])

    # Update the user's links
    user.links = links_string

    # Save changes to the database
    db.session.commit()

    # Flash a success message and redirect to the settings page
    flash("Your links have been updated successfully!", "success")
    return redirect(url_for("settings"))


""" POSTS """


# Feed
@app.route("/")
@login_required
def index():
    posts = Post.query.order_by(Post.created_at.desc()).all()

    # Attach the latest 3 comments to each post
    for post in posts:
        post.total_comments = len(post.comments)
        post.comments = sorted(post.comments, key=lambda x: x.created_at)[:3]

    return render_template("index.html", posts=posts)


# Friends feed
@app.route("/friends")
@login_required
def friends():
    # TODO: Display posts from friends of the user
    posts = Post.query.all()
    return render_template("friends.html", posts=posts)

# Post page
@app.route("/posts/<int:id>")
@login_required
def post_page(id):
    post = Post.query.get_or_404(id)
    post.total_comments = len(post.comments)
    return render_template("post-page.html", post=post)


# Create post
@app.route("/post", methods=["POST"])
@login_required
def create_post():
    content = request.form["content"]
    post = Post(content=content, user_id=session["user_id"])
    db.session.add(post)
    db.session.commit()
    return redirect(url_for("index"))

# Reshare post
@app.route("/post/<id>/reshare", methods=["POST"])
@login_required
def reshare_post(id):
    parent_post = Post.query.get_or_404(id)
    content = request.form["content"]
    post = Post(content=content, parent_id=parent_post.id, user_id=session["user_id"])
    db.session.add(post)
    db.session.commit()
    return redirect(url_for("index"))


# Delete post
@app.route("/post/delete/<id>", methods=["DELETE"])
@login_required
def delete_post(id):
    post = Post.query.get_or_404(id)

    if not post:
        flash("Can't delete the post!", "error")
        return "bad request!", 400

    if post.user_id != session["user_id"]:
        flash("You don't have permission to delete this post.", "error")
        return unauthorized()

    db.session.delete(post)
    db.session.commit()
    flash("Post deleted successfully.", "success")

    return jsonify({"success": True})


# Likepost
@app.route("/like/<id>", methods=["POST"])
@login_required
def like_post(id):
    user = db.get_or_404(User, session["user_id"])
    post = db.get_or_404(Post, id)

    # Convert liked posts to array
    like = Like.query.filter_by(user_id=user.id, post_id=post.id).first()

    # Check if the post is already liked by the user
    if like:
        # Unlike the post if already liked
        db.session.delete(like)
        is_liked = False
    else:
        # Like the post
        new_like = Like(user_id=user.id, post_id=post.id)
        db.session.add(new_like)
        is_liked = True

    # Update the user's liked posts and the post's like count
    db.session.commit()
    like_count = len(post.likes)

    return jsonify({"likes": like_count, "isLiked": is_liked})


# Like comment
@app.route("/like/comment/<id>", methods=["POST"])
@login_required
def like_comment(id):
    user = db.get_or_404(User, session["user_id"])
    comment = db.get_or_404(Comment, id)
    print("here")
    print("after comment")
    # Convert liked posts to array
    like = Like.query.filter_by(user_id=user.id, comment_id=comment.id).first()
    print("after like")

    # Check if the post is already liked by the user
    if like:
        # Unlike the post if already liked
        db.session.delete(like)
        is_liked = False
    else:
        # Like the post
        new_like = Like(user_id=user.id, comment_id=comment.id)
        db.session.add(new_like)
        is_liked = True

    print("after sessions")
    # Update the user's liked posts and the post's like count
    db.session.commit()
    like_count = len(comment.likes)
    print("after count")

    return jsonify({"likes": like_count, "isLiked": is_liked})


@app.route("/comment/<id>", methods=["POST"])
@login_required
def comment_post(id):
    content = request.json

    user = db.get_or_404(User, session["user_id"])
    post = db.get_or_404(Post, id)

    # Create comment
    comment = Comment(user_id=user.id, post_id=post.id, content=content)

    db.session.add(comment)
    db.session.commit()

    comment_data = {
        "id": comment.id,
        "user_id": comment.user_id,
        "post_id": comment.post_id,
        "content": comment.content,
        "timestamp": comment.created_at,
    }

    return jsonify({"comment": comment_data})


# Delete comment
@app.route("/comment/delete/<id>", methods=["DELETE"])
@login_required
def delete_comment(id):
    comment = Comment.query.get_or_404(id)

    if not comment:
        flash("Can't delete the comment!", "error")
        return "bad request!", 400

    if comment.user_id != session["user_id"]:
        flash("You don't have permission to delete this comment.", "error")
        return unauthorized()

    db.session.delete(comment)
    db.session.commit()
    flash("Comment deleted successfully.", "success")

    return jsonify({"success": True})


@app.route("/post/<id>/comments")
@login_required
def load_more_comments(id):
    page = int(request.args["page"]) + 1
    comments = (
        Comment.query.filter_by(post_id=id)
        .order_by(Comment.created_at.asc())
        .paginate(page=page, per_page=3)
    )
    comment_list = []

    for comment in comments:
        # Append json data
        comment_data = {
            "id": comment.id,
            "post_id": comment.post_id,
            "user": {
                "username": comment.user.username,
                "name": comment.user.name,
                "surname": comment.user.surname,
                "image": comment.user.image,
            },
            "content": comment.content,
            "created_at_iso": comment.created_at,
            "created_at": format_time_ago(comment.created_at),
            "own_post": comment.user.id == session["user_id"],
        }
        comment_list.append(comment_data)

    return jsonify({"comments": comment_list, "has_next": comments.has_next})
