# app/events.py
from flask import request, session, url_for
from flask_socketio import emit

from app.helpers import format_time_ago
from app.models import db, Message, User

# Remove the socketio initialization from here
connected_users = {}

def init_socketio(socketio):
    @socketio.on("connect")
    def handle_connect():
        user_id = session["user_id"]
        if user_id:
            connected_users[user_id] = request.sid

    @socketio.on("disconnect")
    def handle_disconnect():
        user_id = session["user_id"]
        if user_id in connected_users:
            del connected_users[user_id]

    @socketio.on("send_message")
    def handle_send_message_event(data):
        username = data["username"]
        content = data["message"]
        is_first_message = data["firstMessage"]

        # Get the current user and the recipient
        current_user = db.get_or_404(User, session["user_id"])
        target_user = User.query.filter_by(username=username).first()

        if target_user and target_user.id in [friend.id for friend in current_user.friends]:
            # Create and save the new message
            message = Message(
                content=content, 
                recipient_id=target_user.id, 
                sender_id=current_user.id
            )

            db.session.add(message)
            db.session.commit()

            if is_first_message:
                emit(
                    "first_message_sent",
                    {
                        "success": True,
                        "chat_url": url_for("main.view_conversation", username=username),
                    },
                )

            message_data = {
                "content": message.content,
                "sender": {
                    "id": current_user.id,
                    "image": current_user.image,
                    "name": current_user.name,
                    "surname": current_user.surname,
                },
                "sender_id": current_user.id,
                "recipient_id": target_user.id,
                "created_at_iso": message.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "created_at": format_time_ago(message.created_at),
            }

            sender_sid = connected_users.get(current_user.id)
            recipient_sid = connected_users.get(target_user.id)

            if sender_sid:
                socketio.emit("receive_message", message_data, to=sender_sid)

            if recipient_sid:
                socketio.emit("receive_message", message_data, to=recipient_sid)
                socketio.emit("new_unread_message", {"new_message": True}, to=recipient_sid)

        else:
            emit("message_error", {"error": "Friend not found"})

    return socketio


