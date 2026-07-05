import glob
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from ragas.testset import TestsetGenerator
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from dotenv import load_dotenv
from ragas.run_config import RunConfig
import os

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Embedding
embedding = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

# LLM
llm = ChatOllama(
    model="qwen2.5:7b",
    temperature=0,
    format="json"
)

# Wrapper Ragas
ragas_llm = LangchainLLMWrapper(llm)
ragas_embedding = LangchainEmbeddingsWrapper(embedding)

# Generator
generator = TestsetGenerator(
    llm=ragas_llm,
    embedding_model=ragas_embedding,
)

pdfs = glob.glob(r"D:\AI_road\Project\backend_projects\NLP_Server\docs\*.pdf")

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100
)

os.makedirs("output", exist_ok=True)
for pdf in pdfs[7:]:

    print(f"Processing {os.path.basename(pdf)}")

    docs = PyPDFLoader(pdf).load()
    docs = splitter.split_documents(docs)
    docs = docs[:50]

    dataset = generator.generate_with_langchain_docs(docs, testset_size=20)

    pdf_name = os.path.splitext(os.path.basename(pdf))[0]

    df = dataset.to_pandas()

    df.to_csv(
        f"./output/{pdf_name}_testset.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print(f"Done: {pdf_name}")