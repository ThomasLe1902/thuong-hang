from pydantic import Field
from .BaseDocument import BaseDocument
from bson import ObjectId


class Bot(BaseDocument):
    id: ObjectId = Field("", description="ID of the bot")
    user_id: str = Field("", description="User ID of the bot")
    name: str = Field(default="", description="Name of the bot")
    prompt: str = Field(default="", description="Prompt of the bot")
    tools: list = Field(default=[], description="Tools of the bot")
    public: bool = Field(default=False, description="Public of the bot")
