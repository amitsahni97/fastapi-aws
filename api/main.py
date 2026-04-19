from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os
from datetime import datetime, timezone
import random

from .routers import dogs, comments, posts, auth
from .models import Dog, Comment, Post, Image, User, SessionLocal

load_dotenv()

app = FastAPI(
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("API_URL"),"https://backend.queuenahi.com"],  # The default React port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for Swagger UI
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.post("/populate/")
def populate_db():
    session = SessionLocal()
    try:
        # Insert Users
        users = [User(username=f'user{i}', hashed_password=f'hash{i}', first_name=f'First{i}', last_name=f'Last{i}') for i in range(1, 31)]
        session.add_all(users)
        session.commit()

        # Refresh each user instance if necessary
        for user in users:
            session.refresh(user)

        # Insert Dogs, Posts, Comments, and Images
        for user in users:
            dogs = [Dog(name=f'Dog{j}', breed=f'Breed{j%5}', age=random.randint(1, 10), user_id=user.id) for j in range(1, 6)]
            session.add_all(dogs)
            
            posts = [Post(content=f'Content{k}', timestamp=datetime.now(timezone.utc), user_id=user.id) for k in range(1, 11)]
            session.add_all(posts)

            # Insert an Image record with image set to None
            image = Image(image=None, user_id=user.id)
            session.add(image)
        
        session.commit()

        # Collect all posts to randomly assign comments
        all_posts = session.query(Post).all()
        for user in users:
            selected_posts = random.sample(all_posts, 4)
            for post in selected_posts:
                comment = Comment(content=f'Comment from user {user.id} on post {post.id}', timestamp=datetime.now(timezone.utc), user_id=user.id, post_id=post.id)
                session.add(comment)

        session.commit()
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()
    return {"message": "Database populated successfully!"}

app.include_router(auth.router)
app.include_router(dogs.router)
app.include_router(comments.router)
app.include_router(posts.router)

@app.get("/health")
async def health_check():
    return {"Healthy": 200}

@app.get("/docs", include_in_schema=False)
async def custom_docs():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="API Docs",
        swagger_js_url="/static/swagger-ui/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui/swagger-ui.css"
    )
