"""
Module used for modelling objects from sqlalchemy.orm 
Those objects can then easy get passed in the DB.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from database import Role
from enum import Enum

class userNew(BaseModel):
    """
    Scheme for any new user.
    """
    username: str = Field(..., example="Bobby", min_length=4, description="Unique user name")
    nickname: Optional[str] = Field(..., example="Bobby", min_length=4, description="Unique user name")
    email: EmailStr = Field(..., example="Bobby@my_worl.com", description="Unique user e-mail")
    password: str = Field(..., example="who is afraid of 6", min_length=6, description="User's password")
    role: Role = Field(..., description="User's role")


class userInDB(userNew):
    """
    Scheme for any existing user in DB
    """
    id: int = Field(..., example=1, description="User's unique ID")
    is_active: bool = Field(..., example=True, description="User's status : active / inactive")
    
    class Config:
        orm_mode = True
        
class userCreateInDB(userNew):
    """
    Scheme to enter a new user into the DB.
    """
    is_active: bool = True


class userUpdateInDB(BaseModel):
    """
    Scheme to update any user in the DB.
    """
    username: Optional[str] = Field(None, description="New username")
    nickname: Optional[str] = Field(None, example="Bobby", min_length=4, description="Unique user name")
    email: Optional[EmailStr] = Field(None, description="New e-mail")
    is_active: Optional[bool] = Field(None, description="Enable or disable user account")
    password: Optional[str] = Field(None, description="New password")
    role: Optional[Role] = Field(None, description="New user's role")  
    # Use None arg to avoid compulsory argument when creating userUpdateInDB
    # Use ... if all arguments must appear when creating the object.

class userDelete(BaseModel):
    """
    Scheme to delete a user in the DB.
    """
    id: int = Field(..., example=1, description="User's unique ID | Primary key of user in the users table.")       

