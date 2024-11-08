from flask import flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from app.routes import auth
from app.models import User
from app.helpers import array_to_str, logout_required, upload


@auth.route("/login", methods=["GET", "POST"])
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


@auth.route("/register", methods=["GET", "POST"])
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

        return redirect(url_for("auth.complete_profile"))

    return render_template("register.html")


@auth.route("/register/complete", methods=["GET", "POST"])
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


@auth.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")
