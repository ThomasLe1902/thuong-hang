from datetime import datetime
from src.config.mongo import UserCRUD
from src.utils.logger import logger
from bson import ObjectId
from fastapi.responses import JSONResponse
from fastapi import HTTPException, status
from src.apis.models.user_models import User
from src.apis.providers.jwt_provider import JWTProvider
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


async def list_users_controller():
    try:
        users = await UserCRUD.find_all()
        # Convert datetime fields to ISO format
        for user in users:
            if "created_at" in user and isinstance(user["created_at"], datetime):
                user["created_at"] = user["created_at"].isoformat()
            if "updated_at" in user and isinstance(user["updated_at"], datetime):
                user["updated_at"] = user["updated_at"].isoformat()
            if "expire_at" in user and isinstance(user["expire_at"], datetime):
                user["expire_at"] = user["expire_at"].isoformat()
        return JSONResponse(
            content={
                "status": "success",
                "data": users,
            },
            status_code=200,
        )
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        return JSONResponse(
            content={
                "status": "error",
                "message": str(e),
            },
            status_code=500,
        )


async def update_user_controller(user_id: str, user_data: dict):
    try:
        # Update trả về modified_count (số lượng documents được cập nhật)
        modified_count = await UserCRUD.update({"_id": ObjectId(user_id)}, user_data)
        
        if modified_count > 0:
            # Nếu cập nhật thành công, lấy thông tin user mới nhất
            updated_user = await UserCRUD.find_by_id(user_id)
            
            # Convert datetime fields to ISO format
            if updated_user:
                if "created_at" in updated_user and isinstance(updated_user["created_at"], datetime):
                    updated_user["created_at"] = updated_user["created_at"].isoformat()
                if "updated_at" in updated_user and isinstance(updated_user["updated_at"], datetime):
                    updated_user["updated_at"] = updated_user["updated_at"].isoformat()
                if "expire_at" in updated_user and isinstance(updated_user["expire_at"], datetime):
                    updated_user["expire_at"] = updated_user["expire_at"].isoformat()
            
            return JSONResponse(
                content={
                    "status": "success",
                    "data": updated_user,
                },
                status_code=200,
            )
        else:
            return JSONResponse(
                content={
                    "status": "error",
                    "message": "User not found or no changes made",
                },
                status_code=404,
            )
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return JSONResponse(
            content={
                "status": "error",
                "message": str(e),
            },
            status_code=500,
        )
    # except Exception as e:
    #     logger.error(f"Error updating user: {e}")
    #     return JSONResponse(
    #         content={
    #             "status": "error",
    #             "message": str(e),
    #         },
    #         status_code=500,
        # )


async def delete_user_controller(user_id: str):
    try:
        user = await UserCRUD.delete_one({"_id": ObjectId(user_id)})
        return JSONResponse(
            content={
                "status": "success",
                "data": user,
            },
            status_code=200,
        )
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return JSONResponse(
            content={
                "status": "error",
                "message": str(e),
            },
            status_code=500,
        )


async def get_user_by_id_controller(user_id: str):
    try:
        user = await UserCRUD.find_by_id(user_id)
        if not user:
            return JSONResponse(
                content={
                    "status": "error",
                    "message": "User not found",
                },
                status_code=404,
            )
        # Convert datetime fields to ISO format
        if "created_at" in user and isinstance(user["created_at"], datetime):
            user["created_at"] = user["created_at"].isoformat()
        if "updated_at" in user and isinstance(user["updated_at"], datetime):
            user["updated_at"] = user["updated_at"].isoformat()
        if "expire_at" in user and isinstance(user["expire_at"], datetime):
            user["expire_at"] = user["expire_at"].isoformat()
        return JSONResponse(
            content={
                "status": "success",
                "data": user,
            },
            status_code=200,
        )
    except Exception as e:
        logger.error(f"Error getting user by id: {e}")
        return JSONResponse(
            content={
                "status": "error",
                "message": str(e),
            },
            status_code=500,
        )
