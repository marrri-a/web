from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from sqlalchemy.orm import Session, joinedload, contains_eager
from sqlalchemy import func, desc, asc, or_, and_, text
from sqlalchemy.exc import IntegrityError

from . import models
from .models import User, Post, Category, Comment
from .auth import get_password_hash

def get_user(db: Session, user_id: int) -> Optional[User]:
    """
    Get user by ID.
    """
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Get user by email.
    """
    return db.query(User).filter(User.email == email).first()


def get_user_by_login(db: Session, login: str) -> Optional[User]:
    """
    Get user by login.
    """
    return db.query(User).filter(User.login == login).first()


def get_users(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    is_active: Optional[bool] = None

    query = db.query(User)
    
    if search:
        query = query.filter(
            or_(
                User.login.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%")
            )
        )
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    return query.order_by(desc(User.created_at)).offset(skip).limit(limit).all())

def create_user(db: Session, user_data: dict) -> User:
    """
    Create a new user.
    """
    if "password" in user_data:
        user_data["password_hash"] = get_password_hash(user_data.pop("password"))
    
    db_user = User(**user_data)
    db.add(db_user)
    try:
        db.commit()
        db.refresh(db_user)
    except IntegrityError as e:
        db.rollback()
        if "email" in str(e):
            raise ValueError("Email already registered")
        elif "login" in str(e):
            raise ValueError("Login already taken")
        raise
    return db_user


def update_user(db: Session, user_id: int, user_data: dict) -> Optional[User]:
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    
    if "password" in user_data and user_data["password"]:
        user_data["password_hash"] = get_password_hash(user_data.pop("password"))
    
    for field, value in user_data.items():
        if value is not None:
            setattr(db_user, field, value)
    
    db_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int) -> bool:
    """
    Delete a user.
    """
    db_user = get_user(db, user_id)
    if not db_user:
        return False
    
    db.delete(db_user)
    db.commit()
    return True
def get_post(db: Session, post_id: int) -> Optional[Post]:
    """
    Get post by ID with author and categories.
    """
    return db.query(Post).options(
        joinedload(Post.author),
        joinedload(Post.categories)
    ).filter(Post.id == post_id).first()


def get_post_by_slug(db: Session, slug: str) -> Optional[Post]:
    """
    Get post by slug.
    """
    return db.query(Post).options(
        joinedload(Post.author),
        joinedload(Post.categories)
    ).filter(Post.slug == slug).first()


def get_posts(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    author_id: Optional[int] = None,
    category_id: Optional[int] = None,
    is_published: bool = True,
    search: Optional[str] = None,
    order_by: str = "created_at",
    order: str = "desc"
) -> List[Post]:
    """
    Get posts with filtering, search and pagination.
    """
    query = db.query(Post).options(
        joinedload(Post.author),
        joinedload(Post.categories)
    )
    
    if is_published:
        query = query.filter(Post.is_published == True)
    
    if author_id:
        query = query.filter(Post.author_id == author_id)
    
    if category_id:
        query = query.join(Post.categories).filter(Category.id == category_id)
    
    if search:
        query = query.filter(
            or_(
                Post.title.ilike(f"%{search}%"),
                Post.content.ilike(f"%{search}%"),
                Post.summary.ilike(f"%{search}%")
            )
        )
    order_column = getattr(Post, order_by, Post.created_at)
    if order == "asc":
        query = query.order_by(asc(order_column))
    else:
        query = query.order_by(desc(order_column))
    
    return query.offset(skip).limit(limit).all()


def create_post(db: Session, post_data: dict) -> Post:

    categories = post_data.pop("categories", [])
    category_ids = post_data.pop("category_ids", [])
    from slugify import slugify
    title = post_data.get("title", "")
    post_data["slug"] = slugify(title) + "-" + datetime.utcnow().strftime("%Y%m%d%H%M%S")
    
    if post_data.get("is_published"):
        post_data["published_at"] = datetime.utcnow()
    
    db_post = Post(**post_data)
    if category_ids:
        categories = db.query(Category).filter(Category.id.in_(category_ids)).all()
        db_post.categories = categories
    
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post


def update_post(db: Session, post_id: int, post_data: dict) -> Optional[Post]:

    db_post = get_post(db, post_id)
    if not db_post:
        return None
    
    categories = post_data.pop("categories", [])
    category_ids = post_data.pop("category_ids", [])
    
    for field, value in post_data.items():
        if value is not None:
            setattr(db_post, field, value)
    if category_ids:
        categories = db.query(Category).filter(Category.id.in_(category_ids)).all()
        db_post.categories = categories
    
    db_post.updated_at = datetime.utcnow()
    
    if post_data.get("is_published") and not db_post.published_at:
        db_post.published_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_post)
    return db_post


def delete_post(db: Session, post_id: int) -> bool:
    """
    Delete a post.
    """
    db_post = get_post(db, post_id)
    if not db_post:
        return False
    
    db.delete(db_post)
    db.commit()
    return True


def increment_post_views(db: Session, post_id: int) -> None:

    db.query(Post).filter(Post.id == post_id).update({
        "view_count": Post.view_count + 1
    })
    db.commit()
def get_category(db: Session, category_id: int) -> Optional[Category]:
    """
    Get category by ID.
    """
    return db.query(Category).filter(Category.id == category_id).first()


def get_category_by_slug(db: Session, slug: str) -> Optional[Category]:
    """
    Get category by slug.
    """
    return db.query(Category).filter(Category.slug == slug).first()


def get_categories(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None
) -> List[Category]:
    query = db.query(Category)
    
    if search:
        query = query.filter(
            or_(
                Category.name.ilike(f"%{search}%"),
                Category.slug.ilike(f"%{search}%"),
                Category.description.ilike(f"%{search}%")
            )
        )
    
    return query.order_by(Category.name).offset(skip).limit(limit).all()


def create_category(db: Session, category_data: dict) -> Category:
    """
    Create a new category.
    """
    db_category = Category(**category_data)
    db.add(db_category)
    try:
        db.commit()
        db.refresh(db_category)
    except IntegrityError:
        db.rollback()
        raise ValueError("Category name or slug already exists")
    return db_category


def update_category(db: Session, category_id: int, category_data: dict) -> Optional[Category]:

    db_category = get_category(db, category_id)
    if not db_category:
        return None
    
    for field, value in category_data.items():
        if value is not None:
            setattr(db_category, field, value)
    
    db.commit()
    db.refresh(db_category)
    return db_category


def delete_category(db: Session, category_id: int) -> bool:
    db_category = get_category(db, category_id)
    if not db_category:
        return False
    
    db.delete(db_category)
    db.commit()
    return True
def get_comment(db: Session, comment_id: int) -> Optional[Comment]:

    return db.query(Comment).options(
        joinedload(Comment.user),
        joinedload(Comment.post)
    ).filter(Comment.id == comment_id).first()


def get_comments(
    db: Session,
    post_id: Optional[int] = None,
    user_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Comment]:
    query = db.query(Comment).options(
        joinedload(Comment.user),
        joinedload(Comment.post)
    )
    
    if post_id:
        query = query.filter(Comment.post_id == post_id)
    
    if user_id:
        query = query.filter(Comment.user_id == user_id)
    
    return query.order_by(desc(Comment.created_at)).offset(skip).limit(limit).all()


def create_comment(db: Session, comment_data: dict) -> Comment:
    db_comment = Comment(**comment_data)
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment


def update_comment(db: Session, comment_id: int, comment_data: dict) -> Optional[Comment]:
    db_comment = get_comment(db, comment_id)
    if not db_comment:
        return None
    
    db_comment.content = comment_data["content"]
    db_comment.is_edited = True
    db_comment.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_comment)
    return db_comment


def delete_comment(db: Session, comment_id: int) -> bool:
    db_comment = get_comment(db, comment_id)
    if not db_comment:
        return False
    
    db.delete(db_comment)
    db.commit()
    return True
def add_favorite(db: Session, user_id: int, post_id: int) -> bool:
    """
    Add post to user's favorites.
    """
    from .models import favorites
    existing = db.execute(
        favorites.select().where(
            favorites.c.user_id == user_id,
            favorites.c.post_id == post_id
        )
    ).first()
    
    if existing:
        return False

    db.execute(
        favorites.insert().values(user_id=user_id, post_id=post_id)
    )
    db.commit()
    return True


def remove_favorite(db: Session, user_id: int, post_id: int) -> bool:
    """
    Remove post from user's favorites.
    """
    from .models import favorites
    
    result = db.execute(
        favorites.delete().where(
            favorites.c.user_id == user_id,
            favorites.c.post_id == post_id
        )
    )
    db.commit()
    return result.rowcount > 0


def get_user_favorites(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[Post]:
    from .models import favorites
    
    return db.query(Post).options(
        joinedload(Post.author),
        joinedload(Post.categories)
    ).join(favorites).filter(
        favorites.c.user_id == user_id
    ).order_by(desc(favorites.c.created_at)).offset(skip).limit(limit).all()


def is_favorited(db: Session, user_id: int, post_id: int) -> bool:
    from .models import favorites
    
    result = db.execute(
        favorites.select().where(
            favorites.c.user_id == user_id,
            favorites.c.post_id == post_id
        )
    ).first()
    
    return result is not None

def follow_user(db: Session, follower_id: int, following_id: int) -> bool:
    from .models import subscriptions
    
    existing = db.execute(
        subscriptions.select().where(
            subscriptions.c.follower_id == follower_id,
            subscriptions.c.following_id == following_id
        )
    ).first()
    
    if existing or follower_id == following_id:
        return False
    db.execute(
        subscriptions.insert().values(
            follower_id=follower_id,
            following_id=following_id
        )
    )
    db.commit()
    return True

def unfollow_user(db: Session, follower_id: int, following_id: int) -> bool:
    """
    Unfollow a user.
    """
    from .models import subscriptions
    
    result = db.execute(
        subscriptions.delete().where(
            subscriptions.c.follower_id == follower_id,
            subscriptions.c.following_id == following_id
        )
    )
    db.commit()
    return result.rowcount > 0
def get_following(db: Session, user_id: int) -> List[User]:
    from .models import subscriptions
    
    return db.query(User).join(
        subscriptions, subscriptions.c.following_id == User.id
    ).filter(
        subscriptions.c.follower_id == user_id
    ).all()


def get_followers(db: Session, user_id: int) -> List[User]:
    from .models import subscriptions
    
    return db.query(User).join(
        subscriptions, subscriptions.c.follower_id == User.id
    ).filter(
        subscriptions.c.following_id == user_id
    ).all()


def is_following(db: Session, follower_id: int, following_id: int) -> bool:
    from .models import subscriptions
    
    result = db.execute(
        subscriptions.select().where(
            subscriptions.c.follower_id == follower_id,
            subscriptions.c.following_id == following_id
        )
    ).first()
    
    return result is not None