from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from src.config.llm import llm_2_5_flash_preview


class SplitQuestionRequest(BaseModel):
    question: list[str] = Field(
        ...,
        description="Câu hỏi cần chia nhỏ thành các phần. mỗi câu hỏi là một item trong list.",
    )


extract_image_content_system_prompt = ChatPromptTemplate(
    [
        {
            "role": "system",
            "content": """## Vai trò:
- Bạn là một chuyên gia trích xuất nội dung, văn bản từ hình ảnh được cung cấp.
- Bạn có thể trả ra nội dung văn bản từ hình ảnh với format gốc của nó, bao gồm các ký tự đặc biệt, dấu câu, v.v. dưới dạng markdown.
- Bạn được cung cấp hình ảnh đã được ghép từ các screenshot liên quan đến một assignment/exercise/bài luận.

## Nhiệm vụ:
- Trích xuất nội dung văn bản từ hình ảnh và trả về dưới dạng markdown.
- Trả về nội dung văn bản đã trích xuất một cách chính xác và đầy đủ. Bỏ qua các phần logo, watermark, hoặc các phần không liên quan đến nội dung chính của hình ảnh.
- Không được trả ra thông tin không nằm trong hình ảnh, không được thêm bất kỳ thông tin nào ngoài nội dung văn bản đã trích xuất.
- text trả về dạng markdown nhưng không kèm ký từ ```markdown ``` ở đầu và cuối. Hãy trả về văn bản bình thường kèm các ký hiệu markdown như *bold*, _italic_, `code`, v.v. nếu có trong văn bản gốc.
""",
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Trích xuất văn bản từ hình ảnh đính kèm đã được ghép từ các screenshot liên quan đến bài tập.",
                },
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/jpeg;base64,{image_data}"},
                },
            ],
        },
    ]
)


split_question_prompt = ChatPromptTemplate(
    [
        (
            "system",
            """
## Vai trò:
- Bạn là chuyên gia trong viên tách câu hỏi của một assignment/exercise thành các phần nhỏ hơn theo thứ tự.
- Bạn sẽ nhận một đề bài chứa nhiều câu hỏi, nội dung và chia nó thành các item và cho vào một danh sách.
     

## Nhiệm vụ:
- Chia câu hỏi thành các phần nhỏ hơn để dễ hiểu hơn.
- Giữ nguyên format của câu hỏi, bao gồm các ký tự đặc biệt, dấu câu, v.v.
- Chỉ tách nếu nó là các câu hỏi riêng lẻ, không tách nếu nội dung câu hỏi nằm chung trong một câu hỏi lớn hơn.
- Breakpoint để tách câu hỏi là: 'Question 1:', 'Question 2:', 'Q1:', 'Q2:', 'Câu hỏi 1:',...
""",
        ),
        (
            "user",
            "Hãy chia câu hỏi sau thành các phần nhỏ hơn thành các phần tử của một danh sách: {assignment_content}",
        ),
    ]
)
chain_extract_image_content = (
    extract_image_content_system_prompt | llm_2_5_flash_preview
)
chain_split_question = (
    split_question_prompt
    | llm_2_5_flash_preview.with_structured_output(SplitQuestionRequest)
)
