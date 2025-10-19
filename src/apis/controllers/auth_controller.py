from fastapi import HTTPException, status
from src.apis.models.user_models import User
from src.config.mongo import UserCRUD
from src.apis.providers.jwt_provider import JWTProvider
from src.utils.logger import logger
import jwt

jwt_provider = JWTProvider()


async def login_control(token):
    first_login = False
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization Token is required",
        )
    decoded_token = jwt.decode(token, options={"verify_signature": False})
    decoded_data = {
        "name": decoded_token["name"],
        "email": decoded_token["email"],
        "picture": decoded_token["picture"],
        "role": "user",
    }
    user = User(**decoded_data)
    logger.info(f"User {user.email} is logging in.")
    existing_user = await UserCRUD.read_one({"email": user.email})
    if not existing_user:
        user_data = user.model_dump()
        if "id" in user_data:
            user_data.pop("id")
        user_id = await UserCRUD.create(user_data)
        first_login = True
        logger.info(f"User {user.email} created.")
    else:
        user_id = existing_user["_id"]

    logger.info(f"User {user.email} logged in.")
    token = jwt_provider.encrypt({"id": str(user_id)})
    user_data = user.__dict__
    user_data["id"] = user_id
    user_data["role"] = existing_user["role"] if existing_user else "user"
    user_data.pop("created_at", None)
    user_data.pop("updated_at", None)
    user_data.pop("expire_at", None)
    return token, user_data, first_login
