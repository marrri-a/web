import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.config import settings
SQLALCHEMY_DATABASE_URL = settings.TEST_DATABASE_URL or "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="function")
def test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_register_success(test_db):
    """
    Test successful user registration.
    """
    response = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "login": "testuser",
        "password": "testpassword123",
        "full_name": "Test User"
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["login"] == "testuser"
    assert "password" not in data


def test_register_duplicate_email(test_db):
    """
    Test registration with duplicate email.
    """
    # First registration
    client.post("/api/auth/register", json={
        "email": "test@example.com",
        "login": "testuser1",
        "password": "testpassword123"
    })
    
    # Second registration with same email
    response = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "login": "testuser2",
        "password": "testpassword123"
    })
    
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_register_duplicate_login(test_db):
    """
    Test registration with duplicate login.
    """
    # First registration
    client.post("/api/auth/register", json={
        "email": "test1@example.com",
        "login": "testuser",
        "password": "testpassword123"
    })
    
    response = client.post("/api/auth/register", json={
        "email": "test2@example.com",
        "login": "testuser",
        "password": "testpassword123"
    })
    
    assert response.status_code == 400
    assert "already taken" in response.json()["detail"]


def test_login_success(test_db):
    """
    Test successful login.
    """
    # Register user
    client.post("/api/auth/register", json={
        "email": "test@example.com",
        "login": "testuser",
        "password": "testpassword123"
    })
    
    response = client.post("/api/auth/login", data={
        "username": "test@example.com",
        "password": "testpassword123"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(test_db):
    """
    Test login with wrong password.
    """
    # Register user
    client.post("/api/auth/register", json={
        "email": "test@example.com",
        "login": "testuser",
        "password": "testpassword123"
    })
    
    # Login with wrong password
    response = client.post("/api/auth/login", data={
        "username": "test@example.com",
        "password": "wrongpassword"
    })
    
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


def test_login_nonexistent_user(test_db):
    """
    Test login with non-existent user.
    """
    response = client.post("/api/auth/login", data={
        "username": "nonexistent@example.com",
        "password": "password123"
    })
    
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


def test_get_current_user(test_db):
    """
    Test getting current user information.
    """
    # Register and login
    client.post("/api/auth/register", json={
        "email": "test@example.com",
        "login": "testuser",
        "password": "testpassword123"
    })
    
    login_response = client.post("/api/auth/login", data={
        "username": "test@example.com",
        "password": "testpassword123"
    })
    
    token = login_response.json()["access_token"]
    
    # Get current user
    response = client.get("/api/auth/me", headers={
        "Authorization": f"Bearer {token}"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["login"] == "testuser"


def test_get_current_user_no_token(test_db):
    """
    Test getting current user without token.
    """
    response = client.get("/api/auth/me")
    
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


def test_update_current_user(test_db):
    
    client.post("/api/auth/register", json={
        "email": "test@example.com",
        "login": "testuser",
        "password": "testpassword123",
        "full_name": "Old Name"
    })
    
    login_response = client.post("/api/auth/login", data={
        "username": "test@example.com",
        "password": "testpassword123"
    })
    
    token = login_response.json()["access_token"]

    response = client.put("/api/auth/me", json={
        "full_name": "New Name",
        "bio": "Test bio"
    }, headers={
        "Authorization": f"Bearer {token}"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "New Name"
    assert data["bio"] == "Test bio"