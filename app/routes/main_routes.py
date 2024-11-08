from markupsafe import Markup
from app import db
from flask import flash, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from app.errors.handlers import unauthorized
from app.models import Comment, Like, Message, Notification, NotificationEnum, Post, User
from app.routes import main
from app.services.notifications import create_notification, emit_notification, get_all_unread_notifications, get_next_notification, get_notifications, get_unread_notifications, mark_as_read
from app.helpers import array_to_str, create_notification_link, create_notification_message, format_message_time, format_time_ago, not_found, process_text, upload
from app.services.queries import get_friends, get_latest_conversations, has_unread_messages



@main.before_request
def load_user():
    user_id = session.get("user_id")
    if user_id:
        g.user = db.get_or_404(User, user_id)  # Load the user or 404 if not found
    else:
        g.user = None  # Set to None if no user is in session


# Instead of passing @login_required routes manually
@main.before_request
def require_login():
    if g.user is None:
        if request.endpoint not in ["login", "register"]:
            return redirect(url_for("auth.login"))
        
        
@main.before_request
def load_unread_message_status():
    user_id = session.get("user_id")

    if user_id:
        current_user = User.query.get(user_id)
        if current_user:
            g.has_unread_messages = has_unread_messages(current_user.id)
        else:
            g.has_unread_messages = False
    else:
        g.has_unread_messages = False


@main.before_request
def load_unread_notifications():
    user_id = session.get("user_id")

    if user_id:
        current_user = User.query.get(user_id)
        if current_user:
            g.unread_notifications = get_unread_notifications(current_user.id)
        else:
            g.unread_notifications = []
    else:
        g.unread_notifications = None


# Inject user variable to all pages
# https://flask.palletsprojects.com/en/3.0.x/templating/#context-processors
@main.app_context_processor
def inject_user():
    if "user_id" in session:
        user = User.query.get(session["user_id"])
        return dict(current_user=user)
    return {}


""" Register custom filters """


@main.app_template_filter("time_ago")
def time_ago_filter(dt):
    return format_time_ago(dt)


@main.app_template_filter("message_time")
def message_time_filter(dt):
    return format_message_time(dt)


@main.app_template_filter("notification_message")
def notification_message_converter(notification):
    return create_notification_message(notification)


@main.app_template_filter("notification_link")
def notification_link_converter(notification):
    return create_notification_link(notification)


@main.app_template_filter("process_text")
def process_text_filter(text):
    processed = process_text(text)
    return Markup(processed)


@main.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


""" FEED """


# Feed
@main.route("/")
def index():
    posts = Post.query.order_by(Post.created_at.desc()).all()

    # Attach the latest 3 comments to each post
    for post in posts:
        post.total_comments = len(post.comments)
        post.comments = sorted(post.comments, key=lambda x: x.created_at)[:3]

    return render_template("index.html", posts=posts)


# Friends feed
@main.route("/friends")
def friends():
    # TODO: Display posts from friends of the user
    posts = Post.query.all()
    return render_template("friends.html", posts=posts)


""" PROFILES """


@main.route("/profiles")
def user_list():
    # Get all users
    users = User.query.all()
    return render_template("profiles/list.html", users=users)


@main.route("/profiles/<username>")
def user_profile(username):
    user = db.first_or_404(db.select(User).filter_by(username=username))

    return render_template("profiles/profile.html", user=user)


""" PROFILE SETTINGS  """


@main.route("/settings")
def settings():
    user = db.get_or_404(User, session["user_id"])

    return render_template("profiles/settings.html", user=user)


@main.route("/profiles/<int:id>/delete", methods=["POST"])
def user_delete(id):
    user = db.get_or_404(User, id)

    if user.id != session["user_id"]:
        return unauthorized()

    db.session.delete(user)
    db.session.commit()
    session.clear()
    return redirect(url_for("main.index"))


@main.route("/settings/general", methods=["POST"])
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
            return redirect(url_for("main.settings"))

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

    return redirect(url_for("main.settings"))


@main.route("/settings/password", methods=["POST"])
def password_settings():
    current_password = request.form["current-password"]
    new_password = request.form["new-password"]
    new_password_again = request.form["new-password-again"]

    # Get user
    user = db.get_or_404(User, session["user_id"])

    # Check if the current password is correct
    if not check_password_hash(user.password, current_password):
        flash("Current password is incorrect.", "error")
        return redirect(url_for("main.settings"))

    # Check if the new passwords match
    if new_password != new_password_again:
        flash("New passwords do not match.", "error")
        return redirect(url_for("main.settings"))

    # Check password for minimum length
    if len(new_password) < 8:
        flash("New password must be at least 8 characters long.", "error")
        return redirect(url_for("main.settings"))

    # Update the user's password
    user.password = generate_password_hash(new_password)
    db.session.commit()

    flash("Your password has been changed successfully!", "success")
    return redirect(url_for("main.settings"))


@main.route("/settings/info", methods=["POST"])
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
    return redirect(url_for("main.settings"))


@main.route("/settings/classes", methods=["POST"])
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
    return redirect(url_for("main.settings"))


@main.route("/settings/links", methods=["POST"])
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
    return redirect(url_for("main.settings"))


""" POSTS """


# Post page
@main.route("/posts/<int:id>")
def post_page(id):
    post = Post.query.get_or_404(id)
    post.total_comments = len(post.comments)
    return render_template("post-page.html", post=post)


# Create post
@main.route("/post", methods=["POST"])
def create_post():
    content = request.form["content"]
    post = Post(content=content, user_id=session["user_id"])
    db.session.add(post)
    db.session.commit()
    return redirect(url_for("main.index"))


# Reshare post
@main.route("/post/<id>/reshare", methods=["POST"])
def reshare_post(id):
    current_user = db.get_or_404(User, session["user_id"])
    parent_post = Post.query.get_or_404(id)
    parent_post.shares += 1
    content = request.form["content"]

    post = Post(content=content, parent_id=parent_post.id, user_id=session["user_id"])
    db.session.add(post)
    db.session.flush()

    # Create a notification for original_post user
    if current_user.id != parent_post.user_id:
        notification = create_notification(
            recipient_id=parent_post.user_id,
            post_id=post.id,
            sender_id=session["user_id"],
            notification_type=NotificationEnum.POST_SHARE,
        )

    db.session.commit()

    # Emitting notification before commit creates error, took me an hour to debug
    if current_user.id != parent_post.user_id:
        # Emit notification with SocketIO
        emit_notification(notification)

    return redirect(url_for("main.index"))


# Delete post
@main.route("/post/delete/<id>", methods=["DELETE"])
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


# Like post
@main.route("/like/<id>", methods=["POST"])
def like_post(id):
    current_user = db.get_or_404(User, session["user_id"])
    post = db.get_or_404(Post, id)

    # Convert liked posts to array
    like = Like.query.filter_by(user_id=current_user.id, post_id=post.id).first()

    # Check if the post is already liked by the user
    if like:
        # Unlike the post if already liked
        db.session.delete(like)
        is_liked = False
    else:
        # Like the post
        new_like = Like(user_id=current_user.id, post_id=post.id)
        db.session.add(new_like)
        is_liked = True

    if current_user.id != post.user_id and not like:
        notification = create_notification(
            recipient_id=post.user_id,
            post_id=post.id,
            sender_id=current_user.id,
            notification_type=NotificationEnum.POST_LIKE,
        )

    # Update the user's liked posts and the post's like count, also create notification
    db.session.commit()

    if current_user.id != post.user_id and not like:
        # Emit notification with SocketIO
        emit_notification(notification)

    like_count = len(post.likes)

    return jsonify({"likes": like_count, "isLiked": is_liked})


# Like comment
@main.route("/like/comment/<id>", methods=["POST"])
def like_comment(id):
    current_user = db.get_or_404(User, session["user_id"])
    comment = db.get_or_404(Comment, id)

    # Liked comments
    like = Like.query.filter_by(user_id=current_user.id, comment_id=comment.id).first()

    # Check if the comment is already liked by the user
    if like:
        # Unlike the comment if already liked
        db.session.delete(like)
        is_liked = False
    else:
        # Like the comment
        new_like = Like(user_id=current_user.id, comment_id=comment.id)
        db.session.add(new_like)
        is_liked = True

    # Create a notification for comment's user
    if current_user.id != comment.user_id:
        notification = create_notification(
            recipient_id=comment.user_id,
            sender_id=current_user.id,
            comment_id=comment.id,
            post_id=comment.post_id,
            notification_type=NotificationEnum.COMMENT_LIKE,
        )

    # Update the user's liked posts and the post's like count
    db.session.commit()

    if current_user.id != comment.user_id:
        # Emit notification with SocketIO
        emit_notification(notification)

    like_count = len(comment.likes)

    return jsonify({"likes": like_count, "isLiked": is_liked})


@main.route("/comment/<id>", methods=["POST"])
def comment_post(id):
    content = request.json

    current_user = db.get_or_404(User, session["user_id"])
    post = db.get_or_404(Post, id)

    # Create comment
    comment = Comment(user_id=current_user.id, post_id=post.id, content=content)
    db.session.add(comment)
    db.session.flush()

    # Create a notification for post user
    if current_user.id != post.user_id:
        notification = create_notification(
            recipient_id=post.user_id,
            sender_id=current_user.id,
            comment_id=comment.id,
            post_id=post.id,
            notification_type=NotificationEnum.POST_COMMENT,
        )

    db.session.commit()

    if current_user.id != post.user_id:
        # Emit notification with SocketIO
        emit_notification(notification)

    comment_data = {
        "id": comment.id,
        "user_id": comment.user_id,
        "post_id": comment.post_id,
        "content": comment.content,
        "timestamp": comment.created_at,
    }

    return jsonify({"comment": comment_data})


# Delete comment
@main.route("/comment/delete/<id>", methods=["DELETE"])
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


# Load more comments
@main.route("/post/<id>/comments")
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


""" FRIENDS """


# Requests
@main.route("/friends/requests")
def display_friend_requests():
    user = db.get_or_404(User, session["user_id"])

    received_requests = (
        User.query.filter(User.id in user.received_requests.split(","))
        .order_by(User.received_requests.desc())
        .all()
        if user.received_requests
        else []
    )

    return render_template("profiles/requests.html", users=received_requests)


# Send a friend request
@main.route("/requests/<username>", methods=["POST"])
def send_friend_request(username):
    current_user = db.get_or_404(User, session["user_id"])
    target_user = User.query.filter_by(username=username).first()

    if not target_user:
        flash("User not found!", "error")
        return "", 200

    if target_user in current_user.friends:
        flash("You're already friends with this user.", "info")
        return "", 200

    elif target_user in current_user.pending_requests:
        flash("Friend request already sent.", "info")
        return "", 200

    # Accept the request if current user was already requested by the target user
    elif current_user in target_user.pending_requests:
        current_user.friends.append(target_user)
        target_user.friends.append(current_user)

        # Remove pending/received requests
        current_user.received_requests.remove(target_user)
        target_user.pending_requests.remove(current_user)

        # Send a friend accept notification to target user
        notification = create_notification(
            recipient_id=target_user.id,
            sender_id=current_user.id,
            notification_type=NotificationEnum.FRIEND_ACCEPTED,
        )

        # Emit notification with SocketIO
        emit_notification(notification)

        # Update friend request notification to read if not read yet
        unread_request = Notification.query.filter(
            Notification.recipient_id == current_user.id,
            Notification.sender_id == target_user.id,
            Notification.notification_type == NotificationEnum.FRIEND_REQUEST.value,
            Notification.is_read == False,
        ).first()

        # TODO: Test if this works seamlessly
        if unread_request:
            unread_request.is_read = True

        db.session.commit()

        flash(
            f"You are now friends with {target_user.name} {target_user.surname}.",
            "success",
        )
        return "", 200

    current_user.pending_requests.append(target_user)
    target_user.received_requests.append(current_user)

    # Send a friend request notification to target user
    notification = create_notification(
        recipient_id=target_user.id,
        sender_id=current_user.id,
        notification_type=NotificationEnum.FRIEND_REQUEST,
    )

    db.session.commit()

    # Emit notification with SocketIO
    emit_notification(notification)

    flash(
        f"Friend request sent to {target_user.name} {target_user.surname}.", "success"
    )
    return jsonify({"username": target_user.username, "status": "success"})


# Accept a friend request
@main.route("/requests/<username>/accept", methods=["POST"])
def accept_friend_request(username):
    current_user = db.get_or_404(User, session["user_id"])
    target_user = User.query.filter_by(username=username).one_or_404()

    if target_user in current_user.friends:
        flash("You're already friends with this user.", "info")
        return "", 200

    # Accept the request if current user was already requested by the target user
    current_user.friends.append(target_user)
    target_user.friends.append(current_user)

    # Remove pending/received requests
    current_user.received_requests.remove(target_user)
    target_user.pending_requests.remove(current_user)

    # Send a notification
    notification = create_notification(
        recipient_id=target_user.id,
        sender_id=current_user.id,
        notification_type=NotificationEnum.FRIEND_ACCEPTED,
    )

    # Emit notification with SocketIO
    emit_notification(notification)

    # Update friend request notification to read if not read yet
    unread_request = Notification.query.filter(
        Notification.recipient_id == current_user.id,
        Notification.sender_id == target_user.id,
        Notification.notification_type == NotificationEnum.FRIEND_REQUEST.value,
        Notification.is_read == False,
    ).first()

    # TODO: Test if this works seamlessly
    if unread_request:
        unread_request.is_read = True

    db.session.commit()

    flash(
        f"You're now friends with {target_user.name} {target_user.surname}.", "success"
    )
    return jsonify({"username": target_user.username, "status": "success"})


# Decline a friend request
@main.route("/requests/<username>/decline", methods=["POST"])
def decline_friend_request(username):
    current_user = db.get_or_404(User, session["user_id"])
    target_user = User.query.filter_by(username=username).one_or_404()

    if target_user in current_user.friends:
        flash("You're already friends with this user.", "info")
        return "", 200

    # Remove pending/received requests
    current_user.received_requests.remove(target_user)
    target_user.pending_requests.remove(current_user)

    db.session.commit()

    flash(
        f"Friend request from {target_user.name} {target_user.surname} declined.",
        "success",
    )
    return jsonify({"username": target_user.username, "status": "success"})


# Remove a user from friends
@main.route("/friends/<username>/remove", methods=["DELETE"])
def remove_friend(username):
    current_user = db.get_or_404(User, session["user_id"])
    target_user = User.query.filter_by(username=username).one_or_404()

    if target_user not in current_user.friends:
        flash("You're not friends with this user.", "info")
        return "", 200

    # Remove pending/received requests
    current_user.friends.remove(target_user)
    target_user.friends.remove(current_user)

    db.session.commit()

    flash(f"{target_user.name} {target_user.surname} removed from friends.", "success")
    return jsonify({"username": target_user.username, "status": "success"})


""" MESSAGES """


# Start a new conversation
@main.route("/messages/new")
def start_conversation():
    friends_data = get_friends(session["user_id"])
    friends = []
    for friend_data in friends_data:
        friend_json = {
            "id": friend_data.id,
            "username": friend_data.username,
            "name": friend_data.name,
            "surname": friend_data.surname,
            "image": friend_data.image,
        }
        friends.append(friend_json)

    return render_template("messages/create_message.html", friends=friends)


# Messages page
@main.route("/messages")
def view_messages():
    current_user = db.get_or_404(User, session["user_id"])
    messages = get_latest_conversations(current_user.id)

    return render_template("messages/index.html", messages=messages)


# Single message page
@main.route("/messages/<username>")
def view_conversation(username):
    # Get current user and friend
    current_user = db.get_or_404(User, session["user_id"])
    friend = User.query.filter_by(username=username).first_or_404()

    if current_user.username == username:
        flash("You can't chat with yourself!", "error")
        return redirect(url_for("main.view_messages"))

    # Limit the initial number of messages to load, for example, the latest 20
    message_limit = 20

    # Fetch initial messages between current user and friend
    messages = (
        Message.query.filter(
            (
                (Message.sender_id == current_user.id)
                & (Message.recipient_id == friend.id)
            )
            | (
                (Message.sender_id == friend.id)
                & (Message.recipient_id == current_user.id)
            )
        )
        .order_by(Message.created_at.desc())
        .limit(message_limit)
        .all()
    )

    # Reverse to show from oldest to newest after limiting
    messages.reverse()

    if messages:
        return render_template(
            "messages/conversation.html",
            messages=messages,
            friend=friend,
            has_more=len(messages) == message_limit,
        )
    else:
        return not_found()


# Load more messages
@main.route("/messages/<username>/more")
def load_more_conversation(username):
    # Get current user and friend
    current_user = db.get_or_404(User, session["user_id"])
    friend = User.query.filter_by(username=username).first_or_404()

    if current_user.username == username:
        flash("You can't chat with yourself!", "error")
        return redirect(url_for("main.view_messages"))

    # Limit the initial number of messages to load
    message_limit = 20
    page = int(request.args["page"]) + 1

    # Fetch initial messages between current user and friend
    messages = (
        Message.query.filter(
            (
                (Message.sender_id == current_user.id)
                & (Message.recipient_id == friend.id)
            )
            | (
                (Message.sender_id == friend.id)
                & (Message.recipient_id == current_user.id)
            )
        )
        .order_by(Message.created_at.desc())
        .paginate(page=page, per_page=message_limit)
    )

    message_list = []

    for message in messages:
        message_data = {
            "content": message.content,
            "sender": {
                "id": message.sender.id,
                "image": message.sender.image,
                "name": message.sender.name,
                "surname": message.sender.surname,
            },
            "sender_id": message.sender.id,
            "recipient_id": message.recipient_id,
            "created_at_iso": message.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "created_at": format_time_ago(message.created_at),
        }
        message_list.append(message_data)

    return jsonify({"messages": message_list, "has_next": messages.has_next})


# Update read status
@main.route("/messages/<username>/mark_read", methods=["POST"])
def mark_messages_as_read(username):
    # Get current user and friend
    current_user = db.get_or_404(User, session["user_id"])
    friend = User.query.filter_by(username=username).first_or_404()

    if current_user.username == username:
        flash("You can't chat with yourself!", "error")
        return redirect(url_for("main.view_messages"))

    unread_messages = Message.query.filter(
        Message.sender_id == friend.id,
        Message.recipient_id == current_user.id,
        Message.is_read == False,
    )

    for message in unread_messages:
        message.is_read = True

    other_unread_messages = Message.query.filter(
        Message.recipient_id == current_user.id, Message.is_read == False
    ).count()

    db.session.commit()
    return jsonify(
        {"success": True, "other_unread_messages": other_unread_messages > 0}
    )


@main.route("/notifications")
def notifications():
    current_user = db.get_or_404(User, session["user_id"])
    notifications = get_notifications(current_user.id)

    return render_template("notifications.html", notifications=notifications)


@main.route("/notifications/unread/all")
def all_unread_notifications():
    current_user = db.get_or_404(User, session["user_id"])
    notifications = get_all_unread_notifications(current_user.id)
    print(notifications)

    return render_template("notifications-unread.html", notifications=notifications)


@main.route("/notifications/unread")
def unread_notifications():
    current_user = db.get_or_404(User, session["user_id"])
    notifications = get_unread_notifications(current_user.id)
    return jsonify([n.to_dict() for n in notifications])


@main.route("/notifications/<int:notification_id>/read", methods=["POST"])
def mark_notification_read(notification_id):
    notification = mark_as_read(notification_id, session["user_id"])

    if not notification:
        flash("Notification not found!", "error")
        return jsonify({"status": "error", "message": "Notification not found"}), 404

    return jsonify({"status": "success"})


@main.route("/notifications/next-unread-notification", methods=["POST"])
def next_unread_notification():
    notifications = request.get_json()

    next_notification = get_next_notification(session["user_id"], notifications)

    if not next_notification:
        return jsonify({"has_more": False}), 204

    notification = next_notification.to_dict()

    return jsonify(notification)


@main.route("/notifications/mark-all-read", methods=["POST"])
def mark_all_notifications_read():
    current_user = db.get_or_404(User, session["user_id"])
    Notification.query.filter_by(recipient_id=current_user.id, is_read=False).update(
        {Notification.is_read: True}
    )
    db.session.commit()
    return jsonify({"status": "success"})


# Hashtag page
@main.route("/tags/<string:tag>")
def tag_view(tag):
    pattern = f"%#{tag}%"

    posts = (
        Post.query.filter(Post.content.ilike(pattern)).order_by(Post.id.desc()).all()
    )

    for post in posts:
        post.total_comments = len(post.comments)
        post.comments = sorted(post.comments, key=lambda x: x.created_at)[:3]

    return render_template("tags.html", posts=posts, tag=tag)
