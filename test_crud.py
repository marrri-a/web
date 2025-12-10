import pytest
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app import crud, models
from app.database import Base, engine, SessionLocal


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
    Base.metadata.drop_all(bind=engine)


def test_create_user(db: Session):
    """
    Test creating a user.
    """
    user_data = {
        "email": "test@example.com",
        "login": "testuser",
        "password_hash": "hashedpassword",
        "full_name": "Test User"
    }
    
    user = crud.create_user(db, user_data)
    
    assert user.email == "test@example.com"
    assert user.login == "testuser"
    assert user.full_name == "Test User"
    assert user.is_active == True
    assert user.is_admin == False


def test_get_user_by_email(db: Session):
    """
    Test getting a user by email.
    """
    user_data = {
        "email": "test@example.com",
        "login": "testuser",
        "password_hash": "hashedpassword"
    }
    
    crud.create_user(db, user_data)
    
    user = crud.get_user_by_email(db, "test@example.com")
    assert user is not None
    assert user.email == "test@example.com"


def test_get_user_by_login(db: Session):
    """
    Test getting a user by login.
    """
    user_data = {
        "email": "test@example.com",
        "login": "testuser",
        "password_hash": "hashedpassword"
    }
    
    crud.create_user(db, user_data)
    
    user = crud.get_user_by_login(db, "testuser")
    assert user is not None
    assert user.login == "testuser"


def test_get_users_with_search(db: Session):
    """
    Test getting users with search.
    """
    # Create test users
    users_data = [
        {"email": "john@example.com", "login": "john", "password_hash": "hash1", "full_name": "John Doe"},
        {"email": "jane@example.com", "login": "jane", "password_hash": "hash2", "full_name": "Jane Smith"},
        {"email": "bob@example.com", "login": "bob", "password_hash": "hash3", "full_name": "Bob Johnson"},
    ]
    
    for user_data in users_data:
        crud.create_user(db, user_data)
    
    # Search for "john"
    users = crud.get_users(db, search="john")
    assert len(users) == 2  # John Doe and Johnson
    assert any(user.login == "john" for user in users)


def test_create_post(db: Session):
    """
    Test creating a post.
    """
    # Create user first
    user_data = {
        "email": "author@example.com",
        "login": "author",
        "password_hash": "hashedpassword"
    }
    user = crud.create_user(db, user_data)
    
    # Create post
    post_data = {
        "author_id": user.id,
        "title": "Test Post",
        "content": "This is a test post content.",
        "summary": "Test summary",
        "is_published": True
    }
    
    post = crud.create_post(db, post_data)
    
    assert post.title == "Test Post"
    assert post.author_id == user.id
    assert post.is_published == True
    assert post.published_at is not None


def test_get_posts_with_filtering(db: Session):
    """
    Test getting posts with filtering.
    """
    # Create users
    user1 = crud.create_user(db, {
        "email": "user1@example.com",
        "login": "user1",
        "password_hash": "hash1"
    })
    
    user2 = crud.create_user(db, {
        "email": "user2@example.com",
        "login": "user2",
        "password_hash": "hash2"
    })
    
    # Create posts
    posts_data = [
        {"author_id": user1.id, "title": "Post 1", "content": "Content 1", "is_published": True},
        {"author_id": user1.id, "title": "Post 2", "content": "Content 2", "is_published": False},
        {"author_id": user2.id, "title": "Post 3", "content": "Content 3", "is_published": True},
    ]
    
    for post_data in posts_data:
        crud.create_post(db, post_data)
    
    # Get published posts only
    published_posts = crud.get_posts(db, is_published=True)
    assert len(published_posts) == 2
    
    # Get posts by user1
    user1_posts = crud.get_posts(db, author_id=user1.id)
    assert len(user1_posts) == 1  # Only published posts by default
    
    # Get all posts including unpublished
    all_posts = crud.get_posts(db, is_published=False)
    assert len(all_posts) == 3


def test_create_comment(db: Session):
    """
    Test creating a comment.
    """
    # Create user
    user = crud.create_user(db, {
        "email": "user@example.com",
        "login": "user",
        "password_hash": "hash"
    })
    
    # Create post
    post = crud.create_post(db, {
        "author_id": user.id,
        "title": "Test Post",
        "content": "Content",
        "is_published": True
    })
    
    # Create comment
    comment_data = {
        "post_id": post.id,
        "user_id": user.id,
        "content": "Great post!"
    }
    
    comment = crud.create_comment(db, comment_data)
    
    assert comment.content == "Great post!"
    assert comment.post_id == post.id
    assert comment.user_id == user.id


def test_add_favorite(db: Session):
    """
    Test adding a post to favorites.
    """
    # Create user
    user = crud.create_user(db, {
        "email": "user@example.com",
        "login": "user",
        "password_hash": "hash"
    })
    
    # Create post
    post = crud.create_post(db, {
        "author_id": user.id,
        "title": "Test Post",
        "content": "Content",
        "is_published": True
    })
    
    # Add to favorites
    result = crud.add_favorite(db, user.id, post.id)
    assert result == True
    
    # Try adding again (should return False)
    result = crud.add_favorite(db, user.id, post.id)
    assert result == False


def test_is_favorited(db: Session):
    """
    Test checking if a post is favorited.
    """
    # Create user
    user = crud.create_user(db, {
        "email": "user@example.com",
        "login": "user",
        "password_hash": "hash"
    })
    
    # Create post
    post = crud.create_post(db, {
        "author_id": user.id,
        "title": "Test Post",
        "content": "Content",
        "is_published": True
    })
    
    # Check before adding
    assert crud.is_favorited(db, user.id, post.id) == False
    # Add to favorites
    crud.add_favorite(db, user.id, post.id)
    # Check after adding
    assert crud.is_favorited(db, user.id, post.id) == True


def test_follow_user(db: Session):
    
    user1 = crud.create_user(db, {
        "email": "user1@example.com",
        "login": "user1",
        "password_hash": "hash1"
    })
    
    user2 = crud.create_user(db, {
        "email": "user2@example.com",
        "login": "user2",
        "password_hash": "hash2"
    })
    
    result = crud.follow_user(db, user1.id, user2.id)
    assert result == True

    result = crud.follow_user(db, user1.id, user2.id)
    assert result == False
    
    result = crud.follow_user(db, user1.id, user1.id)
    assert result == False


def test_is_following(db: Session):
    
    user1 = crud.create_user(db, {
        "email": "user1@example.com",
        "login": "user1",
        "password_hash": "hash1"
    })
    
    user2 = crud.create_user(db, {
        "email": "user2@example.com",
        "login": "user2",
        "password_hash": "hash2"
    })
    
    assert crud.is_following(db, user1.id, user2.id) == False
    
    crud.follow_user(db, user1.id, user2.id)
    
    assert crud.is_following(db, user1.id, user2.id) == True