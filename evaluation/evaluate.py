import glob
import pandas as pd
import asyncio
import ast
from datasets import Dataset

from app.services.rag_services.rag_service import RAG_responses
from ragas import evaluate
from ragas.metrics import (
    Faithfulness,
    ResponseRelevancy,
    LLMContextRecall,
    LLMContextPrecisionWithReference
)

files = glob.glob(r"D:\AI_road\Project\backend_projects\NLP_Server\output\*.csv")
top_k = 5
samples = []

async def evaluate_def():
    for file in files:

        df = pd.read_csv(file)

        documents = [int(file[-6:-4])]

        for _, row in df.iterrows():

            query = row["user_input"]
            reference = row["reference"]
            reference_contexts = ast.literal_eval(row["reference_contexts"])

            prediction, chunks = await RAG_responses(query, documents, top_k)

            resp = prediction.get("response", {})

            answer = resp.get("answer", "") if isinstance(resp, dict) else str(resp)

            samples.append({
                "user_input": query,
                "response": answer,
                "reference": reference,
                "reference_contexts": reference_contexts,
                "retrieved_contexts": [
                    c["text"] if isinstance(c, dict) else str(c)
                    for c in chunks
                ]
            })

async def main():
    await evaluate_def()

    if not samples:
        raise ValueError("samples is empty - RAG pipeline did not produce results")

    dataset = Dataset.from_list(samples)

    result = evaluate(
        dataset,
        metrics=[
            Faithfulness(),
            ResponseRelevancy(),
            LLMContextRecall(),
            LLMContextPrecisionWithReference(),
        ],
    )

    print(result)

if __name__ == "__main__":
    asyncio.run(main())