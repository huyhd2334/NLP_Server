import glob
import pandas as pd
import asyncio
import ast
import gc
from datasets import Dataset

from app.services.rag_services.rag_service import RAG_responses
from ragas import evaluate
from ragas.metrics import (
    Faithfulness,
    ResponseRelevancy,
    LLMContextRecall,
    LLMContextPrecisionWithReference
)

from langchain_ollama import ChatOllama
from ragas.llms import LangchainLLMWrapper

from langchain_ollama import OllamaEmbeddings
from ragas.embeddings import LangchainEmbeddingsWrapper

from ragas.run_config import RunConfig
from datasets.arrow_writer import cast_to_python_objects

files = glob.glob(r"D:\AI_road\Project\backend_projects\NLP_Server\output\*.csv")
top_k = 5

sem = asyncio.Semaphore(5)

run_config = RunConfig(
    timeout=600,
    max_workers=8
)

judge = ChatOllama(
    model="Gemma3:4B",
    temperature=0,
    format="json"
)

ragas_llm = LangchainLLMWrapper(judge)

emb = OllamaEmbeddings(model="nomic-embed-text:latest")
ragas_emb = LangchainEmbeddingsWrapper(emb)

async def process_row_with_semaphore(row, documents, top_k):
    async with sem:
        return await process_row(row, documents, top_k)
    
async def process_row(row, documents, top_k):
    query = row.user_input
    reference = row.reference
    try:
        reference_contexts = ast.literal_eval(row.reference_contexts)
    except Exception:
        reference_contexts = []

    prediction, chunks = await RAG_responses(query, documents, top_k)
    
    resp = prediction.get("response", {})
    answer = resp.get("answer", "") if isinstance(resp, dict) else str(resp)
    
    return {
        "user_input": query,
        "response": answer,
        "reference": reference,
        "reference_contexts": reference_contexts,
        "retrieved_contexts": [
            c["text"] if isinstance(c, dict) else str(c)
            for c in chunks
        ]
    }

async def evaluate_def():
    all_samples = []
    
    for file in files:
        df = pd.read_csv(file)
        documents = [int(file[-6:-4])]
        
        tasks = [process_row_with_semaphore(row, documents, top_k) for row in df.itertuples(index=False)]    

        file_samples = await asyncio.gather(*tasks)
        
        all_samples.extend(file_samples)
        print(f"Done RAG for file: {file} ({len(file_samples)} samples)")

    if not all_samples:
        print("Không có dữ liệu để đánh giá.")
        return

    print(f"Ragas for total {len(all_samples)} samples...")

    valid_samples = []
    skipped_count = 0

    for idx, sample in enumerate(all_samples):
        try:
            clean_sample = {
                "user_input": str(sample.get("user_input", "")),
                "response": str(sample.get("response", "")),
                "reference": str(sample.get("reference", "")),
                "reference_contexts": [str(c) for c in sample.get("reference_contexts", [])],
                "retrieved_contexts": [str(c) for c in sample.get("retrieved_contexts", [])]
            }
            
            cast_to_python_objects(clean_sample)
            
            valid_samples.append(clean_sample)
            
        except Exception as pyarrow_err:
            skipped_count += 1
            print(f"[WARNING] Discarded sample {idx + 1} due to (ArrowTypeError): {pyarrow_err}")
            continue

    print(f"[INFO] Inject success: {len(valid_samples)}/{len(all_samples)} valid samples. (miss: {skipped_count} error samples).")

    if len(valid_samples) == 0:
        print("[ERROR] No valid sample found")
        return

    dataset = Dataset.from_list(valid_samples)

    result = evaluate(
        dataset,
        metrics=[
            Faithfulness(),
            ResponseRelevancy(),
            LLMContextRecall(),
            LLMContextPrecisionWithReference(),
        ],
        llm=ragas_llm,
        embeddings=ragas_emb,
        run_config=run_config
    )
    
    print("\nFinall results:")
    print(result)

async def main():
    await evaluate_def()

if __name__ == "__main__":
    asyncio.run(main())