""" Due to circular import errors """

from dataclasses import asdict
from helpers import format_time_ago
from models import db, Notification
from events import socketio, connected_users


def create_notification(
    recipient_id, sender_id, notification_type, post_id=None, comment_id=None
):
    notification = Notification(
        recipient_id=recipient_id,
        sender_id=sender_id,
        notification_type=notification_type,
        post_id=post_id,
        comment_id=comment_id,
    )

    db.session.add(notification)

    return notification


def emit_notification(notification):
    """Emit notification to specific user"""
    recipient_sid = connected_users.get(notification.recipient_id)
    socketio.emit("notification", notification.to_dict(), to=recipient_sid)


def get_unread_notifications(user_id):
    """Get user's unread notifications"""
    return (
        Notification.query.filter_by(recipient_id=user_id, is_read=False)
        .order_by(Notification.created_at.desc())
        .limit(5)
        .all()
    )

def get_all_unread_notifications(user_id):
    """Get user's unread notifications"""
    return (
        Notification.query.filter_by(recipient_id=user_id, is_read=False)
        .order_by(Notification.created_at.desc())
        .all()
    )


def get_notifications(user_id):
    """Get user's all notifications"""
    return (
        Notification.query.filter_by(recipient_id=user_id)
        .order_by(Notification.created_at.desc())
        .all()
    )


def get_next_notification(user_id, notificationIds):
    next_unread_notification = (
        Notification.query.filter(
            Notification.recipient_id == user_id,
            Notification.is_read == False,
            Notification.id.not_in(notificationIds),
        )
        .order_by(Notification.created_at.desc())
        .first()
    )

    return next_unread_notification


def mark_as_read(notification_id, user_id):
    """Mark notification as read"""
    notification = Notification.query.filter(
        Notification.id == notification_id, Notification.recipient_id == user_id
    ).first()

    if notification:
        notification.is_read = True
        db.session.commit()

    return notification
