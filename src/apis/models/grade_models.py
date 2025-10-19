from pydantic import BaseModel, Field
from typing import List, Any, Optional
from datetime import datetime

class GradedAssignment(BaseModel):
    user_id: str = Field(..., description="ID of the user who submitted the assignment")
    project_name: str = Field(..., description="Name of the source code project")
    selected_files: List[str] = Field(..., description="List of files that were graded")
    folder_structure_criteria: Optional[str] = Field(None, description="Folder structure criteria")
    criterias_list: List[str] = Field(..., description="List of grading criteria")
    project_description: Optional[str] = Field(None, description="Project description")
    grade_result: Any = Field(..., description="Final grade result")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now) 