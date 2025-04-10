from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import gradio as gr
import PyPDF2
import docx
import google.generativeai as genai
import os
import io
import uvicorn
from dotenv import load_dotenv
import magic
import requests

# Load env vars (only for local testing)
load_dotenv()

# Initialize Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = FastAPI()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Core Analysis Functions (Same as before) ---
def extract_text_from_pdf(file_content: bytes): ...

def extract_text_from_docx(file_content: bytes): ...

def analyze_resume(file_content: bytes, target_company: str, interview_type: str): ...

# --- API Endpoints ---
@app.post('/api/analyze')
async def analyze(file: UploadFile = File(...), target_company: str = Form(...), interview_type: str = Form(...)):
    try:
        file_content = await file.read()
        result = analyze_resume(file_content, target_company, interview_type)
        return JSONResponse(content={'result': result})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# --- Gradio Interface ---
def gradio_interface(file: UploadFile, company: str, interview_type: str):
    try:
        file_content = file.read()
        return analyze_resume(file_content, company, interview_type)
    except Exception as e:
        return f"Error: {str(e)}"

# Launch Gradio only in dev mode
if not os.getenv("RAILWAY_ENVIRONMENT"):
    iface = gr.Interface(
        fn=gradio_interface,
        inputs=[
            gr.File(label="Upload Resume"),
            gr.Textbox(label="Target Company"),
            gr.Radio(["Technical", "Behavioral", "Mixed"], label="Interview Type")
        ],
        outputs="text",
        title="Resume Analyzer"
    )
    iface.launch(server_port=8000, server_name="0.0.0.0")

# Start FastAPI
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
    return {"message": "Resume Evaluation API is running!"}

