from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List
from src.config.llm import llm_2_5_flash_preview


class GeneratedAnswer(BaseModel):
    answer: str = Field(description="Đáp án dựa trên câu hỏi bài tập")
    reasoning: str = Field(
        description="Lý do giải thích cho đáp án đã tạo. Ngắn gọn và súc tích."
    )


gen_answer_prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """<Role>
Role: Bạn là chuyên gia AI chuyên giải bài tập
<Role/>
<Instruction>
- Bạn tạo ra các câu trả lời cho bài tập dựa trên câu hỏi bài tập, tiêu chí trong phần <exercise_question/> .
- Câu hỏi bài tập có thể liên quan đến lập trình, toán học, khoa học, hoặc các lĩnh vực khác.
- Câu trả lời của bạn nên đầy đủ, chính xác và phù hợp với yêu cầu.
- Đưa ra đáp án và lý do giải thích rõ ràng về cách bạn đạt được câu trả lời đó.

<Instruction/>


<note>
- Nếu là ngôn ngữ lập trình, hãy đảm bảo rằng mã nguồn được viết đúng cú pháp và có thể chạy được.
- Nếu là bài tập tự luận thì hãy đảm bảo rằng câu trả lời có cấu trúc rõ ràng, logic và đầy đủ. Và resoning nên ngắn gọn, súc tích.
- Nếu bài tập là trắc nghiệm, hãy cung cấp câu trả lời đúng và giải thích ngắn gọn về lý do lựa chọn đó.

</note>
"""
            + "\n{format_instructions}",
        ),
        (
            "user",
            """Giải bài tập này cho tôi.
<exercise_question/>
{exercise_question}
<exercise_question/> """,
        ),
    ]
).partial(
    format_instructions=PydanticOutputParser(
        pydantic_object=GeneratedAnswer
    ).get_format_instructions()
)


chain_gen_answer = (
    gen_answer_prompt_template
    | llm_2_5_flash_preview.with_structured_output(GeneratedAnswer)
)
