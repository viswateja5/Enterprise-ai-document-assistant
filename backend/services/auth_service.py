from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.db_models import User
from schemas.api_schemas import UserCreate
from auth.security import get_password_hash, verify_password

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """
    Queries database to find a user by their username.
    """
    result = await db.execute(select(User).where(User.username == username))
    return result.scalars().first()

async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    """
    Registers a new user account, encrypting their password.
    
    Raises:
        ValueError: If username is already taken.
    """
    existing_user = await get_user_by_username(db, user_in.username)
    if existing_user:
        raise ValueError("Username is already registered.")
        
    db_user = User(
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password)
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    """
    Validates user credentials against database hashed passwords.
    
    Returns:
        User: The authenticated user model instance if valid, else None.
    """
    user = await get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
