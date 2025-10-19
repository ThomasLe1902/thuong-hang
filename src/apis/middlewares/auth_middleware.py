from typing import Annotated
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import JSONResponse
from src.apis.providers.jwt_provider import jwt_provider as jwt
from src.apis.models.user_models import get_user
from src.config.mongo import UserCRUD
from bson import ObjectId
from jose import JWTError
from src.utils.logger import logger

security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
):

    try:
        token = credentials.credentials
        if not token:
            return JSONResponse(
                content={"msg": "Authentication failed"}, status_code=401
            )
        payload = jwt.decrypt(token)
        user_id: str = payload["id"]
        if not user_id:
            return JSONResponse(
                content={"msg": "Authentication failed"}, status_code=401
            )
        user = await UserCRUD.read_one({"_id": ObjectId(user_id)})
        # print(user)
        user_email = user.get("email", None)
        # logger.info(f"Request of user: {user_email}")
        if not user:
            return JSONResponse(
                content={"msg": "Authentication failed"}, status_code=401
            )
        return get_user(user)
    except JWTError:
        return JSONResponse(content={"msg": "Authentication failed"}, status_code=401)
