import os
from contextlib import asynccontextmanager
import fitz
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from .database import Base, engine, get_db
from .models import User, Document, Chunk
from .security import passwords, create_token, get_user
from .retrieval import split_text, retrieve
from .llm import generate_answer

MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_PAGES = 100

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)  # use Alembic migrations for production
    yield

app = FastAPI(title="DocuMind", version="1.0.0", lifespan=lifespan)

class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

class Question(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=3, ge=1, le=5)

@app.post("/auth/register", status_code=201)
def register(data: Credentials, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email==data.email)):
        raise HTTPException(409,"Email already registered")
    user = User(email=data.email, password_hash=passwords.hash(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"token": create_token(user.id)}

@app.post("/auth/login")
def login(data: Credentials, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email==data.email))
    if not user or not passwords.verify(data.password, user.password_hash):
        raise HTTPException(401,"Invalid credentials")
    return {"token": create_token(user.id)}

@app.post("/documents", status_code=201)
async def upload(file: UploadFile = File(...), user: User = Depends(get_user), db: Session = Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400,"Only PDF files are accepted")
    data = await file.read(MAX_PDF_BYTES + 1)
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(413,"PDF exceeds 10 MB")
    if not data.startswith(b"%PDF-"):
        raise HTTPException(400,"Invalid PDF signature")
    try:
        pdf = fitz.open(stream=data, filetype="pdf")
        if pdf.page_count > MAX_PAGES:
            raise HTTPException(413,"PDF exceeds 100 pages")
        page_texts = [(i+1, page.get_text("text")) for i,page in enumerate(pdf)]
        pdf.close()
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(400,"Unreadable PDF") from exc
    doc = Document(owner_id=user.id, filename=os.path.basename(file.filename)[:255])
    db.add(doc)
    db.flush()
    count = 0
    for page_no, text in page_texts:
        for idx, chunk in enumerate(split_text(text)):
            db.add(Chunk(document_id=doc.id, page=page_no, position=idx, text=chunk))
            count += 1
    if count == 0:
        db.rollback()
        raise HTTPException(422,"No extractable text; scanned PDFs need OCR")
    db.commit()
    return {"id":doc.id,"filename":doc.filename,"pages":len(page_texts),"chunks":count}

@app.get("/documents")
def list_documents(user:User=Depends(get_user),db:Session=Depends(get_db)):
    docs=db.scalars(select(Document).where(Document.owner_id==user.id)).all()
    return [{"id":d.id,"filename":d.filename,"status":d.status} for d in docs]

@app.post("/documents/{document_id}/ask")
async def ask(document_id:int, data:Question, user:User=Depends(get_user),db:Session=Depends(get_db)):
    doc=db.scalar(select(Document).where(Document.id==document_id,Document.owner_id==user.id))
    if doc is None:
        raise HTTPException(404,"Document not found")
    rows=db.scalars(select(Chunk).where(Chunk.document_id==document_id)).all()
    records=[{"page":r.page,"text":r.text,"chunk_id":r.id} for r in rows]
    passages=retrieve(data.question,records,data.top_k)
    answer,mode=await generate_answer(data.question,passages)
    return {"document_id":document_id,"question":data.question,"answer":answer,"mode":mode,"sources":passages}

@app.delete("/documents/{document_id}",status_code=204)
def delete_document(document_id:int,user:User=Depends(get_user),db:Session=Depends(get_db)):
    doc=db.scalar(select(Document).where(Document.id==document_id,Document.owner_id==user.id))
    if not doc:
        raise HTTPException(404,"Document not found")
    db.delete(doc)
    db.commit()
