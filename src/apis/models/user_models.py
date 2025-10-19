from pydantic import Field, EmailStr
from .BaseDocument import BaseDocument
from bson import ObjectId


def get_user(user) -> dict:
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "picture": user["picture"],
        "contact_number": user["contact_number"],
        "role": user["role"],
        "major": user.get("major", None),
    }


def list_serial(users) -> list:
    return [get_user(user) for user in users]


class User(BaseDocument):
    id: str = Field("", description="User's id")
    name: str = Field("", description="User's name")
    email: EmailStr = Field("", description="User's email")
    picture: str = Field("", title="User Picture")
    contact_number: str = Field("", description="User's contact number")
    role: str = Field("", description="User's role")
    major: str = Field("", description="User's major", title="User Major")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "johnUS192@gmail.com",
                "picture": "https://example.com/picture.jpg",
                "contact_number": "1234567890",
                "role": "user",
                "major": "SE",
            }
        }
