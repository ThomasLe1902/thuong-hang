from langchain_core.tools import tool
from src.utils.logger import logger


def enough_information(name: str, info: str):
    """
    Call tool nếu đã thu thập đủ thông tin cần thiết. Hoặc là người dùng đã xác nhận thông tin đã thu thập.
    Nếu chưa đủ thông tin, sẽ không gọi tool này.
    Args:
        name (str): Tên chatbot cần tạo
        info (str): Thông tin đã thu thập về chatbot muốn tạo từ người dùng
    """
    logger.info(f"Created successful")
    return "Created successful"
