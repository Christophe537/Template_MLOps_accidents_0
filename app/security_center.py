"""
Module managing security purposes based on Oauth2"""

from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from dotenv import load_dotenv, dotenv_values
import os
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import database


# Load .env file variables to the current working environement.
load_dotenv()

# Create constants based on .env variables
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Engine to hash passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def check_password(plain_password, hashed_password):
    """
    Check password authenticity by comparing hashed entered password with the one stored in database.
    
    ARGS : 
        - plain_password (str): plain password entered by user
        - hashed_password (str): present hashed password stored in the database.
    
    RETURN: Boolean
        True if both are identical and False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(plain_password):
    """
    Hash a password using the password context.

    ARGS:
        - plain_password (str): pasword entered by user
    
    RETURN: str
        hashed_password
    """
    return pwd_context.hash(plain_password)


def create_access_token(data: dict, expires_delta: timedelta = None):
    """
    Creates a JWT access token encoded with a secret key and a specific algorithm (from .env).

    The token is created from a supplied data set and can be configured to expire
    after a certain period of time. If no expiry time is supplied, a default time of 15 minutes is applied.

    ARGS:
        - data (dict): Parts of the token body to be encoded.
        - expires_delta (timedelta, optional): timedelta object representing the time until the token expires.
            If None, a default expiration of 15 minutes is used.

    RETURN: str
        Encoded JWT token containing the supplied data and an expiration mark.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Oauth2 engine 
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_user_with_token(db: Session = Depends(database.query_db), token: str = Depends(oauth2_scheme)):

    """
    Get user details from databse if the provided token is valid and if the user exists:
        - Decode the supplied token, 
        - Extract the user name (sub),
        - Attempt to retrieve the corresponding user from the database. 
    
    If the token is invalid, expired, or if the user does not exist in the database then credentials are KO and 
    an HTTP 401 exception is raised.

    ARGS:
        db (Session): The SQLAlchemy database session, automatically injected by FastAPI thanks to the `database.get_db` dependency
        token (str): The JWT token supplied by the user, automatically injected by FastAPI thanks to the `oauth2_scheme` dependency

    RETURN: database.User
        The user instance retrieved from the database if the token is valid and if the user does exist.

    EXCEPTION:
        HTTPException: An HTTP 401 exception is raised if the token:
            - Is invalid
            - Expired
            - No corresponding user is found in the database.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unable to validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Find the user in table User if exists and take the first corresponding occurence.
    user = db.query(database.User).filter(database.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user
