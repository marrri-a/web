from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean,
    ForeignKey, Table, Index, CheckConstraint
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from email_validator import validate_email, EmailNotValidError

from .database import Base
post_categories = Table(
    "post_categories",
    Base.metadata,
    Column("post_id", Integer, ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", Integer, ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now())
)
favorites = Table(
    "favorites",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("post_id", Integer, ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now())
)
subscriptions = Table(
    "subscriptions",
    Base.metadata,
    Column("follower_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("following_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    CheckConstraint("follower_id != following_id", name="check_no_self_follow")
)
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    login = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100))
    bio = Column(Text)
    avatar_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="user", cascade="all, delete-orphan")
    liked_posts = relationship("Post", secondary=favorites, back_populates="liked_by")
    following = relationship(
        "User",
        secondary=subscriptions,
        primaryjoin=(id == subscriptions.c.follower_id),
        secondaryjoin=(id == subscriptions.c.following_id),
        back_populates="followers"
    )
    followers = relationship(
        "User",
        secondary=subscriptions,
        primaryjoin=(id == subscriptions.c.following_id),
        secondaryjoin=(id == subscriptions.c.follower_id),
        back_populates="following"
    )

    @validates("email")
    def validate_email(self, key: str, email: str) -> str:
        try:
            valid = validate_email(email)
            return valid.email
        except EmailNotValidError as e:
            raise ValueError(str(e))

    @validates("login")
    def validate_login(self, key: str, login: str) -> str:
        if len(login) < 3:
            raise ValueError("Login must be at least 3 characters long")
        if len(login) > 50:
            raise ValueError("Login must be at most 50 characters long")
        return login


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    posts = relationship("Post", secondary=post_categories, back_populates="categories")


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, index=True)
    content = Column(Text, nullable=False)
    summary = Column(Text)
    is_published = Column(Boolean, default=True)
    published_at = Column(DateTime(timezone=True))
    view_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    author = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    categories = relationship("Category", secondary=post_categories, back_populates="posts")
    liked_by = relationship("User", secondary=favorites, back_populates="liked_posts")

    __table_args__ = (
        Index("idx_posts_author_id", "author_id"),
        Index("idx_posts_created_at", "created_at"),
        Index("idx_posts_title_content", "title", "content"),
    )


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    parent_id = Column(Integer, ForeignKey("comments.id", ondelete="CASCADE"))
    is_edited = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    post = relationship("Post", back_populates="comments")
    user = relationship("User", back_populates="comments")
    parent = relationship("Comment", remote_side=[id], backref="replies")
    __table_args__ = (
        Index("idx_comments_post_id", "post_id"),
        Index("idx_comments_user_id", "user_id"),
        Index("idx_comments_created_at", "created_at"),
    )
class UserBase(BaseModel):
    email: EmailStr
    login: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = None
    avatar_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    login: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)


class UserRead(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime


class UserWithStats(UserRead):
    posts_count: int = 0
    followers_count: int = 0
    following_count: int = 0


class CategoryBase(BaseModel):
    name: str = Field(..., max_length=100)
    slug: str = Field(..., max_length=100)
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    slug: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
class CategoryRead(CategoryBase):
    id: int
    created_at: datetime
class PostBase(BaseModel):
    title: str = Field(..., max_length=200)
    content: str
    summary: Optional[str] = None
    is_published: bool = True
    category_ids: Optional[List[int]] = None

    model_config = ConfigDict(from_attributes=True)


class PostCreate(PostBase):
    pass


class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    content: Optional[str] = None
    summary: Optional[str] = None
    is_published: Optional[bool] = None
    category_ids: Optional[List[int]] = None


class PostRead(PostBase):
    id: int
    author_id: int
    slug: str
    view_count: int
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    author: Optional[UserRead] = None
    categories: List[CategoryRead] = []


class PostWithStats(PostRead):
    likes_count: int = 0
    comments_count: int = 0


class CommentBase(BaseModel):
    content: str
    parent_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class CommentCreate(CommentBase):
    pass


class CommentUpdate(BaseModel):
    content: str


class CommentRead(CommentBase):
    id: int
    post_id: int
    user_id: int
    is_edited: bool
    created_at: datetime
    updated_at: datetime
    user: Optional[UserRead] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    is_admin: bool = False