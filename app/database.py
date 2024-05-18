
"""
Module that initiate or use an existing database.

Define a relational database.

Define an engine and a session function binded to it.
"""

from sqlalchemy import create_engine, Column, Integer, String, Boolean, Enum, DateTime, ForeignKey, func
from sqlalchemy.orm import sessionmaker, relationship, Session, DeclarativeBase, Mapped, mapped_column
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from enum import Enum as PyEnum
from sqlalchemy.orm import validates
from datetime import datetime as dt
from typing import List, Optional


# Default database URL created on related volume
SQLALCHEMY_DATABASE_URL = "sqlite:///./users.db"

# Create a sqlalchemy engine which we will use as the basis for all our db calls
try:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, 
        connect_args={"check_same_thread": False},
        echo=True
        )
except SQLAlchemyError() as e:
    print(f"Database connection error: {e}")
    raise e

# Use class standard to create tables and their related objects at once
# Base = declarative_base()

#######################################################################
# TABLES 
#######################################################################
# Fundamental class generator
class Base(DeclarativeBase):
    pass

# Specific class that lists avaialble roles within users.db
class Role(PyEnum):
    """
    Enumerate available roles
    """
    admin = "Admin role"
    employee = "Employee role"
    client = "Customer role"

# Define table User
class User(Base):
    __tablename__ = "users"
    id = mapped_column(Integer, primary_key=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100))
    nickname: Mapped[Optional[str]] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role))
    timestamp: Mapped[dt] = mapped_column(insert_default = func.now())  # Datetime of recording
    
    __mapper_args__ = {
        'version_id_col': timestamp,
        'version_id_generator': lambda v:dt.now(),
                }

    password: Mapped[List["Password"]] = relationship(back_populates="user", 
                                                      uselist=False)

    # Set constraint on email
    @validates('email')
    def validate_email(self, key, email):
        assert '@' in email, "Email address must contain @"
        return email
    
    # Set constraint on username minimum size
    @validates('username')
    def validate_username(self, key, username):
        assert len(username) >= 4, "Username must contain at least 4 characters."
        return username

# Define table for passwords in plain text
class Password(Base):
    __tablename__ = "passwords"
    id = mapped_column(Integer, primary_key=True)
    pass_id = mapped_column(ForeignKey("users.id"))
    plain_password: Mapped[str]
    
    user: Mapped["User"] = relationship(back_populates="password")
    
    # Set a constraint on password size
    @validates('plain_password')
    def validate_password(self, key, plain_password):
        assert len(plain_password) >= 4, "Password must contain at least 4 characters"
        return plain_password

# Build tables
Base.metadata.create_all(engine)

# Use a parametrized connection for any calls and bind it with engine
# sessionmaker is more structured than session (from sqlalchemy.orm)
# Connect to the local database
SessionLocal  = sessionmaker(autocommit=False, autoflush=False, bind=engine)
session = Session(bind=engine)

#######################################################################
# CONNECT TO DATABASE
#######################################################################
# Function used to call database from outter modules
def query_db():
    
    """
    Creates a new SQLAlchemy session for a query,
    and close it once the request has been completed.
    """
    db = SessionLocal()
    
    try:
       yield db
       
    finally:
       db.close()

