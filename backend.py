import asyncio
import sys
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import os
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain.chains import RetrievalQA
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, UnstructuredWordDocumentLoader, TextLoader


DATA_PATH = r"CompanyData"
CHROMA_PATH = "chroma_db"
GOOGLE_API_KEY = "AIzaSyDZOJJdHiBxIirgIVaDaeb0T3YaxHJl_zM"


async def get_rag_response(query: str):
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=GOOGLE_API_KEY
    )
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", google_api_key=GOOGLE_API_KEY, temperature=0.2)
    retriever = db.as_retriever(search_kwargs={"k": 1000})
    qa_chain = RetrievalQA.from_chain_type(
        llm,
        retriever=retriever,
        return_source_documents=True
    )
    result = await qa_chain.ainvoke({"query": query})
    return result['result']


app = FastAPI()

class Query(BaseModel):
    query: str

class Answer(BaseModel):
    answer: str


@app.post("/ask", response_model=Answer)
async def handle_question(request: Query):
    user_query = request.query
    response_text = await get_rag_response(user_query)
    return {"answer": response_text}