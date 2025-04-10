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
import requests
import zipfile

# Load environment variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("Error: GEMINI_API_KEY not found in environment variables.")

genai.configure(api_key=api_key)

# Initialize FastAPI with CORS
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# File processing functions
def extract_text_from_pdf(file_content: bytes):
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        text = "\n".join([page.extract_text() or "" for page in reader.pages])
        return text.strip() if text.strip() else "Error: Could not extract text from PDF."
    except Exception as e:
        return f"Error reading PDF: {e}"

def extract_text_from_docx(file_content: bytes):
    try:
        file_stream = io.BytesIO(file_content)
        doc = docx.Document(file_stream)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text.strip() if text.strip() else "Error: Could not extract text from DOCX."
    except Exception as e:
        return f"Error reading DOCX: {e}"

def get_file_type(file_content: bytes):
    """Simplified file type detection without magic"""
    if file_content.startswith(b'%PDF'):
        return 'pdf'
    elif file_content.startswith(b'PK\x03\x04'):
        try:
            with io.BytesIO(file_content) as f:
                with zipfile.ZipFile(f) as z:
                    if 'word/document.xml' in z.namelist():
                        return 'docx'
        except:
            pass
    return 'unknown'

def analyze_resume(file_content: bytes, target_company: str, interview_type: str):
    if not file_content:
        return "Please upload a resume file."

    file_type = get_file_type(file_content)
    print(f"Detected file type: {file_type}")

    if file_type == 'pdf':
        resume_text = extract_text_from_pdf(file_content)
    elif file_type == 'docx':
        resume_text = extract_text_from_docx(file_content)
    else:
        return "Unsupported file format. Please upload a PDF or DOCX file."

    if "Error" in resume_text:
        return resume_text

    prompt = f"""
    Analyze the following resume for a candidate targeting {target_company} for a {interview_type} interview.
    Provide the following:
    1. An overall score out of 10.
    2. Scores out of 10 for clarity, relevance, skills, experience, and formatting.
    3. Specific suggestions for improvement.
    
    Resume:
    {resume_text}
    """

    try:
        model = genai.GenerativeModel("gemini-1.5-pro-002")
        response = model.generate_content(prompt)
        return response.text.strip() if response.text else "No response generated."
    except Exception as e:
        return f"Error generating AI response: {e}"

# FastAPI Endpoints
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
    return {"status": "healthy", "version": "1.0"}

# Gradio Interface
def create_gradio_interface():
    def gradio_interface(file: UploadFile, target_company: str, interview_type: str):
        try:
            file_content = file.read()
            return analyze_resume(file_content, target_company, interview_type)
        except Exception as e:
            return f"Error processing file: {str(e)}"

    with gr.Blocks() as interface:
        gr.Markdown("## Resume Analyzer")
        with gr.Tab("Standard Interface"):
            file_input = gr.File(label="Upload Resume (PDF/DOCX)")
            company_input = gr.Textbox(label="Target Company")
            interview_input = gr.Radio(["Technical", "Behavioral", "Mixed"], label="Type of Interview")
            output = gr.Textbox(label="Analysis Result")
            analyze_btn = gr.Button("Analyze")
            
            analyze_btn.click(
                fn=gradio_interface,
                inputs=[file_input, company_input, interview_input],
                outputs=output
            )
        
        with gr.Tab("API Tester"):
            gr.Markdown("### Test FastAPI Endpoint")
            api_output = gr.Textbox(label="API Response")
            test_api_btn = gr.Button("Test /health Endpoint")
            
            def test_api():
                try:
                    response = requests.get(f"http://localhost:{os.getenv('PORT', 8000)}/health")
                    return f"Status Code: {response.status_code}\nResponse: {response.text}"
                except Exception as e:
                    return f"API Test Failed: {str(e)}"
            
            test_api_btn.click(fn=test_api, outputs=api_output)

    return interface

# Railway-optimized launch
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    
    # Only launch Gradio in development mode
    if not os.getenv("RAILWAY_ENVIRONMENT"):
        gradio_interface = create_gradio_interface()
        gradio_interface.launch(
            server_name="0.0.0.0",
            server_port=port,
            share=False
        )
    else:
        # In production, just run FastAPI
        uvicorn.run(app, host="0.0.0.0", port=port)
