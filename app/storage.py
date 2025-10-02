from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from .models import (
    UserCreate, UserUpdate, UserRead,
    PostCreate, PostUpdate, PostRead
)

DATA_FILE = Path("data.json")
def utcnow() -> datetime: return datetime.now(timezone.utc)

@dataclass
class Store:
    users: Dict[int, UserRead]
    posts: Dict[int, PostRead]
    _user_seq: int = 0
    _post_seq: int = 0

    # ----- USERS -----
    def create_user(self, data: UserCreate) -> UserRead:
        if any(u.email == data.email for u in self.users.values()): raise ValueError("email already in use")
        if any(u.login == data.login for u in self.users.values()): raise ValueError("login already in use")
        self._user_seq += 1
        user = UserRead(id=self._user_seq, email=data.email, login=data.login,
                        createdAt=utcnow(), updatedAt=utcnow())
        self.users[user.id] = user
        return user

    def get_user(self, user_id: int) -> Optional[UserRead]:
        return self.users.get(user_id)

    def list_users(self, offset=0, limit=100) -> list[UserRead]:
        vals = list(self.users.values())
        return vals[offset: offset + limit]

    def update_user(self, user_id: int, data: UserUpdate) -> UserRead:
        user = self.users.get(user_id)
        if not user: raise KeyError("user not found")
        if data.email is not None and any(u.email == data.email and u.id != user_id for u in self.users.values()):
            raise ValueError("email already in use")
        if data.login is not None and any(u.login == data.login and u.id != user_id for u in self.users.values()):
            raise ValueError("login already in use")
        new_user = user.model_copy(update={
            "email": data.email if data.email is not None else user.email,
            "login": data.login if data.login is not None else user.login,
            "updatedAt": utcnow(),
        })
        self.users[user_id] = new_user
        return new_user

    def delete_user(self, user_id: int) -> None:
        if user_id not in self.users: raise KeyError("user not found")
        # каскадно удалим посты автора, чтобы не было «сирот»
        self.posts = {pid: p for pid, p in self.posts.items() if p.authorId != user_id}
        del self.users[user_id]

    
    def create_post(self, data: PostCreate) -> PostRead:
        if data.authorId not in self.users: raise ValueError("authorId does not exist")
        self._post_seq += 1
        post = PostRead(id=self._post_seq, authorId=data.authorId, title=data.title,
                        content=data.content, createdAt=utcnow(), updatedAt=utcnow())
        self.posts[post.id] = post
        return post

    def get_post(self, post_id: int) -> Optional[PostRead]:
        return self.posts.get(post_id)

    def list_posts(self, offset=0, limit=100, authorId: int|None=None, q: str|None=None) -> list[PostRead]:
        vals = list(self.posts.values())
        if authorId is not None: vals = [p for p in vals if p.authorId == authorId]
        if q: 
            s = q.lower()
            vals = [p for p in vals if s in p.title.lower()]
        vals.sort(key=lambda p: p.createdAt, reverse=True)
        return vals[offset: offset + limit]

    def update_post(self, post_id: int, data: PostUpdate) -> PostRead:
        post = self.posts.get(post_id)
        if not post: raise KeyError("post not found")
        new_author = data.authorId if data.authorId is not None else post.authorId
        if new_author not in self.users: raise ValueError("authorId does not exist")
        new_post = post.model_copy(update={
            "authorId": new_author,
            "title": data.title if data.title is not None else post.title,
            "content": data.content if data.content is not None else post.content,
            "updatedAt": utcnow(),
        })
        self.posts[post_id] = new_post
        return new_post

    def delete_post(self, post_id: int) -> None:
        if post_id not in self.posts: raise KeyError("post not found")
        del self.posts[post_id]

    
    def save_to_json(self) -> None:
        import json
        payload = {
            "users": [u.model_dump(mode="json") for u in self.users.values()],
            "posts": [p.model_dump(mode="json") for p in self.posts.values()],
            "_user_seq": self._user_seq,
            "_post_seq": self._post_seq,
        }
        DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_from_json(self) -> None:
        import json
        if not DATA_FILE.exists(): return
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        self.users = {u["id"]: UserRead.model_validate(u) for u in payload.get("users", [])}
        self.posts = {p["id"]: PostRead.model_validate(p) for p in payload.get("posts", [])}
        self._user_seq = int(payload.get("_user_seq", len(self.users)))
        self._post_seq = int(payload.get("_post_seq", len(self.posts)))

store = Store(users={}, posts={})
