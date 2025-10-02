from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, constr

LoginStr = constr(min_length=3, max_length=32)
PasswordStr = constr(min_length=6, max_length=64)
TitleStr = constr(min_length=1, max_length=120)

def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class UserBase(BaseModel):
    email: EmailStr
    login: LoginStr

class UserCreate(UserBase):
    password: PasswordStr  

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    login: Optional[LoginStr] = None
    password: Optional[PasswordStr] = None

class UserRead(UserBase):
    id: int
    createdAt: datetime = Field(default_factory=now_utc)
    updatedAt: datetime = Field(default_factory=now_utc)


class PostBase(BaseModel):
    authorId: int
    title: TitleStr
    content: constr(min_length=1)

class PostCreate(PostBase):
    pass

class PostUpdate(BaseModel):
    authorId: Optional[int] = None
    title: Optional[TitleStr] = None
    content: Optional[constr(min_length=1)] = None

class PostRead(PostBase):
    id: int
    createdAt: datetime = Field(default_factory=now_utc)
    updatedAt: datetime = Field(default_factory=now_utc)
