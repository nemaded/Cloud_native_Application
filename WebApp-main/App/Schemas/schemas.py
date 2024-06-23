from pydantic import BaseModel, EmailStr, HttpUrl, UUID4
from datetime import datetime


class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr 
    password: str

class UserOut(BaseModel):
    first_name: str
    last_name: str
    email: str
    
class UserCredentials(BaseModel):
    first_name: str
    password: str

class AssignmentCreate(BaseModel):
    name: str
    points: int
    num_of_attempts: int
    deadline: str

class AssignmentResponse(BaseModel):
    id: str
    name: str
    points: int
    num_of_attempts: int
    deadline: datetime
    owner:UserOut
    assignment_created: datetime
    assignment_updated: datetime

class SubmissionCreate(BaseModel):
    submission_url: str


class SubmissionResponse(BaseModel):
    id: str
    assignment_id: str
    submission_url: str
    submission_date: datetime
    submission_updated: datetime

    class Config:
        orm_mode = True