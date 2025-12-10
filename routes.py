from typing import List, Optional
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .database import get_db
from .auth import (
    get_current_user, get_current_active_user, get_current_admin_user,
    create_access_token, verify_password, get_password_hash
)
from .dependencies import (
    get_pagination_params, get_post_or_404, verify_post_owner,
    get_comment_or_404, verify_comment_owner, get_category_or_404
)
from .config import settings
from .models import User, Token

router = APIRouter()
@router.post("/auth/register", response_model=models.UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: models.UserCreate,
    db: Session = Depends(get_db)
):
    
    if crud.get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    if crud.get_user_by_login(db, user_data.login):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Login already taken"
        )
    

    try:
        user_dict = user_data.model_dump()
        user = crud.create_user(db, user_dict)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    return user


@router.post("/auth/login", response_model=models.Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login and get access token.
    """

    user = crud.get_user_by_email(db, form_data.username)
    if not user:
        user = crud.get_user_by_login(db, form_data.username)
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "is_admin": user.is_admin},
        expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, token_type="bearer")


@router.get("/auth/me", response_model=models.UserRead)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):

    return current_user


@router.put("/auth/me", response_model=models.UserRead)
async def update_current_user(
    user_data: models.UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update current user information.
    """
    update_data = user_data.model_dump(exclude_unset=True)
    

    if "email" in update_data and update_data["email"] != current_user.email:
        if crud.get_user_by_email(db, update_data["email"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    

    if "login" in update_data and update_data["login"] != current_user.login:
        if crud.get_user_by_login(db, update_data["login"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Login already taken"
            )
    
    user = crud.update_user(db, current_user.id, update_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user

@router.get("/users", response_model=List[models.UserRead])
async def list_users(
    search: Optional[str] = None,
    pagination: dict = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
 
    users = crud.get_users(
        db,
        skip=pagination["skip"],
        limit=pagination["limit"],
        search=search
    )
    return users


@router.get("/users/{user_id}", response_model=models.UserWithStats)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):

    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    posts_count = len(user.posts)
    followers_count = len(user.followers)
    following_count = len(user.following)
    
    return models.UserWithStats(
        **user.__dict__,
        posts_count=posts_count,
        followers_count=followers_count,
        following_count=following_count
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Delete a user (admin only).
    """
    if not crud.delete_user(db, user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

@router.get("/posts", response_model=List[models.PostWithStats])
async def list_posts(
    author_id: Optional[int] = None,
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    order_by: str = Query("created_at", regex="^(created_at|updated_at|view_count|title)$"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    pagination: dict = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):

    posts = crud.get_posts(
        db,
        skip=pagination["skip"],
        limit=pagination["limit"],
        author_id=author_id,
        category_id=category_id,
        is_published=True if not current_user or not current_user.is_admin else None,
        search=search,
        order_by=order_by,
        order=order
    )
    
    # Add statistics
    result = []
    for post in posts:
        likes_count = len(post.liked_by)
        comments_count = len(post.comments)
        result.append(
            models.PostWithStats(
                **post.__dict__,
                likes_count=likes_count,
                comments_count=comments_count
            )
        )
    
    return result


@router.get("/posts/{post_id}", response_model=models.PostWithStats)
async def get_post(
    post_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):

    post = get_post_or_404(post_id, db)

    if not post.is_published and (not current_user or 
                                  (post.author_id != current_user.id and not current_user.is_admin)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    background_tasks.add_task(crud.increment_post_views, db, post_id)

    likes_count = len(post.liked_by)
    comments_count = len(post.comments)
    
    return models.PostWithStats(
        **post.__dict__,
        likes_count=likes_count,
        comments_count=comments_count
    )


@router.post("/posts", response_model=models.PostRead, status_code=status.HTTP_201_CREATED)
async def create_post(
    post_data: models.PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new post.
    """
    post_dict = post_data.model_dump()
    post_dict["author_id"] = current_user.id
    
    try:
        post = crud.create_post(db, post_dict)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    return post


@router.put("/posts/{post_id}", response_model=models.PostRead)
async def update_post(
    post_id: int,
    post_data: models.PostUpdate,
    db: Session = Depends(get_db),
    post: Post = Depends(verify_post_owner)
):

    update_data = post_data.model_dump(exclude_unset=True)
    
    try:
        post = crud.update_post(db, post_id, update_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    return post


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    post: Post = Depends(verify_post_owner)
):
 
    if not crud.delete_post(db, post_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )


# Category routes
@router.get("/categories", response_model=List[models.CategoryRead])
async def list_categories(
    search: Optional[str] = None,
    pagination: dict = Depends(get_pagination_params),
    db: Session = Depends(get_db)
):
    """
    List categories.
    """
    categories = crud.get_categories(
        db,
        skip=pagination["skip"],
        limit=pagination["limit"],
        search=search
    )
    return categories


@router.get("/categories/{category_id}", response_model=models.CategoryRead)
async def get_category(
    category: models.Category = Depends(get_category_or_404)
):
    """
    Get category by ID.
    """
    return category


@router.post("/categories", response_model=models.CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: models.CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):

    try:
        category = crud.create_category(db, category_data.model_dump())
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    return category


@router.put("/categories/{category_id}", response_model=models.CategoryRead)
async def update_category(
    category_id: int,
    category_data: models.CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):

    update_data = category_data.model_dump(exclude_unset=True)
    category = crud.update_category(db, category_id, update_data)
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    return category


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):

    if not crud.delete_category(db, category_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

@router.get("/posts/{post_id}/comments", response_model=List[models.CommentRead])
async def list_post_comments(
    post_id: int,
    pagination: dict = Depends(get_pagination_params),
    db: Session = Depends(get_db)
):

    comments = crud.get_comments(
        db,
        post_id=post_id,
        skip=pagination["skip"],
        limit=pagination["limit"]
    )
    return comments


@router.post("/posts/{post_id}/comments", response_model=models.CommentRead, status_code=status.HTTP_201_CREATED)
async def create_comment(
    post_id: int,
    comment_data: models.CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):

    post = get_post_or_404(post_id, db)
    if not post.is_published:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot comment on unpublished post"
        )
    
    comment_dict = comment_data.model_dump()
    comment_dict["post_id"] = post_id
    comment_dict["user_id"] = current_user.id
    
    comment = crud.create_comment(db, comment_dict)
    return comment


@router.put("/comments/{comment_id}", response_model=models.CommentRead)
async def update_comment(
    comment_id: int,
    comment_data: models.CommentUpdate,
    db: Session = Depends(get_db),
    comment: Comment = Depends(verify_comment_owner)
):

    comment = crud.update_comment(db, comment_id, comment_data.model_dump())
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    return comment


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    comment: Comment = Depends(verify_comment_owner)
):

    if not crud.delete_comment(db, comment_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )



@router.post("/posts/{post_id}/favorite", status_code=status.HTTP_201_CREATED)
async def add_to_favorites(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):

    post = get_post_or_404(post_id, db)
    if not post.is_published:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot favorite unpublished post"
        )
    
    if not crud.add_favorite(db, current_user.id, post_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Post already in favorites"
        )
    
    return {"detail": "Post added to favorites"}


@router.delete("/posts/{post_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_favorites(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):

    if not crud.remove_favorite(db, current_user.id, post_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found in favorites"
        )


@router.get("/me/favorites", response_model=List[models.PostRead])
async def get_my_favorites(
    pagination: dict = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):

    posts = crud.get_user_favorites(
        db,
        user_id=current_user.id,
        skip=pagination["skip"],
        limit=pagination["limit"]
    )
    return posts


@router.get("/posts/{post_id}/favorite/status")
async def get_favorite_status(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    is_favorited = crud.is_favorited(db, current_user.id, post_id)
    return {"is_favorited": is_favorited}


@router.post("/users/{user_id}/follow", status_code=status.HTTP_201_CREATED)
async def follow_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Follow a user.
    """
    # Check if user exists
    user_to_follow = crud.get_user(db, user_id)
    if not user_to_follow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot follow yourself"
        )
    
    if not crud.follow_user(db, current_user.id, user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already following this user"
        )
    
    return {"detail": "User followed successfully"}


@router.delete("/users/{user_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):

    if not crud.unfollow_user(db, current_user.id, user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not following this user"
        )


@router.get("/users/{user_id}/following", response_model=List[models.UserRead])
async def get_user_following(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):

    following = crud.get_following(db, user_id)
    return following


@router.get("/users/{user_id}/followers", response_model=List[models.UserRead])
async def get_user_followers(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):

    followers = crud.get_followers(db, user_id)
    return followers


@router.get("/me/feed", response_model=List[models.PostWithStats])
async def get_feed(
    pagination: dict = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    following = crud.get_following(db, current_user.id)
    following_ids = [user.id for user in following]
    
    if not following_ids:
        return []

    posts = crud.get_posts(
        db,
        skip=pagination["skip"],
        limit=pagination["limit"],
        author_id=None,  
        is_published=True
    )
    
    feed_posts = [post for post in posts if post.author_id in following_ids]
    
    result = []
    for post in feed_posts:
        likes_count = len(post.liked_by)
        comments_count = len(post.comments)
        result.append(
            models.PostWithStats(
                **post.__dict__,
                likes_count=likes_count,
                comments_count=comments_count
            )
        )
    
    return result

@router.get("/admin/stats")
async def get_admin_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get admin statistics.
    """
    from sqlalchemy import func
    
    total_users = db.query(func.count(User.id)).scalar()
    
    total_posts = db.query(func.count(models.Post.id)).scalar()
    
    total_comments = db.query(func.count(models.Comment.id)).scalar()
    
    from datetime import datetime, timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_users = db.query(func.count(User.id)).filter(
        User.created_at >= week_ago
    ).scalar()
    
    return {
        "total_users": total_users,
        "total_posts": total_posts,
        "total_comments": total_comments,
        "recent_users": recent_users,
        "posts_per_day": total_posts / 30 if total_posts else 0,
        "comments_per_post": total_comments / total_posts if total_posts else 0
    }


@router.get("/admin/users/{user_id}/posts")
async def get_user_posts_admin(
    user_id: int,
    include_unpublished: bool = False,
    pagination: dict = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    posts = crud.get_posts(
        db,
        skip=pagination["skip"],
        limit=pagination["limit"],
        author_id=user_id,
        is_published=None if include_unpublished else True
    )
    
    result = []
    for post in posts:
        likes_count = len(post.liked_by)
        comments_count = len(post.comments)
        result.append(
            models.PostWithStats(
                **post.__dict__,
                likes_count=likes_count,
                comments_count=comments_count
            )
        )
    
    return result

@router.get("/search/posts")
async def search_posts(
    q: str = Query(..., min_length=1, description="Search query"),
    pagination: dict = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):

    posts = crud.get_posts(
        db,
        skip=pagination["skip"],
        limit=pagination["limit"],
        is_published=True if not current_user or not current_user.is_admin else None,
        search=q
    )
    
    result = []
    for post in posts:
        likes_count = len(post.liked_by)
        comments_count = len(post.comments)
        result.append(
            models.PostWithStats(
                **post.__dict__,
                likes_count=likes_count,
                comments_count=comments_count
            )
        )
    
    return result


@router.get("/search/users")
async def search_users(
    q: str = Query(..., min_length=1, description="Search query"),
    pagination: dict = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):

    users = crud.get_users(
        db,
        skip=pagination["skip"],
        limit=pagination["limit"],
        search=q
    )
    return users