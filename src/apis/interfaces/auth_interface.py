from pydantic import BaseModel, Field


class Credential(BaseModel):
    credential: str = Field(..., example="F9P/3?@q2!vq")


class _LoginResponseInterface(BaseModel):
    token: str = Field(..., title="JWT Token")


class LoginResponseInterface(BaseModel):
    msg: str = Field(..., title="Message")
    data: _LoginResponseInterface = Field(..., title="User Data")


class AuthInterface(BaseModel):
    gtoken: str = Field(..., title="Google Access-Token")