from .prompt import (
    SplitQuestionRequest,
    chain_extract_image_content,
    chain_split_question,
)

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from typing import List
import base64
import io
from io import BytesIO
from PIL import Image
import tempfile
import os
from datetime import datetime
from src.config.llm import llm_2_5_flash_preview
from langchain_core.prompts import ChatPromptTemplate


def combine_images_and_save(image_files: List[UploadFile]) -> str:
    """
    Ghép danh sách hình ảnh thành một ảnh duy nhất và lưu trên máy local

    Args:
        image_files: Danh sách các file hình ảnh

    Returns:
        str: Đường dẫn đến file ảnh đã ghép
    """
    try:
        # Đọc và xử lý các hình ảnh
        images = []
        for file in image_files:
            contents = file.file.read()
            img = Image.open(BytesIO(contents)).convert("RGB")
            images.append(img)
            # Reset file pointer
            file.file.seek(0)

        # Tính kích thước ảnh đầu ra (theo chiều dọc)
        widths = [img.width for img in images]
        heights = [img.height for img in images]

        max_width = max(widths)
        total_height = sum(heights)

        # Tạo ảnh trống ghép tất cả lại
        combined_img = Image.new("RGB", (max_width, total_height), (255, 255, 255))

        y_offset = 0
        for img in images:
            combined_img.paste(img, (0, y_offset))
            y_offset += img.height

        # Tạo tên file với timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"combined_images_{timestamp}.jpg"

        # Tạo thư mục lưu ảnh nếu chưa có
        save_directory = "saved_images"
        os.makedirs(save_directory, exist_ok=True)

        # Đường dẫn đầy đủ
        full_path = os.path.join(save_directory, filename)

        # Lưu ảnh đã ghép
        combined_img.save(full_path, "JPEG", quality=100)

        return full_path

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi ghép và lưu hình ảnh: {str(e)}"
        )


async def extract_text_from_images(image_files: List[UploadFile]) -> tuple[str, str]:
    """
    Trích xuất văn bản từ danh sách hình ảnh

    Args:
        image_files: Danh sách các file hình ảnh

    Returns:
        tuple: (Văn bản được trích xuất, Đường dẫn ảnh đã lưu)
    """
    try:
        # Ghép ảnh và lưu trên local
        saved_image_path = combine_images_and_save(image_files)

        # Đọc ảnh đã ghép và chuyển thành base64 để gửi cho LLM
        with open(saved_image_path, "rb") as img_file:
            img_data = img_file.read()
            img_base64 = base64.b64encode(img_data).decode("utf-8")

        # Gọi LLM để trích xuất văn bản (cập nhật prompt cho ảnh thay vì PDF)
        assignment_content = await chain_extract_image_content.ainvoke(
            {"image_data": img_base64}
        )

        questions: SplitQuestionRequest = await chain_split_question.ainvoke(
            {"assignment_content": assignment_content.content}
        )

        return (
            assignment_content.content,
            questions.question,
            saved_image_path,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi trích xuất văn bản: {str(e)}"
        )


async def split_question(assignment_content: str) -> List[str]:
    """
    Tách câu hỏi thành các phần nhỏ hơn theo định dạng đã cho

    Args:
        question: Câu hỏi cần tách

    Returns:
        List[str]: Danh sách các câu hỏi đã tách
    """
    try:
        result: SplitQuestionRequest = await chain_split_question.ainvoke(
            {"assignment_content": assignment_content}
        )
        return result.question
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi tách câu hỏi: {str(e)}")
