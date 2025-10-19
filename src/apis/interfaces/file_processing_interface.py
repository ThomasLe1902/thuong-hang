from pydantic import BaseModel, Field


class FileProcessingBody(BaseModel):
    bot_id: str = Field(..., title="Bot ID associated with the file")
    model_config = {
        "json_schema_extra": {
            "example": {
                "bot_id": "bot123"
            }
        }
    }


class FileAnalysisResponse(BaseModel):
    bot_id: str = Field(..., title="Bot ID associated with the file")
    file_path: str = Field(..., title="Path to the processed file")
    word_count: int = Field(..., title="Number of words in the file")
    image_count: int = Field(..., title="Number of images in the file")
    file_type: str = Field(..., title="Type of the file (PDF, DOCX, etc.)")


class FileIngressResponse(BaseModel):
    bot_id: str = Field(..., title="Bot ID associated with the file")
    file_path: str = Field(..., title="Path to the processed file")
    chunks_count: int = Field(..., title="Number of chunks created")
    success: bool = Field(..., title="Whether the ingestion was successful")
    message: str = Field("File processed and indexed successfully", title="Status message")
