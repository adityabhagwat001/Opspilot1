from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.audit import AuditLog
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.core.security import verify_password, get_password_hash, create_access_token
from app.api.deps import get_current_user

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User Account",
    description="Registers a new user account. If this is the first user in the database, automatically assigns the ADMIN role."
)
async def register_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> User:
    # Check if email is already taken
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists."
        )

    # Determine role: if no users exist in the system, promote first user to ADMIN
    user_count_res = await db.execute(select(func.count(User.id)))
    user_count = user_count_res.scalar_one()
    assigned_role = UserRole.ADMIN if user_count == 0 else payload.role

    new_user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        role=assigned_role,
        is_active=True
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Audit log
    audit_entry = AuditLog(
        user_id=new_user.id,
        action="USER_REGISTERED",
        resource=f"user:{new_user.id}",
        details=f"User {new_user.email} registered with role {new_user.role.value}"
    )
    db.add(audit_entry)
    await db.commit()

    return new_user


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="User Authentication Login",
    description="Authenticates user credentials and returns a signed JWT Bearer access token."
)
async def login_user(
    payload: UserLogin,
    db: AsyncSession = Depends(get_db)
) -> Token:
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email address or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is currently inactive. Contact your system administrator."
        )

    access_token = create_access_token(subject=user.id, role=user.role.value)

    # Record login audit trace
    audit_entry = AuditLog(
        user_id=user.id,
        action="USER_LOGIN_SUCCESS",
        resource=f"user:{user.id}",
        details=f"Successful login from user {user.email}"
    )
    db.add(audit_entry)
    await db.commit()

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current User Profile",
    description="Returns the profile and role permissions of the currently authenticated user."
)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
