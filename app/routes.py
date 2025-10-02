from fastapi import APIRouter, HTTPException, Query, status
from .models import (
    UserCreate, UserUpdate, UserRead,
    PostCreate, PostUpdate, PostRead
)
from .storage import store

router = APIRouter()

@router.get("/ping")
def ping():
    return {"status": "ok"}


users = APIRouter(prefix="/users", tags=["users"])

@users.get("", response_model=list[UserRead])
async def list_users(offset: int = 0, limit: int = Query(100, le=1000)):
    return store.list_users(offset=offset, limit=limit)

@users.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: int):
    u = store.get_user(user_id)
    if not u:
        raise HTTPException(404, "user not found")
    return u

@users.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate):
    try:
        return store.create_user(data)
    except ValueError as e:
        raise HTTPException(409, str(e))

@users.put("/{user_id}", response_model=UserRead)
async def put_user(user_id: int, data: UserUpdate):
    try:
        return store.update_user(user_id, data)
    except KeyError:
        raise HTTPException(404, "user not found")
    except ValueError as e:
        raise HTTPException(409, str(e))

@users.patch("/{user_id}", response_model=UserRead)
async def patch_user(user_id: int, data: UserUpdate):
    return await put_user(user_id, data)

@users.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int):
    try:
        store.delete_user(user_id)
    except KeyError:
        raise HTTPException(404, "user not found")


posts = APIRouter(prefix="/posts", tags=["posts"])

@posts.get("", response_model=list[PostRead])
async def list_posts(offset: int = 0, limit: int = Query(100, le=1000),
                     authorId: int | None = None, q: str | None = None):
    return store.list_posts(offset=offset, limit=limit, authorId=authorId, q=q)

@posts.get("/{post_id}", response_model=PostRead)
async def get_post(post_id: int):
    p = store.get_post(post_id)
    if not p:
        raise HTTPException(404, "post not found")
    return p

@posts.post("", response_model=PostRead, status_code=status.HTTP_201_CREATED)
async def create_post(data: PostCreate):
    try:
        return store.create_post(data)
    except ValueError as e:
        raise HTTPException(400, str(e))

@posts.put("/{post_id}", response_model=PostRead)
async def put_post(post_id: int, data: PostUpdate):
    try:
        return store.update_post(post_id, data)
    except KeyError:
        raise HTTPException(404, "post not found")
    except ValueError as e:
        raise HTTPException(400, str(e))

@posts.patch("/{post_id}", response_model=PostRead)
async def patch_post(post_id: int, data: PostUpdate):
    return await put_post(post_id, data)

@posts.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int):
    try:
        store.delete_post(post_id)
    except KeyError:
        raise HTTPException(404, "post not found")


router.include_router(users)
router.include_router(posts)
