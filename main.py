import secrets
from fastapi import FastAPI,Depends,HTTPException,Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from config import ROOT, ADMIN_USERNAME, ADMIN_PASSWORD
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from database import engine,SessionLocal
import models,schemas
from auth import create_token,verify_token,hash_password,check_password

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Blog Application",
    description="This is a blog application built with FastAPI and SQLAlchemy.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

#DB Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

#Login API
def current_user(payload = Depends(verify_token), db: Session = Depends(get_db)):
    if payload["kind"] == "admin" and payload["sub"] == ADMIN_USERNAME and ADMIN_PASSWORD:
        return {"id": None, "username": ADMIN_USERNAME, "is_admin": True}
    if payload["kind"] == "user" and payload["sub"].isdigit():
        user = db.get(models.User, int(payload["sub"]))
        if user:
            return {"id": user.id, "username": user.username, "is_admin": False}
    raise HTTPException(status_code=401, detail="Please sign in again.")


def token_response(user):
    subject = ADMIN_USERNAME if user["is_admin"] else str(user["id"])
    return {"access_token": create_token({"sub": subject, "kind": "admin" if user["is_admin"] else "user"}),
            "token_type": "bearer", "user": user}


@app.post("/register", response_model=schemas.TokenResponse, status_code=201)
def register(details: schemas.RegisterRequest, db: Session = Depends(get_db)):
    username = details.username.lower()
    if username == ADMIN_USERNAME.lower() or db.query(models.User).filter_by(username=username).first():
        raise HTTPException(status_code=409, detail="That username is already taken. Please choose another.")
    user = models.User(username=username, password_hash=hash_password(details.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="That username is already taken. Please choose another.")
    db.refresh(user)
    return token_response({"id": user.id, "username": user.username, "is_admin": False})


@app.get("/me", response_model=schemas.UserResponse)
def me(user = Depends(current_user)):
    return user


@app.post("/login", response_model=schemas.TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    if len(form.username) > 128 or len(form.password) > 128:
        raise HTTPException(status_code=401, detail="Incorrect username or password.")
    if ADMIN_PASSWORD and secrets.compare_digest(form.username.lower().encode(), ADMIN_USERNAME.lower().encode()) and secrets.compare_digest(form.password.encode(), ADMIN_PASSWORD.encode()):
        return token_response({"id": None, "username": ADMIN_USERNAME, "is_admin": True})
    user = db.query(models.User).filter_by(username=form.username.lower()).first()
    # Use the same password hashing work for unknown usernames.
    if user:
        valid = check_password(form.password, user.password_hash)
    else:
        hash_password(form.password)
        valid = False
    if not valid:
        raise HTTPException(status_code=401, detail="Incorrect username or password.", headers={"WWW-Authenticate": "Bearer"})
    assert user is not None
    return token_response({"id": user.id, "username": user.username, "is_admin": False})

#Home
@app.get("/")
def home():
    return FileResponse(ROOT / "frontend" / "index.html")

@app.get("/health")
def health():
    return{
        "message":"Blog API Started"
    }



#Create Blog (Protected)
@app.post("/blogs", response_model=schemas.BlogResponse)
def create_blog(blog:schemas.BlogCreate, db:Session = Depends(get_db), user = Depends(current_user)):
    new_blog = models.Blog(
        title = blog.title,
        content = blog.content
    )
    if not user["is_admin"]:
        new_blog.ownership = models.BlogAuthor(user_id=user["id"])
    db.add(new_blog)
    db.commit()
    db.refresh(new_blog)

    return new_blog

#Read All Blog
@app.get("/blogs", response_model=schemas.BlogPage)
def get_blogs(page: int = Query(default=1, ge=1),
              limit: int = Query(default=6, ge=1, le=100),
              search:str = Query(default="", max_length=200),
              db: Session = Depends(get_db)):
    query = db.query(models.Blog)
    if search:
        query = query.filter(models.Blog.title.ilike(f"%{search}%"))

    total = query.count()
    start = (page-1)*limit
    blogs = query.order_by(models.Blog.id.desc()).offset(start).limit(limit).all()

    return{
        "page": page,
        "limit": limit,
        "total": total,
        "data":blogs
    }

#READ one Blog
@app.get("/blogs/{id}", response_model=schemas.BlogResponse)
def get_blog(id:int, db:Session = Depends(get_db)): 
    blog = db.query(models.Blog).filter(models.Blog.id == id).first()
    if not blog:
        raise HTTPException(status_code=404, detail=f"Blog with the id {id} is not available")
    return blog 

#Update Blog API(protected)
@app.put("/blogs/{id}",response_model=schemas.BlogResponse)
def update_blog(id:int,blog:schemas.BlogCreate,db: Session = Depends(get_db), user = Depends(current_user)):
    existing_blog = db.query(models.Blog).filter(models.Blog.id == id).first()

    if not existing_blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    if not user["is_admin"] and existing_blog.owner_id != user["id"]:
        raise HTTPException(status_code=403, detail="You can only edit your own stories.")
    
    existing_blog.title = blog.title
    existing_blog.content = blog.content

    db.commit()

    return existing_blog

#Delete Blog API(protected)
@app.delete("/blogs/{id}")
def delete_blog(id:int, db:Session = Depends(get_db), user = Depends(current_user)):
    existing_blog = db.query(models.Blog).filter(models.Blog.id == id).first()

    if not existing_blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    if not user["is_admin"] and existing_blog.owner_id != user["id"]:
        raise HTTPException(status_code=403, detail="You can only delete your own stories.")
    
    db.delete(existing_blog)
    db.commit()

    return {"message": f"Blog with id {id} has been deleted successfully."}

app.mount("/static", StaticFiles(directory=ROOT / "frontend"), name="static")
