from pydantic import BaseModel


class Comment(BaseModel):
    content: str
