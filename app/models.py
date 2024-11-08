from app import db

import enum
from datetime import datetime
from typing import List

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func


# Association table for friends
friends_table = Table(
    "friends",
    db.Model.metadata,
    Column("user_id", Integer, ForeignKey("user.id")),
    Column("friend_id", Integer, ForeignKey("user.id")),
)

# Association table for pending friend requests
pending_requests_table = Table(
    "pending_requests",
    db.Model.metadata,
    Column("user_id", Integer, ForeignKey("user.id")),
    Column("pending_id", Integer, ForeignKey("user.id")),
)

# Association table for received friend requests
received_requests_table = Table(
    "received_requests",
    db.Model.metadata,
    Column("user_id", Integer, ForeignKey("user.id")),
    Column("request_id", Integer, ForeignKey("user.id")),
)


# User model
class User(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(200), nullable=False)

    image: Mapped[str] = mapped_column(String(300), nullable=True)
    name: Mapped[str] = mapped_column(String(150), nullable=True)
    surname: Mapped[str] = mapped_column(String(150), nullable=True)
    location: Mapped[str] = mapped_column(String(150), nullable=True)
    about: Mapped[str] = mapped_column(Text, nullable=True)
    working_on: Mapped[str] = mapped_column(String(200), nullable=True)
    interests: Mapped[str] = mapped_column(Text, nullable=True)
    classes: Mapped[str] = mapped_column(Text, nullable=True)
    links: Mapped[str] = mapped_column(Text, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)

    # Many-to-Many relationship for friends
    friends: Mapped[List["User"]] = relationship(
        "User",
        secondary=friends_table,
        primaryjoin=id == friends_table.c.user_id,
        secondaryjoin=id == friends_table.c.friend_id,
        backref="friends_with",
    )

    # Many-to-Many relationship for pending friend requests
    pending_requests: Mapped[List["User"]] = relationship(
        "User",
        secondary=pending_requests_table,
        primaryjoin=id == pending_requests_table.c.user_id,
        secondaryjoin=id == pending_requests_table.c.pending_id,
        backref="pending_from",
    )

    # Many-to-Many relationship for received friend requests
    received_requests: Mapped[List["User"]] = relationship(
        "User",
        secondary=received_requests_table,
        primaryjoin=id == received_requests_table.c.user_id,
        secondaryjoin=id == received_requests_table.c.request_id,
        backref="received_from",
    )

    posts: Mapped[List["Post"]] = relationship(
        back_populates="user", cascade="all, delete"
    )

    likes: Mapped[List["Like"]] = relationship(
        back_populates="user", cascade="all, delete"
    )

    def __repr__(self) -> str:
        return super().__repr__()


# Post model
class Post(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    # Reshare
    parent_id: Mapped[int] = mapped_column(ForeignKey("post.id"), nullable=True)

    content: Mapped[str] = mapped_column(Text, nullable=False)
    shares: Mapped[int] = mapped_column(Integer, default=0)

    # Likes
    likes: Mapped[List["Like"]] = relationship(
        primaryjoin="and_(Like.post_id == Post.id, Like.post_id.isnot(None))",
        back_populates="post",
        cascade="all, delete-orphan",
    )

    # Comments
    comments: Mapped[List["Comment"]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="posts")
    original_post: Mapped["Post"] = relationship("Post", remote_side=[id])

    def __repr__(self) -> str:
        return f"<Post {self.id} by User {self.user_id}>"

    def is_liked_by_user(self, user_id):
        return any(like.user_id == user_id for like in self.likes)


# Comment model
class Comment(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    post_id: Mapped[int] = mapped_column(ForeignKey("post.id"), nullable=False)

    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    post: Mapped["Post"] = relationship(back_populates="comments")
    user: Mapped["User"] = relationship()

    likes: Mapped[List["Like"]] = relationship(
        primaryjoin="and_(Like.comment_id == Comment.id, Like.comment_id.isnot(None))",
        back_populates="comment",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Comment {self.id} on Post {self.post_id}>"

    def is_liked_by_user(self, user_id):
        return any(like.user_id == user_id for like in self.likes)


# Like model
class Like(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    post_id: Mapped[int] = mapped_column(ForeignKey("post.id"), nullable=True)
    comment_id: Mapped[int] = mapped_column(ForeignKey("comment.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # One of post_id or comment_id must be filled
    __table_args__ = (
        db.CheckConstraint(
            "(post_id IS NOT NULL AND comment_id IS NULL) OR (post_id IS NULL AND comment_id IS NOT NULL)",
            name="like_on_one_type",
        ),
    )

    # Relationship to post and comment
    post: Mapped["Post"] = relationship(back_populates="likes", foreign_keys=[post_id])
    comment: Mapped["Comment"] = relationship(
        back_populates="likes", foreign_keys=[comment_id]
    )

    user: Mapped["User"] = relationship()

    def __repr__(self) -> str:
        return f"<Like {self.id} by User {self.user_id}>"


# Message model
class Message(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)

    sender: Mapped["User"] = relationship(
        foreign_keys=[sender_id], backref="sent_messages"
    )
    recipient: Mapped["User"] = relationship(
        foreign_keys=[recipient_id], backref="received_messages"
    )

    def __repr__(self):
        return f"<Message {self.id} from {self.sender_id} to {self.recipient_id}>"


# Notification Enum
class NotificationEnum(enum.Enum):
    FRIEND_REQUEST = "friend_request"
    FRIEND_ACCEPTED = "friend_accepted"
    POST_LIKE = "post_like"
    POST_COMMENT = "post_comment"
    POST_SHARE = "post_share"
    COMMENT_LIKE = "comment_like"


# Notification class
class Notification(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    sender_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    notification_type: Mapped[NotificationEnum] = mapped_column(
        # Modified with ChatGPT, before I was getting Enum keys instead of Enum values
        Enum(NotificationEnum, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )

    post_id: Mapped[int] = mapped_column(ForeignKey("post.id"), nullable=True)
    comment_id: Mapped[int] = mapped_column(ForeignKey("comment.id"), nullable=True)

    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationships
    recipient: Mapped["User"] = relationship(
        foreign_keys=[recipient_id], backref="received_notifications"
    )
    sender: Mapped["User"] = relationship(foreign_keys=[sender_id])
    post: Mapped["Post"] = relationship()
    comment: Mapped["Comment"] = relationship()

    def __repr__(self):
        return f"<Notification {self.id} from {self.sender_id} to {self.recipient_id}>"

    def to_dict(self):
        """Convert notification to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "type": self.notification_type.value,
            "sender_name": f"{self.sender.name} {self.sender.surname}",
            "sender_username": self.sender.username,
            "sender_image": self.sender.image,
            "created_at": self.created_at.isoformat(),
            "is_read": self.is_read,
            "post_id": self.post_id,
            "comment_id": self.comment_id,
        }
