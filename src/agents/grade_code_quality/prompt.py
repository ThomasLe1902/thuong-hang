from langchain_core.prompts import PromptTemplate
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable


organized_project_structure_grade_prompt = PromptTemplate.from_template(
    """
Analyze the project's folder structure and organization

File Tree:
{file_tree}

Criteria to Evaluate:
{criteria}

Please provide:
1. Analysis: Detailed review of folder structure (in Markdown)
2. Suggestions: Specific improvements if needed
3. Rating (1-5):
   1 = Poor (Disorganized, no clear structure)
   2 = Below Average (Basic structure but inconsistent)
   3 = Average (Standard structure with some organization)
   4 = Good (Well-organized with clear separation)
   5 = Excellent (Optimal structure following best practices)

Note: 
- Consider the project size when evaluating - smaller projects may not need all folders but should still maintain clear organization.
- Return Vietnamese text for the analysis and suggestions.

"""
)


project_description_generator_prompt = PromptTemplate.from_template(
    """
Generate a concise project description by analyzing this file tree.

File Tree: {file_tree}

Instructions:
1. Identify project type (Frontend/Backend/AI/Full-stack)
2. Specify frameworks and technologies
3. Determine project architecture
4. Note distinctive patterns

Output: 3-5 sentence description of project nature, tech stack, and purpose
Return in Vietnamese text.
"""
)

# Code Relevance Assessment
check_relevant_criteria_prompt = PromptTemplate.from_template(
    """
Assess code relevance to criteria scope

Inputs:

- Criteria: {criterias}

- Code: 
```
{code}
```

Determine if this code can be meaningfully evaluated using the given criteria:
- Return True if the criteria can reasonably evaluate the code, even if some parts of the code fall outside the criteria's scope.
- Return True if at least 40% of the code content is relevant to what the criteria is designed to assess.
- Only return False if the criteria is fundamentally mismatched with the code (e.g., CSS styling criteria being applied to pure Python logic with no styling elements, or database query criteria applied to a frontend component with no data access).
- Return Vietnamese text.

"""
)

# Code Review Prompts
analyze_code_files_prompt = PromptTemplate.from_template(
    """
Analyze code against specific criteria

File: {file_name}
Criteria: 
{criterias}
Code: 
{code}

Review Format:
1. Comments: (Return in Markdown text)
   - line X: [code] #[issue, suggestion] 
   - line Y: [code] #[issue, suggestion]
    Note: Always give briefly suggest improvements to increase rating score (in case score < 5). Exclude lines that have no issues.
        

2. Criteria Analysis: Concise assessment with examples (Return in Markdown text)

3. Rating (1-5):
   - 1: Poor
   - 2: Below Average
   - 3: Average
   - 4: Good
   - 5: Excellent

                                           
##Code:
```
{code}
```


Note: return Vietnamese text for comments, criteria analysis, and rating.                                       
"""
)

# Grading Prompts
grade_code_across_review_prompt = PromptTemplate.from_template(
    """
# Code Quality Assessment
Grade each criterion on a 1-5 scale based on the comprehensive review comments across all files.

#Criteria: 
{criterias}

Review Summary: {review_summary}

Format: Return in Markdown format
Criterion X: **[Title]**
- Summary: [Concise assessment based on cross-file patterns]
- Grade: **[1-5]**

Note: Evaluate each criterion based on the rating and evaluation of all files. Do not evaluate each file.


Rating Scale: Based on the comments on each file to give the most objective assessment. Consider giving 4 or 5 points if they don't make many mistakes.
1 = Poor
2 = Below Average (Fresher)
3 = Average (Junior)
4 = Good (Middle)
5 = Excellent (Senior)

return Vietnamese text for the summary and grading.
"""
)
from src.config.llm import get_llm
from pydantic import BaseModel, Field


class CheckRelevantCriteriaOutput(BaseModel):
    relevant_criteria: bool = Field(
        ...,
        description="True if the criteria is designed to evaluate the file content Else return False",
    )


class AnaLyzeOutput(BaseModel):
    comment: str = Field(
        ...,
        description="Comment for the code line need to be improved. Return in Markdown text",
    )
    criteria_eval: str = Field(
        ...,
        description="Criteria evaluation for the code file. Return in Markdown text",
    )
    rating: int = Field(
        ...,
        description="Status of the code file: 1=Poor, 2=Below Average, 3=Average, 4=Good, 5=Excellent",
    )


def grade_code_quality_chain(
    llm: BaseChatModel,
) -> dict[str, Runnable]:

    chain_organized_project_structure_grade = (
        organized_project_structure_grade_prompt | llm
    )
    chain_project_description_generator = project_description_generator_prompt | llm
    chain_check_relevant_criteria = (
        check_relevant_criteria_prompt
        | llm.with_structured_output(CheckRelevantCriteriaOutput)
    )
    chain_analyze_code_file = analyze_code_files_prompt | llm.with_structured_output(
        AnaLyzeOutput
    )
    chain_summarize_code_review = grade_code_across_review_prompt | llm

    return {
        "organized_project_structure_grade": chain_organized_project_structure_grade,
        "project_description_generator": chain_project_description_generator,
        "check_relevant_criteria": chain_check_relevant_criteria,
        "analyze_code_file": chain_analyze_code_file,
        "summarize_code_review": chain_summarize_code_review,
    }


# chain_final_grade = final_grade_prompt | llm_4o_mini
