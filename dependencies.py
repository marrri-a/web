from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from .database import get_db
from .auth import get_current_user, get_current_admin_user
from . import crud
from .models import User

def get_pagination_params(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page")
) -> dict:

    return {
        "skip": (page - 1) * page_size,
        "limit": page_size
    }

def get_post_or_404(
    post_id: int,
    db: Session = Depends(get_db)
):

    post = crud.get_post(db, post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    return post


def verify_post_owner(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    post = get_post_or_404(post_id, db)
    if post.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return post


def get_comment_or_404(
    comment_id: int,
    db: Session = Depends(get_db)
):

    comment = crud.get_comment(db, comment_id)
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    return comment


def verify_comment_owner(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify that current user is the comment owner.
    """
    comment = get_comment_or_404(comment_id, db)
    if comment.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return comment

def get_category_or_404(
    category_id: int,
    db: Session = Depends(get_db)
):
    """
    Get category by ID or raise 404.
    """
    category = crud.get_category(db, category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    return category