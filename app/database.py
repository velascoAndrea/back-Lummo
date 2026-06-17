import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://lummo:lummo_dev@localhost:5432/lummo_db")

# Lambda doesn't support persistent connection pools
is_lambda = bool(os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
engine = create_engine(DATABASE_URL, poolclass=NullPool if is_lambda else None)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
