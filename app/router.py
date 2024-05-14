"""
Module of a sub API dedicated to users management : create, update or delete users
"""

from fastapi import FastAPI, Depends, HTTPException, status, APIRouter, File, Form, UploadFile
import database
from security_center import get_user_with_token
from sqlalchemy.orm import Session
import models
import db_tools

# Create an API router engine
users_router = APIRouter()

# Structure of this sub API
tags_metadata = [
    {
        "name": "User management",
        "description": "User management: Create, update and delete by using JWT token management.",
    }]



# Create a user (user) in DB by the administrator (current_user): holding a valid token through Oauth2).
@users_router.post("/users", response_model=models.userNew, tags=["User management"])
def create_user(user: models.userCreateInDB, db: Session = Depends(database.query_db), 
                current_user: models.userInDB = Depends(get_user_with_token)):
    
    # THe administrator is the only one to create a new user in the database
    if current_user.role != database.Role.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized user")
    
    # Try to find the user in the database.
    existing_user = db.query(database.User).filter(database.User.username == user.username).first()
    # Raise an error if the user already exists in the database.
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This username already exist")
    # Create user in database if credentials and no presence test are OK
    return db_tools.create_user(db=db, user=user)



# Update an existing user (user) by grasping its payload based on its id (primary key in table User) by the admin user (current_user)
@users_router.put("/users/{identifier}", response_model=models.userUpdateInDB, tags=["User management"])
def update_user(identifier: str, user: models.UserUpdate, db: Session = Depends(database.query_db),
                 current_user: models.userInDB = Depends(get_user_with_token)):
    if current_user.role != database.Role.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized user")
    db_user = db_tools.update_user_by_identifier(db=db, identifier=identifier, user_update=user)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user



# Delete an existing user (user) based on its id (primary key in table User) by the admin user (current_user)
@users_router.delete("/users/{identifier}", status_code=status.HTTP_204_NO_CONTENT, tags=["User management"])
def delete_user(identifier: str, db: Session = Depends(database.query_db), 
                current_user: models.userInDB = Depends(get_user_with_token)):
    if current_user.role != database.Role.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized user")
    success =db_tools.delete_user(db=db, identifier=identifier)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"detail": f"User {identifier} deleted"}
