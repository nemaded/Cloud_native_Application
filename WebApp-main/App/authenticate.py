import base64
from fastapi import Depends, HTTPException, status, utils
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from .database import get_db
from .Models import models
from sqlalchemy import and_
import bcrypt
import logging

security = HTTPBasic()

# Define a dependency function to verify user credentials and retrieve the user from the database
def get_authenticated_user(credentials: HTTPBasicCredentials = Depends(security), db: Session = Depends(get_db)):
    logging.info(f"Attempting authentication for user: {credentials.username}")

    user = db.query(models.User).filter(models.User.email == credentials.username).first()
    if not user:
        logging.warning(f"Authentication failed: No user found with username {credentials.username}")

        raise HTTPException(
            status_code=401,  # Return a 401 Unauthorized status code
            detail="User not found",
        )

    else:
        user = db.query(models.User).filter(
        
            models.User.email == credentials.username,
        
        ).first()
        if bcrypt.checkpw(credentials.password.encode('utf-8'), user.password.encode('utf-8')):
            logging.info(f"User authenticated successfully: {credentials.username}")

            return user
        


        else  : 
            logging.warning(f"Authentication failed: Incorrect password for user {credentials.username}")

            raise HTTPException(
                status_code=401,  # Return a 401 Unauthorized status code
                detail="Wrong credentials",
            )
    
    




