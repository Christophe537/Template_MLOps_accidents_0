"""
This module purpose is to test API functions when when launching the application.
Tests are launched when push occurs in github or through the related git action.

We import function from the API, mock them and test them asynchronously using pytest
"""
import pytest
import sys
import os

# Get the absolute path of the parent directory
parent_folder_path = os.path.abspath(os.path.join(os.path.dirname(__name__), ".."))

# Add it to modules search path
sys.path.append(parent_folder_path)

# Get the current directory path
current_directory = os.path.abspath(os.path.dirname(__name__))

# Add current directory to sys.path if missing out 
if current_directory not in sys.path:
    sys.path.insert(0, current_directory)

from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status
from my_api import get_ping, predict
# Replace my_api by main in Github
from models import userNew
import database
from dotenv import load_dotenv

# Load .env file variables to the current working environement.
load_dotenv()

# Grasp environment variables from .env file 
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

#Define a valid user
valid_user = userNew(username=ADMIN_USERNAME, password=ADMIN_PASSWORD, email=ADMIN_EMAIL, role=database.Role.admin)
         
# Define an invalid user
fake_user = userNew(username='username', password='username', email='username@username.com', role=database.Role.admin)

# Test that the API is open #######################################################
@pytest.mark.asyncio
async def test_get_ping():
    result = await get_ping()
    assert result.status_code == 200
    assert result.value =="API is working well"

# Test that the admin can make a prediction #######################################
@pytest.mark.asyncio
async def test_predict_valid_user():
    result = await predict(file_to_load_path='./src/models/test_features.json',
                       db=database.query_db,
                       user=valid_user)
    assert result.status_code == 200
    assert result.values.get('prediction') == 0.82  # Number to be checked

# Test that a fake user cannot access to predictions ##############################
@pytest.mark.asyncio
async def test_predict_fake_user():
    result = await predict(file_to_load_path='./src/models/test_features.json',
                       db=database.query_db,
                       user=fake_user)
    assert result.status_code == 404 # NOT FOUND


# Test negative if a wrong file is provided #######################################
@pytest.mark.asyncio
async def test_predict_fake_file():
    result = await predict(file_to_load_path='dummy_path',
                       db=database.query_db,
                       user=valid_user)
    assert result.status_code == 404 # NOT FOUND

