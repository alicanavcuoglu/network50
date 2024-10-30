from flask import jsonify
from sqlalchemy import case, desc
from models import User, db, Message


# Friends of current user
def get_friends(user_id):
    current_user = db.get_or_404(User, user_id)

    return current_user.friends


# Errors fixed by ChatGPT
# Messages between current user and users
def get_latest_conversations(user_id):
    # Define user1_id and user2_id without LEAST and GREATEST
    latest_message_subquery = (
        db.session.query(
            case(
                (Message.sender_id < Message.recipient_id, Message.sender_id),
                else_=Message.recipient_id,
            ).label("user1_id"),
            case(
                (Message.sender_id > Message.recipient_id, Message.sender_id),
                else_=Message.recipient_id,
            ).label("user2_id"),
            db.func.max(Message.created_at).label("latest_created_at"),
        )
        .filter((Message.sender_id == user_id) | (Message.recipient_id == user_id))
        .group_by("user1_id", "user2_id")
        .subquery()
    )

    # Join with Message to get the full Message objects
    latest_messages = (
        db.session.query(Message)
        .join(
            latest_message_subquery,
            db.or_(
                db.and_(
                    Message.sender_id == latest_message_subquery.c.user1_id,
                    Message.recipient_id == latest_message_subquery.c.user2_id,
                ),
                db.and_(
                    Message.sender_id == latest_message_subquery.c.user2_id,
                    Message.recipient_id == latest_message_subquery.c.user1_id,
                ),
            )
            & (Message.created_at == latest_message_subquery.c.latest_created_at),
        )
        .order_by(Message.created_at.desc())
        .all()
    )

    return latest_messages


# Fetch messages exchanged between the current user and the other user
def get_conversation(user_id, other_user_id):
    messages = (
        Message.query.filter(
            ((Message.sender_id == user_id) & (Message.recipient_id == other_user_id))
            | ((Message.sender_id == other_user_id) & (Message.recipient_id == user_id))
        )
        .order_by(Message.created_at.asc())
        .all()
    )

    return messages


def start_conversation(): ...
