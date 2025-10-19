from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from src.apis.routers.rag_agent_template import router as router_rag_agent_template
from src.apis.routers.file_processing_router import router as router_file_processing
from src.apis.routers.custom_chatbot_router import router as custom_chatbot_processing
from src.apis.routers.vector_store_router import router as vector_store_router

# from src.apis.routers.tts_router import router as tts_router
from src.apis.routers.auth_router import router as auth_router
from src.apis.routers.grade_code_router import router as grade_code_router
from src.apis.routers.graded_assignment_router import router as graded_assignment_router
from src.apis.routers.api_testing_router import router as api_testing_router
from src.apis.routers.image_generation import router as image_generation_router
# from src.apis.routers.code_grader import router as code_grader_router
from src.apis.routers.prompt_optimization_router import router as prompt_optimization_router
# Monitoring imports
from src.config.monitoring import setup_monitoring
from src.apis.middlewares.monitoring_middleware import MonitoringMiddleware

api_router = APIRouter()
api_router.include_router(router_rag_agent_template)
api_router.include_router(router_file_processing)
api_router.include_router(custom_chatbot_processing)
api_router.include_router(vector_store_router)
# api_router.include_router(tts_router)
api_router.include_router(auth_router)
api_router.include_router(grade_code_router)
api_router.include_router(graded_assignment_router)
api_router.include_router(api_testing_router)
# api_router.include_router(code_grader_router)
api_router.include_router(image_generation_router)
api_router.include_router(prompt_optimization_router)

def create_app():
    app = FastAPI(
        docs_url="/docs",
        title="AI Service ABAOXOMTIEU",
    )

    @app.get("/")
    def root():
        return {
            "message": "Backend is running",
            "api": "https://ai.ftes.vn/api",
            "frontend": "https://ai.ftes.vn",
            "local_api": "http://localhost:7860",
        }

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add monitoring middleware
    app.add_middleware(MonitoringMiddleware)

    # Setup monitoring (Prometheus + OpenTelemetry)
    monitoring_config = setup_monitoring(app)

    return app
