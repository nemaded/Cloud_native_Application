import csv
import os
import bcrypt

from fastapi import APIRouter, FastAPI, HTTPException, status, Depends
from fastapi.responses import JSONResponse
import pandas as pd
from sqlalchemy.orm import Session
from pydantic import ValidationError

from ..Schemas import schemas
from ..Models import models
from ..database import engine, SessionLocal, get_db






#stroing the response schema to use it directly
user_output=schemas.UserOut

#using the router path to send it to main file in include_router 
router = APIRouter(    
    tags=['Users']
)

#function to write the user created successfully into the csv also
def write_user_to_csv(first_name, last_name, email, password):
    # Define the path to the CSV file
    csv_file = 'users.csv'

    # Append the new user's data to the CSV file
    with open(csv_file, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['first_name', 'last_name', 'email', 'password'])
        writer.writerow({'first_name': first_name, 'last_name': last_name, 'email': email, 'password': password})


  

#adds a user to the database and also to the csv 
@router.post("/users", status_code=status.HTTP_201_CREATED, response_model=user_output)
def create_user(user: schemas.UserCreate,  db: Session = Depends(get_db)):

    try:
        new_user = models.User(**user.dict())
        password_hash = bcrypt.hashpw(new_user.password.encode('utf-8'), bcrypt.gensalt())
        user_model = models.User(
            first_name=new_user.first_name,
            last_name=new_user.last_name,
            email=new_user.email,
            password=password_hash.decode('utf-8')
        )
        db.add(user_model)
        db.commit()
        db.refresh(user_model)
       
          # Create variables for user data
        first_name = new_user.first_name
        last_name = new_user.last_name
        email = new_user.email
        password = password_hash.decode('utf-8')

        # Call the function to write user data to the CSV file
        write_user_to_csv(first_name, last_name, email, password)

        return {"first_name": new_user.first_name, "last_name": new_user.last_name, "email": new_user.email}
    except Exception as e:
        # Handle exceptions, possibly raise an HTTPException if there's an error
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User creation failed")
    finally:
        # Close the database session when done, regardless of success or failure
        db.close()
