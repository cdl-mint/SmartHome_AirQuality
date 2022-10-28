from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import psycopg2

class Settings:
    PROJECT_NAME:str = "CDL-MINT Project-Perform CRUD operations on smart devices based on indoor air quality with the APIs"
    PROJECT_VERSION: str = "1.0.0"
    POSTGRES_USER : str = "postgres"
    POSTGRES_PASSWORD = "cdlmint"
    POSTGRES_SERVER : str = "timeScaleDatabaseSRAQ"
    POSTGRES_PORT : str = "5432"
    POSTGRES_DB : str ="cdl-mint"
    DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"

#psycopg2 db url format
    psycopg2_DATABASE_URL="user='{}' password='{}' host='{}' dbname='{}' port='{}'".format(POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_SERVER, POSTGRES_DB, POSTGRES_PORT)
   
settings = Settings()

# Create engine using sqlalchemy
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
#SQLALCHEMY_DATABASE_URL = "postgresql://postgres:cdlmint@timeScaleDatabase:5432/cdl-mint"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
engine.connect()
# Create  Session with engine
SessionLocal = sessionmaker(bind=engine)

#instantiation
db_Session=SessionLocal()
