from app.services.upload_services.main_upload_service import main_upload_service
import glob
import os
import asyncio

from dotenv import load_dotenv

load_dotenv()

pdfs = glob.glob(r"D:\AI_road\Project\backend_projects\NLP_Server\docs\*.pdf")

async def loader():
    for i, pdf in enumerate(pdfs):
        result = await main_upload_service(file_path=pdf, file_id=str(i))
        print(f'docs {i} / {len(pdfs)} Done \n result: {result}')

async def main():
    await loader()

if __name__ == "__main__":
    asyncio.run(main())

