"""
Module to interact with database : create, update, delete, get a user, get all database users
"""

from sqlalchemy.orm import Session
from sqlalchemy import exc
import database, models
from fastapi import HTTPException
from security_center import check_password, hash_password, create_access_token 
from datetime import datetime as dt


def create_user(db: Session, user: models.userCreateInDB):
    """
    Try to create/commit a new user in the database based on its models data.

    ARGS: 
        - db (Session) : Database Session
        - user (models.userCreateInDB) : user to be created in DB and following userCreateInDB model.
    
    RETURN: 
        models.userCreateInDB: Instance of the created user in the DB.
    
    RAISE EXCEPTION: HTTPException
        Status 400 for a username conflict or validation problem.
        Status 500 for an error from the database.
    """
    # Hash the given password
    hashed_password = hash_password(user.password)

    new_user = models.userCreateInDB(
        username = user.username,
        #nickname = if user.nickname != '':
        #    user.nickname,
        email=user.email,
        hashed_password=hashed_password,
        is_active=True,
        role=user.role
    )
    db.add(new_user)
    try:
        db.commit()
        db.refresh(new_user)
        return new_user
    except exc.IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="This e-mail or username already exist")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error when creating user.: {str(e)}")
    

def get_user(db: Session, username: str, email: str, raise_exception: bool = True):
    """
    Retrieve a user with its username and hashed password (this couple is a foreign key).

    ARGS:
        - db: Session
            The database session. 
        - username: str
            The searched username.
        - email: str
            The user's email.

    RETURN: models.userInDB
        The researched user grasped in the database.

    RAISE EXCEPTION: HTTPException
        Status 400 for an unknown user.
    """
    # Query the user in table User
    user = db.query(database.User).filter(database.User.username == username, database.User.email == email)  # .first()
    if user is None and raise_exception:
        raise HTTPException(status_code=404, detail="User not found")
    if len(user) > 1:
        raise HTTPException(status=404, details="More than one user found with the same username and password")
    return user


def get_all_users(db: Session, raise_exception: bool = True):
    """
    List all users contained in the database with a username.

        ARGS:
        - db: Session
            The database session. 

    RETURN: dict
        The list of users with their details listed by primary key (dic key either).

    RAISE EXCEPTION: HTTPException
        Status 400 if unknown user.
    """

    # Query table User
    users = db.query(database.User).filter(database.User.username != '')  # .first()
    if users is None and raise_exception:
        raise HTTPException(status_code=404, detail="Not any user in the database")
    resp = {}
    for user in users:
        resp[user.id] = {
            "username": user.username,
            "nickname": user.nickname, 
            "email": user.email,
            "hashed_password": user.hashed_password,
            "is_active": user.is_active,
            "role": user.role,
            "timestamp": dt.strftime(user.timestamp,"%Y-%m-%d, %H:%M:%S")
        }
    return resp


def update_user(db: Session, identifier: str, user_update: models.userUpdateInDB):
    """
    Update an existing user in the database based on its id in table User.
    
    ARGS:
        - db: Session
            The database session. 
        - identifier: str
            The id: primary key of the user in table User.
    RETURN: dict
        Updated user details.

    RAISE EXCEPTION: HTTPException
        Status 400 if unknown user.
        Status 500 if database updating error.

    """
    if identifier.isdigit():  
        user = db.query(database.User).filter(database.User.id == int(identifier)).first()
    else:
        user = db.query(database.User).filter(database.User.username == identifier).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get user updated data in dictionnary format
    update_data = user_update.model_dump(exclude_unset=True) # model_dump() -> {}
    
    # Add modification of user in database by setting attributes (key, value) to the user.
    for key, value in update_data.items():
        setattr(user, key, value)  
    # Commit database    
    try:
        db.commit()
        db.refresh(user)
        return user.model_dump(exclude_unset=True)
    except:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error when updating user.")


def delete_user(db: Session, identifier: str):
    """
    Delete an existing user in the database based on its id in table User.
    
    ARGS:
        - db: Session
            The database session. 
        - identifier: str
            The id: primary key of the user in table User.
    RETURN: dict
        Updated user details.

    RAISE EXCEPTION: HTTPException
        Status 400 if unknown user.
        Status 500 if database updating error.

    """
    if identifier.isdigit():
        user = db.query(database.User).filter(database.User.id == int(identifier)).first()
    else:
        user = db.query(database.User).filter(database.User.username == identifier).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        db.delete(user)
        db.commit()
        return {"user": user.model_dump(exclude_unset=True), "detail": "User deleted"}
    except:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error when deleting user.")

