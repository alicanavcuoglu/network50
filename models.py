from datetime import datetime, timezone
from typing import List

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Boolean, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column, relationship


db = SQLAlchemy()


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

    # Sent friend requests
    # Received friend requests
    # Friends

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
