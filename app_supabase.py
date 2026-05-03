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

# Modelo para CADASTRO (completo)
class UsuarioCadastro(BaseModel):
    nome: str
    email: str
    telefone: str
    tipo: str
    senha: str

# Modelo para LOGIN (apenas email e senha)
class LoginRequest(BaseModel):
    email: str
    senha: str

@app.post("/cadastrar")
def cadastrar(user: UsuarioCadastro):
    existente = supabase.table("usuarios").select("*").eq("email", user.email).execute()
    if existente.data:
        raise HTTPException(400, "E-mail já cadastrado")
    supabase.table("usuarios").insert(user.dict()).execute()
    return {"mensagem": "Cadastro realizado"}

@app.post("/login")
def login(credenciais: LoginRequest):
    resultado = supabase.table("usuarios").select("*").eq("email", credenciais.email).eq("senha", credenciais.senha).execute()
    if not resultado.data:
        raise HTTPException(401, "E-mail ou senha inválidos")
    usuario = resultado.data[0]
    return {
        "usuario_id": usuario["id"],
        "nome": usuario["nome"],
        "tipo": usuario["tipo"]
    }

@app.get("/")
def root():
    return {"mensagem": "ACEITAÊ online"}

@app.get("/health")
def health():
    return {"status": "online"}
