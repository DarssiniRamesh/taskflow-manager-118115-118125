from fastapi import FastAPI, Depends, HTTPException, status, Body, Path
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from passlib.context import CryptContext
import jwt
import uuid
import os

# JWT Configuration
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev_secret_change_me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Password Crypto Context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory databases
db_users: Dict[str, Dict] = {}  # key = email, value = user dict
db_tasks: Dict[str, Dict] = {}  # key = task_id, value = task dict

# OAuth2 scheme for FastAPI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Models

# PUBLIC_INTERFACE
class UserRegister(BaseModel):
    """Request model for user registration."""
    email: EmailStr = Field(..., description="User email address (unique)")
    password: str = Field(..., min_length=6, description="User password, at least 6 characters.")

# PUBLIC_INTERFACE
class UserLogin(BaseModel):
    """Request model for user login."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="Password")

# PUBLIC_INTERFACE
class UserPublic(BaseModel):
    """Public information returned after registration or login."""
    email: EmailStr

# PUBLIC_INTERFACE
class Token(BaseModel):
    """JWT token returned by login endpoint."""
    access_token: str
    token_type: str

# PUBLIC_INTERFACE
class TaskBase(BaseModel):
    """Base model for a task."""
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Task details/description")
    status: str = Field(default="pending", description="Task status, e.g., pending/complete")
    due_date: Optional[datetime] = Field(None, description="Due date for the task")

# PUBLIC_INTERFACE
class TaskCreate(TaskBase):
    """Task creation model."""
    pass

# PUBLIC_INTERFACE
class TaskUpdate(BaseModel):
    """Model for updating a task."""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[datetime] = None

# PUBLIC_INTERFACE
class Task(TaskBase):
    """Full task model (with ID and timestamps)."""
    id: str
    created_at: datetime
    updated_at: datetime

########################################################
# Utility functions

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None

def get_user_by_email(email: str):
    return db_users.get(email)

def authenticate_user(email: str, password: str):
    user = get_user_by_email(email)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user

async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    email: str = payload["sub"]
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=401, detail="Inactive or non-existent user")
    return user

# FastAPI application and OpenAPI settings
app = FastAPI(
    title="TaskFlow Manager - Task Management Backend",
    description=(
        "Backend API for user authentication and task management. Provides endpoints for user registration, login, "
        "and CRUD operations on user tasks. All task endpoints require JWT authentication."
    ),
    version="1.0.0",
    openapi_tags=[
        {"name": "Authentication", "description": "User registration and login endpoints"},
        {"name": "Tasks", "description": "CRUD operations for tasks (JWT required)"}
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update allowed origins as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

########################################################
# ROUTES: AUTH

# PUBLIC_INTERFACE
@app.post("/auth/register", response_model=UserPublic, status_code=201, tags=["Authentication"], summary="Register a new user")
def register(user: UserRegister = Body(...)):
    """
    Register a new user account.

    - **email**: Email address (unique)
    - **password**: Password (min 6 characters)

    Returns the registered user (public fields).
    """
    # Check if user already exists
    if user.email in db_users:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists with this email"
        )
    # Store user with hashed password
    db_users[user.email] = {
        "email": user.email,
        "hashed_password": get_password_hash(user.password)
    }
    return UserPublic(email=user.email)

# PUBLIC_INTERFACE
@app.post("/auth/login", response_model=Token, tags=["Authentication"], summary="Login as an existing user")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Login endpoint for users.

    Accepts email and password, returns a JWT access token for authenticated requests.

    - **username**: Email address (use as username)
    - **password**: Password

    Returns:
        - `access_token`: JWT token string
        - `token_type`: "bearer"

    Example
    -------
    Request body (form data):
        username: test@example.com
        password: hunter2
    """
    # Use OAuth2 form (username is email)
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    access_token = create_access_token(data={"sub": user["email"]})
    return Token(access_token=access_token, token_type="bearer")

########################################################
# ROUTES: TASKS (JWT required)

# PUBLIC_INTERFACE
@app.get("/tasks", response_model=List[Task], tags=["Tasks"], summary="List all user tasks")
def get_tasks(status: Optional[str] = None, sort_by: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """
    Get all tasks for the authenticated user.

    Optional query params:
    - **status**: Filter by status (e.g., 'pending', 'complete')
    - **sort_by**: Sort field - 'due_date', 'created_at', 'updated_at'

    Returns all tasks for the current user.
    """
    # Collect tasks for this user
    tasks = [
        Task(**t) for t in db_tasks.values()
        if t["owner"] == current_user["email"]
    ]
    if status:
        tasks = [t for t in tasks if t.status == status]
    if sort_by in {"due_date", "created_at", "updated_at"}:
        tasks.sort(key=lambda t: getattr(t, sort_by) or datetime.max)
    return tasks

# PUBLIC_INTERFACE
@app.post("/tasks", response_model=Task, status_code=201, tags=["Tasks"], summary="Create a new task")
def create_task(task: TaskCreate, current_user: dict = Depends(get_current_user)):
    """
    Create a new task belonging to the authenticated user.

    - **title**: Task title
    - **description**: Task details (optional)
    - **status**: Task status (default 'pending')
    - **due_date**: Due date in ISO format (optional)

    Returns the created task with ID and timestamps.
    """
    now = datetime.utcnow()
    task_id = str(uuid.uuid4())
    task_dict = task.dict()
    new_task = {
        "id": task_id,
        "owner": current_user["email"],
        "created_at": now,
        "updated_at": now,
        **task_dict
    }
    db_tasks[task_id] = new_task
    return Task(**new_task)

# PUBLIC_INTERFACE
@app.put("/tasks/{task_id}", response_model=Task, tags=["Tasks"], summary="Update an existing task")
def update_task(
    task_id: str = Path(..., description="Task ID"),
    task_update: TaskUpdate = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Update an existing task (only if owned by the current user).

    Fields provided in body will be updated.

    - **task_id**: ID of the task to update
    - **task_update**: Fields to update

    Returns the updated task.
    """
    task = db_tasks.get(task_id)
    if not task or task["owner"] != current_user["email"]:
        raise HTTPException(status_code=404, detail="Task not found")
    updated_fields = task_update.dict(exclude_unset=True)
    for k, v in updated_fields.items():
        if v is not None:
            task[k] = v
    task["updated_at"] = datetime.utcnow()
    db_tasks[task_id] = task
    return Task(**task)

# PUBLIC_INTERFACE
@app.delete("/tasks/{task_id}", status_code=204, tags=["Tasks"], summary="Delete a task")
def delete_task(
    task_id: str = Path(..., description="Task ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a task owned by the authenticated user.

    - **task_id**: ID of the task to delete

    Returns 204 No Content on success.
    """
    task = db_tasks.get(task_id)
    if not task or task["owner"] != current_user["email"]:
        raise HTTPException(status_code=404, detail="Task not found")
    del db_tasks[task_id]
    return

# PUBLIC_INTERFACE
@app.get("/", summary="Health Check")
def health_check():
    """
    Returns a health check message.
    """
    return {"message": "Healthy"}

# PUBLIC_INTERFACE
@app.get("/docs/jwt", tags=["Authentication"], summary="JWT Usage Help")
def jwt_auth_usage():
    """
    Returns OpenAPI JWT authentication usage information for clients.
    """
    return {
        "message": "Use 'Bearer <access_token>' in the Authorization header for all /tasks endpoints."
    }

# Advanced: Override OpenAPI to show JWT auth in docs for /tasks endpoints
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags
    )
    # Patch JWT security to /tasks endpoints
    token_security = {
        "OAuth2PasswordBearer": []
    }
    if "paths" in openapi_schema:
        for path in openapi_schema["paths"]:
            if path.startswith("/tasks"):
                for m in openapi_schema["paths"][path]:
                    operation = openapi_schema["paths"][path][m]
                    operation.setdefault("security", [token_security])
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

