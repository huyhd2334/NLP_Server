from app.services.upload_services.main_upload_service import main_upload_service
from app.services.rag_services.vector_service import init_qdrant
import glob
import os
import asyncio

from dotenv import load_dotenv

load_dotenv()

pdfs = glob.glob(r"D:\AI_road\Project\backend_projects\NLP_Server\docs\*.pdf")

async def loader():
    await init_qdrant()
    for i, pdf in enumerate(pdfs):
        try:
            result = await main_upload_service(file_path=pdf, file_id=str(i))
            print(f'docs {i+1} / {len(pdfs)} Done \n result: {result}')
        except Exception as e:
            print(f'[ERROR] docs {i} ({pdf}) failed: {e}')
            continue

async def main():
    await loader()

if __name__ == "__main__":
    asyncio.run(main())

