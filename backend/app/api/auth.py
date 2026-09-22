import logging
from fastapi import APIRouter, HTTPException, status, Depends
from app.core.database import get_supabase_client
from app.core.security import get_password_hash, verify_password, create_access_token
from app.models.schemas import UserCreate, UserLogin, Token, UserResponse
from app.api.deps import get_current_user

logger = logging.getLogger("ai_journal.auth")
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate):
    """
    Registers a new user account with secure password hashing.
    Enforces uniqueness on email address.
    """
    supabase = get_supabase_client()
    
    # Check if email is already taken
    existing = supabase.table("users").select("id").eq("email", user_in.email.lower()).execute()
    if existing.data and len(existing.data) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists."
        )

    # Hash password using bcrypt
    hashed = get_password_hash(user_in.password)

    # Insert user record
    insert_res = supabase.table("users").insert({
        "email": user_in.email.lower(),
        "hashed_password": hashed
    }).execute()

    if not insert_res.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user record."
        )

    user_record = insert_res.data[0]
    user_id = str(user_record["id"])

    # Issue JWT Token
    token = create_access_token({"sub": user_id, "email": user_record["email"]})
    
    return Token(
        access_token=token,
        token_type="bearer",
        user=UserResponse(id=user_id, email=user_record["email"])
    )


@router.post("/login", response_model=Token)
async def login(user_in: UserLogin):
    """
    Authenticates an existing user and returns a signed JWT access token.
    """
    supabase = get_supabase_client()

    query_res = supabase.table("users").select("*").eq("email", user_in.email.lower()).execute()
    if not query_res.data or len(query_res.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )

    user_record = query_res.data[0]
    if not verify_password(user_in.password, user_record["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )

    user_id = str(user_record["id"])
    token = create_access_token({"sub": user_id, "email": user_record["email"]})

    return Token(
        access_token=token,
        token_type="bearer",
        user=UserResponse(id=user_id, email=user_record["email"])
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserResponse = Depends(get_current_user)):
    """Returns the currently authenticated user's profile."""
    return current_user
