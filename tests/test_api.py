import io
import fitz
from fastapi.testclient import TestClient
from app.main import app

def create_pdf():
    pdf=fitz.open()
    page=pdf.new_page()
    page.insert_text((70,70),"Inventory systems protect stock using database transactions.")
    data=pdf.tobytes()
    pdf.close()
    return data

def test_register_upload_and_question(monkeypatch):
    async def mock_generate(question, passages):
        return "See page 1.", "mock"
    monkeypatch.setattr("app.main.generate_answer", mock_generate)
    with TestClient(app) as client:
        import uuid
        email=f"user-{uuid.uuid4()}@example.com"
        token=client.post("/auth/register",json={"email":email,"password":"password123"}).json()["token"]
        headers={"Authorization":f"Bearer {token}"}
        result=client.post("/documents",headers=headers,files={"file":("sample.pdf",create_pdf(),"application/pdf")})
        assert result.status_code==201, result.text
        docid=result.json()["id"]
        response=client.post(f"/documents/{docid}/ask",headers=headers,json={"question":"What protects stock?"})
        assert response.status_code==200, response.text
        assert response.json()["sources"][0]["page"]==1
        assert client.delete(f"/documents/{docid}",headers=headers).status_code==204
