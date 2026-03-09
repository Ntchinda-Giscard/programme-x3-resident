
import os
from typing import List, Optional
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.prompts import ChatPromptTemplate
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
import logging

logger = logging.getLogger(__name__)

class SageRAG:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("No OPENAI_API_KEY found. RAG will use mock components.")
            self.llm = None
            self.vector_store = None
        else:
            self.embeddings = OpenAIEmbeddings()
            self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
            self.vector_store = None
            self.db_path = "faiss_index"
            self.load_index()

    def load_index(self):
        if os.path.exists(self.db_path):
            try:
                self.vector_store = FAISS.load_local(
                    self.db_path, 
                    self.embeddings, 
                    allow_dangerous_deserialization=True
                )
                logger.info("FAISS index loaded successfully.")
            except Exception as e:
                logger.error(f"Error loading FAISS index: {e}")
        else:
            logger.info("No FAISS index found. Initialize it by crawling docs.")

    def add_documents(self, docs: List[Document]):
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(docs)
        if self.vector_store:
            self.vector_store.add_documents(splits)
        else:
            self.vector_store = FAISS.from_documents(splits, self.embeddings)
        
        self.vector_store.save_local(self.db_path)
        logger.info(f"Added {len(splits)} chunks to vector store.")

    async def query(self, user_query: str, chat_history: List[dict] = None) -> str:
        if not self.llm:
            return "⚠️ Mode Démo : Clé API manquante. Veuillez configurer OPENAI_API_KEY dans le fichier .env."

        if not self.vector_store:
            return "Je n'ai pas encore de documentation indexée. Veuillez lancer le crawl des données Sage X3 d'abord."

        # Retrieval - Deep search (k=20 for broad context, user asked for "100 searches" which might mean deep context)
        # We'll retrieve 30 chunks to be comprehensive
        docs = self.vector_store.similarity_search(user_query, k=30)
        context = "\n\n".join([doc.page_content for doc in docs])

        system_prompt = """Tu es l'assistant expert Sage X3. 
Ta mission est de fournir des réponses extrêmement détaillées, structurées et professionnelles.
Utilise le CONTEXTE ci-dessous pour répondre à la question. 
Si le contexte ne contient pas l'information, dis-le poliment mais essaie d'aider avec tes connaissances générales sur l'ERP Sage X3 si possible, en précisant que c'est une connaissance générale.

RÈGLES DE RÉPONSE :
1. Utilise un formatage Markdown riche (titres, listes, gras).
2. Cite des noms de champs, de tables ou de paramètres Sage X3 si possible (ex: APPPOH, POHSIG).
3. Sois proactif : si l'utilisateur pose une question sur un workflow, explique les étapes de paramétrage, les conditions et les pièges à éviter.
4. Si la question est simple (ex: "Bonjour"), réponds chaleureusement sans forcément faire une analyse technique profonde, mais propose ton aide sur Sage X3.
5. PRENDS EN COMPTE L'HISTORIQUE pour garder le fil de la conversation.

CONTEXTE :
{context}
"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            # Chat history can be added here
            ("human", "{question}")
        ])

        chain = prompt | self.llm
        
        response = await chain.ainvoke({
            "context": context,
            "question": user_query
        })

        return response.content

# Singleton instance
rag_instance = SageRAG()
