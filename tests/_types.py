from pydantic import BaseModel


class RequestContext(BaseModel):
    user_id: str
