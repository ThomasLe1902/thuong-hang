from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List
from langchain_core.language_models.chat_models import BaseChatModel
from src.config.llm import llm_2_5_flash_preview


class GradingCriteria(BaseModel):
    criteria_name: str = Field(description="Name of the grading criteria")
    score: float = Field(description="Score from each criteria")
    comment: str = Field(description="Reason for the score")


class GradingResult(BaseModel):
    criteria_scores: List[GradingCriteria] = Field(
        description="List of criteria scores"
    )
    total_score: float = Field(description="Total score from all criteria")
    total_comment: str = Field(description="Overall comment for the total score")


grade_prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """<Role>
Role: You are an AI assignment grader
<Role/>
<Instruction>
Function:
- You grade assignments based on exercise question and code file content.
- Return grading results based on user descriptions
Processing process:
- Understand General Scoring Rubric
- Read and analyze the assignment in the <exercise_question/> section
- Read and analyze student/submitter assignments
- Calculate scores for each criterion and describe the reasons for each score

<Instruction/>

<exercise_question/>
{exercise_question}
<exercise_question/>

<note>
- Max score based on the mentioned score in the <exercise_question/> section. If not mentioned, assume max score is 10.
- The total score is the sum of the scores of all criteria.
- Should evaluate correctly, should not give points too easily or too hard. It must be fair and based on the criteria/requirements in the <exercise_question/> section.
- The comment should be clearly explain and easy to understand.
- Comment for each criteria should be under 50 words.
- Comment in Vietnamese
</note>
"""
            + "\n{format_instructions}",
        ),
        ("user", "{user_input}"),
    ]
).partial(
    format_instructions=PydanticOutputParser(
        pydantic_object=GradingResult
    ).get_format_instructions()
)


chain_grade_assignment = (
    grade_prompt_template | llm_2_5_flash_preview.with_structured_output(GradingResult)
)
