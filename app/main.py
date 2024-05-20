"""
Module for API that provides then following routes:
- Start up and shut down events management 
- Ping the API (Get)  
- Get API info (Get)
- Get a token (Post)
- Import raw data (Post)
- Build dataset (Post) 
- Train a model and save it (Post)
- Get prediction from a features file or manually (Post)
- Check prediction accuracy (Get)
"""

from pathlib import Path
import sys
import os
# Allow importing my modules (users_router, models...) in this file 
sys.path.append(str(Path(__name__).resolve().parent.parent))

from contextlib import asynccontextmanager
from dotenv import load_dotenv
from router import users_router
from fastapi import FastAPI
from security_center import check_password, hash_password
import database
from datetime import datetime as dt, timedelta
import db_tools
import models
from sqlalchemy.exc import OperationalError
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import FastAPI, Depends, HTTPException, status, APIRouter, File, Form, UploadFile
from sqlalchemy.orm import Session
import security_center
from src.data import import_raw_data, make_dataset
from src.models import train_model, predict_model
import json
import pandas as pd
import shutil

# Load .env file variables to the current working environement.
load_dotenv()

# Grasp environment variables from .env file 
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# Create an API cartography
tags_metadata = [
    {
        "name": "Data management",
        "Description": "Data import and dataset bnuilding",
    },
    {
        "name": "Model features",
        "description": "API features such as car accident prediction, model training ...",
    },
    {
        "name": "System",
        "description": "System operations such as checking API operating status",
    }
]


# Managing application startup and closure events
@asynccontextmanager
async def lifespan(api: FastAPI):
    """
    At startup (before the application starts): 
        - checks if users table exists and creates one if it doesn't 
        - checks for the existence of an admin user and creates one if it doesn't exist   
    """
    # Write the opening time in log
    startup_time = dt.strftime(dt.today(),"%Y-%m-%d, %H:%M:%S")
    with open("log.txt", mode="a") as log:
        log.write(f"Application starts up at: {startup_time}") 

    # Connect to database
    db = database.SessionLocal() 
    database.Base.metadata.create_all(bind=database.engine)

    try:
        admin_user = db_tools.get_user(db, username=ADMIN_USERNAME, password=ADMIN_PASSWORD, raise_exception=False)
        if not admin_user:
            user_in = models.userNew(
                username=ADMIN_USERNAME, 
                password=ADMIN_PASSWORD,
                email=ADMIN_EMAIL, 
                role=database.Role.admin
            )
            db_tools.create_user(db=db, user=user_in)
        else:
            print("Admin user already exists.")
    except OperationalError as e:
        print(f"Database access error: {e}")
    finally:
        db.close()
    """
    Then run application
    """
    yield
    """
    Then close application and write the log
    """
    shutdown_time = dt.strftime(dt.today(),"%Y-%m-%d, %H:%M:%S")
    with open("log.txt", mode="a") as log:
        log.write(f"Application shuts down at: {startup_time}") 


# API initialization
api = FastAPI(
    lifespan=lifespan,
    title="Car accidents API",
    description="My Car Accidents prediction using an API.",
    version="1.1",
    openapi_tags=tags_metadata)

# Include the sub API "router" for users management purpose
api.include_router(users_router)

# Ping the API and test it works well
@api.get('/ping', tags=["System"])
async def get_ping():
    return "API is working well"

# Get informations on the current API
@api.get("/info", response_class=HTMLResponse, tags=["System"])
def home():
    """
    Get an index page with links to API documentation and OpenAPI requirements.
    """
    return """
    <html>
        <head>
            <title>Project PREDICT CAR ACCIDENTS API - Index</title>
        </head>
        <body>
            <h1>Welcome to our API, dedicated to geographical car accidents prediction</h1>
            <p>Project purpose is to design an application able to predict car accident probabilities by geolocalization in France. This uses a Machine Learning algorithm called Random Forest. The application can predict an accident occurence probability on the location. Also it can retrain automatically if model accuracy decreases under a certain threshold. </p>
            <h2>Please use the following links to access to the API documentation :</h2>
            <ul>
                <li><a href="/docs">Swagger UI</a></li>
                <li><a href="/redoc">Redoc</a></li>
                <li><a href="/openapi.json">Spécification OpenAPI</a></li>
            </ul>
            <h3>Projet MLOps NOV23 - DataScientest</h3>
            <ul>
                <li>BEAUVA Christophe</li>
            </ul>

        </body>
    </html>
    """

# Get a token if the user is registered into the database
@api.post("/token", tags=["User management"])
async def token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.query_db)):
    user = db_tools.get_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token_expires = timedelta(minutes=security_center.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security_center.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Import raw data from AWS s3 in ./data/raw
@api.post("/raw", tags=["Data management"])
async def import_data(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.query_db)):
    user = db_tools.get_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    import_raw_data.main()
    print("Data have been uploaded from AWS s3 with success in folder: ./data/raw")

# Build a dataset from ./data/raw to ./data/preprocessed where the user can enter a file path
@api.post("/dataset", tags=["Data management"])
async def build_dataset(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.query_db)):
    user = db_tools.get_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    make_dataset.main()
    print("Data have been processed with success and are saved in folder: ./data/preprocessed")

# Train a model and save it on ./src/models
@api.post("/train", tags=["Model features"])
async def train(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.query_db)):
    user = db_tools.get_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    train_model.train()
    print("Model has been trained with success been saved in folder: ./src/models")

# Make a prediction based on features file given by user (file_to_load_path as a json file) or not (in that case, he must fill up features manually).
# If no path provided then the user can enter features manually.
api.post("/prediction/{file_to_load_path}", tags=["Model features"])
async def predict(file_to_load_path: str, 
                form_data: OAuth2PasswordRequestForm = Depends(),
                 db: Session = Depends(database.query_db)):
                   
    user = db_tools.get_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
      
    # If any file path is provided by user => he has to enter feature values manually
    if file_to_load_path is None:
         # features_names = X_train.column.tolist()
         with open('./src/models/test_features.json', 'r', encoding="utf-8") as file:
             features_names = list(json.load(file).keys())
         features = predict_model.get_features_values_manually(features_names)
    else:
        # Try to load data from the path provided by user
        try:
            with open(file_to_load_path, 'r', encoding="utf-8") as file:
                features = json.load(file)
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Unable to load features from provided file path: {str(e)}")
          
    # Compute prediction on provided features
    return {"prediction": predict_model.predict_model(features)}


# Get accuracy of the current model 
@api.get("/accuracy", tags=["Model features"])
async def model_accuracy(form_data: OAuth2PasswordRequestForm = Depends(),db: Session = Depends(database.query_db)):
    user = db_tools.get_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    loaded_model = predict_model.loaded_model
    
    try:
        X_test = pd.read_csv('data/preprocessed/X_test.csv')
        y_test = pd.read_csv('data/preprocessed/y_test.csv')
        return {"accuracy": loaded_model.score(X_test, y_test)}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"X_test or y_test are not available in data/preprocessed/ with Error: {str(e)}")
    

# Save current model as a backup
@api.post("/backup", tags=["Model features"])
async def backup(form_data: OAuth2PasswordRequestForm = Depends(),db: Session = Depends(database.query_db)):
    user = db_tools.get_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    # Get the sources where current model is stored
    source_dir = Path('./src/models/trained_model.joblib')
    datetime_now = dt.now().strftime('%Y%m%d%H%M%S')
    
    
    # Create / use a path where to archive the current trained model
    destination_dir = Path(f'./src/models/archives/archive -{datetime_now}')
    destination_dir.mkdir(parents=True, exist_ok=True)

    # Save in destination directory
    shutil.copy(source_dir, destination_dir)

# Unsave current model and retrieve current model
@api.post("/reverse_backup", tags=["Model features"])
async def backup(form_data: OAuth2PasswordRequestForm = Depends(),db: Session = Depends(database.query_db)):
    user = db_tools.get_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    # Get the sources where current model is stored
    source_dir = list(Path('./src/models/archives/').interdir())[0]  # Take the first available file in archive
    
    # Create / use a path where to archive the current trained model
    destination_dir = Path(f'./src/models/')

    # Save in destination directory
    shutil.copy(source_dir, destination_dir)

