from dotenv import load_dotenv

load_dotenv(override=True)

from src.apis.create_app import create_app, api_router
import uvicorn


app = create_app()

app.include_router(api_router)
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=7860, reload=True)
