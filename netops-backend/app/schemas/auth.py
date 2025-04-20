from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class UserBase(BaseModel):
    username: str
    email: str
    full_name: str | None = None
    is_active: bool = True
    is_superuser: bool = False

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    password: str | None = None

class User(UserBase):
    id: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True 