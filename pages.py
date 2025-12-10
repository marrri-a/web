from fastapi import APIRouter, Form, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette import status

from .storage import store
from .models import PostCreate, PostUpdate

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/")
async def home(request: Request):
    posts = store.list_posts(limit=100)
    users = {u.id: u for u in store.list_users()}
    return templates.TemplateResponse("index.html", {"request": request, "posts": posts, "users": users})

@router.get("/posts/{post_id}/view")
async def view_post(request: Request, post_id: int):
    post = store.get_post(post_id)
    if not post:
        raise HTTPException(404, "post not found")
    author = store.get_user(post.authorId)
    return templates.TemplateResponse("post_view.html", {"request": request, "post": post, "author": author})

@router.get("/posts/create")
async def create_form(request: Request):
    users = store.list_users()
    return templates.TemplateResponse("post_form.html", {"request": request, "users": users, "mode": "create"})

@router.post("/posts/create")
async def create_submit(
    authorId: int = Form(...),
    title: str = Form(...),
    content: str = Form(...)
):
    post = store.create_post(PostCreate(authorId=authorId, title=title, content=content))
    return RedirectResponse(url=f"/posts/{post.id}/view", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/posts/{post_id}/edit")
async def edit_form(request: Request, post_id: int):
    post = store.get_post(post_id)
    if not post:
        raise HTTPException(404, "post not found")
    users = store.list_users()
    return templates.TemplateResponse("post_form.html", {"request": request, "users": users, "post": post, "mode": "edit"})

@router.post("/posts/{post_id}/edit")
async def edit_submit(post_id: int,
    authorId: int = Form(...),
    title: str = Form(...),
    content: str = Form(...)
):
    store.update_post(post_id, PostUpdate(authorId=authorId, title=title, content=content))
    return RedirectResponse(url=f"/posts/{post_id}/view", status_code=status.HTTP_303_SEE_OTHER)
