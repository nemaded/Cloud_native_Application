from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
# from .config import Settings
from dotenv import load_dotenv


import os


# Check if we are running in GitHub Actions workflow environment

is_github_actions = os.getenv("CI") == "true"
print("git hub true")

if is_github_actions:

    POSTGRES_PASSWORD = os.getenv("PGPASSWORD")
    POSTGRES_HOST =os.getenv("PGHOST")
    print(POSTGRES_HOST)
    print(POSTGRES_HOST)
    print(POSTGRES_HOST)

    DATABASE_URL = f"postgresql://postgres:{POSTGRES_PASSWORD}@{POSTGRES_HOST}/cloud_bd"

else:
    # Load environment variables from the ".env" file
        load_dotenv(".env")
        POSTGRES_PASSWORD = os.getenv("PGPASSWORD")
        print(POSTGRES_PASSWORD)
        POSTGRES_HOST = os.getenv("RDS_ENDPOINT")
        POSTGRES_DATABASE=os.getenv("DATABASE_NAME")
        
       

        DATABASE_URL = f"postgresql://csye6225:{POSTGRES_PASSWORD}@{POSTGRES_HOST}/{POSTGRES_DATABASE}"
  

engine = create_engine(
    DATABASE_URL
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
