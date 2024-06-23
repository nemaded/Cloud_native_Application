from fastapi import FastAPI, Depends, HTTPException, status, Request, Response
import logging
from sqlalchemy.exc import OperationalError
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from .database import SessionLocal
from sqlalchemy.orm import Session


from .database import  engine
from.database import Base

import pandas as pd

import bcrypt

from .Models import models
from .Schemas import schemas
from .Routes import users, healthcheck, assignment
from statsd import StatsClient

statsduser = StatsClient(host='localhost', port=8125, prefix='fastapi')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("myapp")

#create instance of fastapi()
app = FastAPI()
# Create the tables (if they don't exist)
models.Base.metadata.create_all(bind=engine)

app.include_router(users.router)
app.include_router(healthcheck.router)
app.include_router(assignment.router)

#reading from the csv 
df = pd.read_csv('users.csv')

session_local = SessionLocal()

# Iterate through the rows of the DataFrame and create users
for index, row in df.iterrows():
    user_data = {
        'first_name': row['first_name'],
        'last_name': row['last_name'],
        'email': row['email'],
        'password': row['password']
    }

    # Validate user_data against the Pydantic schema
    try:
        user = schemas.UserCreate(**user_data)
        print(user.password)
    except Exception as e:
        print(f"Validation error for user {row['email']}: {e}")
        continue
    
     # Check if a user with the same email already exists in the database
    existing_user = session_local.query(models.User).filter(models.User.email == user_data['email']).first()

    if existing_user:
        print(f"User with email {user_data['email']} already exists. Skipping.")
        continue

    # Hash the password using bcrypt
    password_hash = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())

    # Create a User instance with the hashed password
    user_modelss = models.User(
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        password=password_hash.decode('utf-8')  # Store the hash as a string
    )

    # Add the user to the session for database insertion
    session_local.add(user_modelss)

# Commit the changes to the database
session_local.commit()

# Close the session
session_local.close()



        














