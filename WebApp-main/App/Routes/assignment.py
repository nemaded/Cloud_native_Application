from typing import List
from fastapi import APIRouter, Depends, HTTPException, Header, Response, status,Request
from sqlalchemy.orm import Session
from ..Schemas import schemas
from..Models import models
import logging
from ..database import get_db,create_engine,DATABASE_URL
from ..authenticate import get_authenticated_user
import json
import boto3

from .. import main
import os
from botocore.exceptions import NoCredentialsError, ClientError
from dotenv import load_dotenv



router = APIRouter(  
    tags=['assignments']
)
load_dotenv(".env")

aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
print(aws_access_key_id)
def check_postgres_status():
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect():
            return "PostgreSQL server is running"
    except :
        raise HTTPException(status_code=503, detail="PostgreSQL server is not running")

 

def request_has_body(request):
    content_length = request.headers.get("content-length")
    return content_length is not None and int(content_length) > 0

def post_to_sns_topic(url: str, user_email: str):
    sns_arn = os.getenv('SNS_ARN')
    aws_region = os.getenv('AWS_REGION')  # Add this line


    if not all([sns_arn, aws_region]):
        raise HTTPException(status_code=500, detail="AWS configuration is incomplete")

    message = f"Submission URL: {url}\nUser Email: {user_email}"
    sns_client = boto3.client(
        'sns',
        region_name=aws_region
    )

    try:
        response = sns_client.publish(
            TopicArn=sns_arn,
            Message=message,
            Subject="New Assignment Submission"
        )
        return response
    except NoCredentialsError:
        raise HTTPException(status_code=500, detail="AWS credentials not found")
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))
    

#creating Assignments with the authenticated user
@router.post('/demo/assignments', response_model=schemas.AssignmentResponse,status_code=status.HTTP_201_CREATED)
def create_assignment(request: Request,assignment:schemas.AssignmentCreate,username: str = Header(None), 
                     postgres_status: str = Depends(check_postgres_status),  # Include the dependency here

                      authenticated_user: models.User = Depends(get_authenticated_user),db: Session = Depends(get_db),  authorization: str = Header(None, description="Basic Authentication Header")):
    
    main.statsduser.incr('create_assignment.calling')

    if not (1 <= assignment.points <= 10) or not (1 <= assignment.num_of_attempts <= 3):
        error_detail = "Invalid input. Points should be between 1 and 10, and num_of_attempts should be between 1 and 3."
        logging.error(f"- Failed: {error_detail}")


        raise HTTPException(status_code=400, detail="Invalid input. Points should be between 1 and 10, and num_of_attempts should be between 1 and 3.")
    
    client_host = request.client.host

    log_message_base = f"Assignment creation attempted [Method: POST, Path: /assignments, Client: {client_host}, User: {authenticated_user.first_name}]"
    logging.info(f"{log_message_base} - Success: Assignment created ")

    



    db_assignment = models.Assignment(**assignment.dict())
    db_assignment.owner_id=authenticated_user.id
    db.add(db_assignment)
    db.commit()
    db.refresh(db_assignment)

    return db_assignment


#getting assignment with specific id 
@router.get("/demo/assignments/{id}", response_model=schemas.AssignmentResponse)
def get_assignment(id: str,request: Request,
                   postgres_status: str = Depends(check_postgres_status),  
                   authenticated_user: models.User = Depends(get_authenticated_user), db: Session = Depends(get_db)):
    logging.info(f"User {authenticated_user.email} requested assignment with ID {id}.")
    main.statsduser.incr('get_assignment_by_id.calling')

    if request_has_body(request):
        logging.warning(f"Assignment request by {authenticated_user.email} contained an unexpected payload.")

        raise HTTPException(status_code=400, detail="Request payload is not allowed for GET requests")
  
    assignment = db.query(models.Assignment).filter(models.Assignment.id == id).first()

    if not assignment:
            logging.warning(f"Assignment with ID {id} not found for user {authenticated_user.email}.")

            raise HTTPException(status_code=404, detail="Assignment not found")
    
    if assignment.owner_id != authenticated_user.id:
        logging.error(f"User {authenticated_user.email} attempted to access assignment with ID {id} without permission.")

        raise HTTPException(status_code=403, detail="Permission denied. You can only get assignments of your own.")

    return assignment


#getting  the assignments created by the  user
@router.get("/demo/assignments", response_model=List[schemas.AssignmentResponse])
def get_assignments(request:Request,
                    postgres_status: str = Depends(check_postgres_status),  
                    authenticated_user: models.User = Depends(get_authenticated_user),db: Session = Depends(get_db), authorization: str = Header(None, description="Basic Authentication Header")):
    logging.info(f"User {authenticated_user.email} is retrieving their assignments.")
    main.statsduser.incr('get_all_assignments.calling')
   
    if request_has_body(request):
        logging.warning(f"User {authenticated_user.email} sent a payload with GET request, which is unexpected.")

        raise HTTPException(status_code=400, detail="Request payload is not allowed for GET requests")
    
    assignments = db.query(models.Assignment).filter(models.Assignment.owner_id == authenticated_user.id).all()
    if not assignments:
        logging.info(f"User {authenticated_user.email} has no assignments.")
    
    logging.info(f"User {authenticated_user.email} successfully retrieved their assignments.")

    return assignments


#delete the assignment based on id and only if the user is authenticated 
@router.delete("/demo/assignments/{assignment_id}",status_code=status.HTTP_204_NO_CONTENT )
def delete_assignment(assignment_id: str, request:Request,
                      postgres_status: str = Depends(check_postgres_status),  
                      authenticated_user: models.User = Depends(get_authenticated_user), db: Session = Depends(get_db),authorization: str = Header(None, description="Basic Authentication Header")):
        logging.info(f"User {authenticated_user.email} is attempting to delete assignment with ID: {assignment_id}")
        main.statsduser.incr('delete_assignment.calling')

        if request_has_body(request):
            logging.error(f"User {authenticated_user.email} sent a payload with DELETE request, which is unexpected.")

            raise HTTPException(status_code=400, detail="Request payload is not allowed for GET requests")
        
        assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()

        if not assignment:
            logging.error(f"User {authenticated_user.email} tried to delete a non-existent assignment with ID: {assignment_id}")

            raise HTTPException(status_code=404, detail="Assignment not found")

    # Check if the authenticated user is the owner of the assignment
        if assignment.owner_id != authenticated_user.id:
            logging.error(f"User {authenticated_user.email} attempted to delete assignment with ID: {assignment_id} without proper permissions.")

            raise HTTPException(status_code=403, detail="Permission denied. You can only delete assignments you own.")

   
        db.delete(assignment)
        db.commit()
        logging.info(f"User {authenticated_user.email} successfully deleted assignment with ID: {assignment_id}")


        return Response(status_code=status.HTTP_204_NO_CONTENT)


#updating the user based on the user authenticationn and providing the whole object 
@router.put("/demo/assignments/{assignment_id}")
def update_assignment(
    assignment_id: str,assignment_update: schemas.AssignmentCreate,postgres_status: str = Depends(check_postgres_status),
    
    
    authenticated_user: models.User = Depends(get_authenticated_user),
    db: Session = Depends(get_db)
):
    logging.info(f"User {authenticated_user.email} is attempting to update assignment with ID: {assignment_id}")
    main.statsduser.incr('update_assignment.calling')

    if not (1 <= assignment_update.points <= 10) or not (1 <= assignment_update.num_of_attempts <= 3):
        logging.warning(f"Validation error for the update of assignment with ID: {assignment_id} by user {authenticated_user.email}.")

        raise HTTPException(status_code=400, detail="Invalid input. Points should be between 1 and 10, and num_of_attempts should be between 1 and 3.")
     # Query the assignment by its ID
    assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
   
    if not assignment:
        logging.error(f"Assignment with ID: {assignment_id} not found for user {authenticated_user.email}.")

        raise HTTPException(status_code=404, detail="Assignment not found")

    # Check if the authenticated user is the owner of the assignment
    if assignment.owner_id != authenticated_user.id:
        logging.error(f"User {authenticated_user.email} attempted to update assignment with ID: {assignment_id} without proper permissions.")

        raise HTTPException(status_code=403, detail="Permission denied. You can only update assignments you own.")

    # Update assignment details
    assignment.name = assignment_update.name
    assignment.points = assignment_update.points
    assignment.num_of_attempts = assignment_update.num_of_attempts
    assignment.deadline = assignment_update.deadline

    db.commit()
    logging.info(f"Assignment with ID: {assignment_id} was successfully updated by user {authenticated_user.email}.")


    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.patch("/demo/assignments/{assignment_id}", status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
def update_assignment(assignment_id: str):
    main.statsduser.incr('patch_assignment.calling_denied')
   
    logging.warning(f"Attempt to use disallowed PATCH method on /assignments/{assignment_id}")

    raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED, detail="Patch method is not allowed for this endpoint")

from datetime import datetime

from datetime import datetime

@router.post("/demo/assignments/{assignment_id}/submission", status_code=status.HTTP_201_CREATED, response_model=schemas.SubmissionResponse)
def submit_assignment(
    assignment_id: str, 
    submission_data: schemas.SubmissionCreate, 
    authenticated_user: models.User = Depends(get_authenticated_user), 
    db: Session = Depends(get_db)
):
    logging.info(f"User {authenticated_user.email} is submitting an assignment.")

    # Check if the assignment exists
    assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not assignment:
        logging.error(f"Assignment with ID: {assignment_id} not found.")
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Check if the submission deadline has passed
    if datetime.utcnow() > assignment.deadline:
        logging.warning(f"Submission deadline has passed for assignment with ID: {assignment_id}.")
        raise HTTPException(status_code=400, detail="Submission deadline has passed")

    # Check if the user has already submitted the maximum number of attempts
    submission_count = db.query(models.Submission).filter(
        models.Submission.assignment_id == assignment_id,
        models.Submission.user_id == authenticated_user.id
    ).count()
    if submission_count >= assignment.num_of_attempts:
        logging.warning(f"User {authenticated_user.email} has exceeded the maximum number of submission attempts for assignment {assignment_id}.")
        raise HTTPException(status_code=400, detail="Maximum submission attempts exceeded")

    # Create the submission
    new_submission = models.Submission(
        assignment_id=assignment_id,
        user_id=authenticated_user.id,
        submission_url=submission_data.submission_url,
        submission_date=datetime.utcnow(),
        submission_updated=datetime.utcnow()
    )
    db.add(new_submission)
    db.commit()
    db.refresh(new_submission)

    logging.info(f"User {authenticated_user.email} successfully submitted assignment {assignment_id}.")
    try:
        post_to_sns_topic(new_submission.submission_url, authenticated_user.email)
        logging.info(f"Posted submission details to SNS Topic for user {authenticated_user.email}.")
    except HTTPException as e:
        logging.error(f"Failed to post to SNS Topic: {e.detail}")

    return new_submission
