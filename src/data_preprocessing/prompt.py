from langchain_core.prompts import ChatPromptTemplate
from src.config.llm import llm_2_0 as llm

image_caption_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "Bạn là một chuyên gia mô tả hình ảnh, có khả năng quan sát chi tiết và truyền đạt lại bằng tiếng Việt "
                "một cách rõ ràng, sinh động và chính xác. Khi người dùng gửi hình ảnh, bạn cần mô tả toàn cảnh nội dung "
                "bức ảnh, các yếu tố chính như phong cảnh, con người, vật thể, màu sắc, không khí, và cảm xúc mà bức ảnh gợi ra. "
                "Tránh nhận xét chủ quan nếu không có dữ kiện rõ ràng."
            ),
        ),
        ("placeholder", "{messages_history}"),
        ("placeholder", "{messages}"),
    ]
)


if __name__ == "__main__":
    chain = image_caption_prompt | llm
    response = chain.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Mô tả hình ảnh này để trích xuất captioning",
                        },
                        {
                            "type": "image",
                            "source_type": "url",
                            "url": "https://ik.imagekit.io/tvlk/blog/2024/02/ky-co-cover.jpg",
                        },
                    ],
                },
            ]
        }
    )
    print(response.text())
