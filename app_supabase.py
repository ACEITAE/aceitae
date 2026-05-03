from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase_config import supabase

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Usuario(BaseModel):
    nome: str
    email: str
    telefone: str
    tipo: str
    senha: str

@app.post("/cadastrar")
def cadastrar(user: Usuario):
    existente = supabase.table("usuarios").select("*").eq("email", user.email).execute()
    if existente.data:
        raise HTTPException(400, "E-mail já cadastrado")
    supabase.table("usuarios").insert(user.dict()).execute()
    return {"mensagem": "Cadastro realizado"}

@app.post("/login")
def login(user: Usuario):
    result = supabase.table("usuarios").select("*").eq("email", user.email).eq("senha", user.senha).execute()
    if not result.data:
        raise HTTPException(401, "Credenciais inválidas")
    return {"mensagem": "Login ok", "nome": result.data[0]["nome"], "tipo": result.data[0]["tipo"]}

@app.get("/health")
def health():
    return {"status": "online"}
