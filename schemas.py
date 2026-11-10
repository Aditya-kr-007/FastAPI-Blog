from pydantic import BaseModel, ConfigDict, Field

#Input Schema
class BlogCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=100000)

#Output Schema
class BlogResponse(BaseModel):
    id:int
    title:str
    content:str
    owner_id: int | None = None
    author: str = "The Margin"

    model_config = ConfigDict(from_attributes=True)

class BlogPage(BaseModel):
    page: int
    limit: int
    total: int
    data: list[BlogResponse]


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: int | None
    username: str
    is_admin: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
