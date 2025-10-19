from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from typing import Annotated, TypedDict, List
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field

gen_test_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """# Bạn là một chuyên gia tạo test cases để test API dựa trên tài liệu họ cung cấp.
## Vai trò:
    Tạo ra test cases description để test API.
## Đầu vào:
    Bảng mô tả 1 API của hệ thống:
        - API endpoint: {{api_endpoint}} (ví dụ: /api/v1/users, /api/v1/users/{{user_id}})
        - API method: {{method}} (GET, POST, PUT, DELETE)
        - Mục tiêu của API: {{api_description}} (ví dụ: Tạo mới user, Lấy thông tin user, Cập nhật thông tin user, Xóa user)
        - Mô tả các trường/kiểu dữ liệu và api validation bằng json hoặc ngôn ngữ tự nhiên: {{field_description}} (ví dụ: {{
            "name": "string" (required),
            "age": "number" (required) (min: 18, max: 100),
            "email": "string" (required) (email format),
            "phone": "string" (required) (phone format),
            "address": "string" (optional),
            "priority": High, Medium, Low (optional),
        }})
    
## Yêu cầu đầu ra (List of test cases description + expected output):
    - Test cases description để test API.
    - Expected output tương ứng với test cases.
        + Nếu các trường dữ liệu hoặc api validation không được đáp ứng thì trả về False tương ứng với failed.
        + Nếu các trường dữ liệu hoặc api validation được đáp ứng thì trả về True tương ứng với passed.
    - Số lượng test cases từ: 1-5 cho mỗi API. Dựa trên mục tiêu của API và độ phức tạp và priority.
    - Test cases sẽ cover:
        + Positive test cases
        + Negative test cases
        + Boundary test cases
    - Nội dung mô tả test cases rõ ràng, dễ hiểu, dễ implement theo format sau: {{method}} {{api_endpoint}} + {{payload/params}}
        Ví dụ: 
        - Test case 1:
            Test case description: POST /api/v1/users with body params {{payload}}
            Expected output: True
        - Test case 2:
            Test case description: PUT /api/v1/users/{{user_id}} with body params {{payload}}
                "name": "Bao",
                "age": -1,
                "email": "bao@gmail.com",
                "phone": "0909090909"
            }}
            Expected output: False
        """,
        ),
        ("user", "{api_description}"),
    ]
)


prompt_generate_code = PromptTemplate.from_template(
    """You are a Python code generator
### Instruction
Your task is to generate Python code for calling an API using the requests library of Python3.
You are given:
    BaseUrl: {base_url}
    API endpoint: {api_endpoint}
    API method: {method}
    Call API by method {test_case_description}

Requirements:
- Encode special characters in query parameters using `requests.utils.quote`.
- Ensure any boolean values use True or False (not lowercase).
- Use f-strings for path parameters (if any).

Output Format: 
- Provide only Python code for the API call.
- Use `requests.utils.quote` to encode special characters, including spaces.
- If params is empty
Example output:
`
import requests
from requests.utils import quote
query = quote("The Great Gatsby")
{ex_rq}
response = requests.get(url)
print("STATUS CODE", response.status_code)
print("response message", response.text)
`
"""
).partial(ex_rq='url=f"https://jsonplaceholder.typicode.com/books/search/{query}"')


evaluation_response_prompt = PromptTemplate.from_template(
    """You are expert in validation API response 
###Instruction
Your task is validate whether output meet expected

API Information:
    - API endpoint: {api_endpoint}
    - API Description: {api_description}
    - Field Description: {field_description}

Call API with params: {test_case_description}
Actual API Response: {response_output}
Expected API Response: {expected_api_response}

Output:
Actual API Response: Based on Actual API Response if 2xx status code is passed (True), 4xx is failed (False)
"""
)


class EvaluationOutput(BaseModel):
    actual_api_response: bool = Field(
        ..., description="Actual API response is failed or passed"
    )
    reason: str = Field(
        ..., description="concise description why return True or False of each field"
    )


class GenerateCode(BaseModel):
    code: str = Field(..., description="python code using request for api calling")


class TestCase(BaseModel):
    test_case_description: str = Field(..., description="Test case description")
    expected_output: bool = Field(..., description="Expected output")


class OutputTestCases(BaseModel):
    test_cases: list[TestCase] = Field(..., description="List of test cases")


def grade_code_logically_chain(llm: BaseChatModel):
    return {
        "gen_test_cases_chain": gen_test_prompt
        | llm.with_structured_output(OutputTestCases),
        "gen_code_chain": prompt_generate_code
        | llm.with_structured_output(GenerateCode),
        "evaluation_chain": evaluation_response_prompt
        | llm.with_structured_output(EvaluationOutput),
    }
