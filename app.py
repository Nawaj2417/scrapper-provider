from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
import uuid, os, asyncio
from src.excel_utils import process_excel

app = FastAPI()

UPLOADS = "uploads"
OUTPUTS = "outputs"
os.makedirs(UPLOADS, exist_ok=True)
os.makedirs(OUTPUTS, exist_ok=True)

@app.post("/upload")
async def upload_excel(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    input_path = f"{UPLOADS}/{job_id}.xlsx"
    output_path = f"{OUTPUTS}/{job_id}_enriched.xlsx"

    with open(input_path, "wb") as f:
        f.write(await file.read())

    await process_excel(input_path, output_path)

    return {
        "job_id": job_id,
        "download_url": f"/download/{job_id}"
    }

@app.get("/download/{job_id}")
def download(job_id: str):
    path = f"{OUTPUTS}/{job_id}_enriched.xlsx"
    return FileResponse(path, filename="scraped.xlsx")
