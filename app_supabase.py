from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase_config import supabase
from typing import Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# MODELOS SEPARADOS (ESSENCIAL)
# ============================================

class UsuarioCadastro(BaseModel):
    nome: str
    email: str
    telefone: str
    tipo: str
    senha: str
    cpf: Optional[str] = None
    pix: Optional[str] = None
    endereco: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    senha: str

# ============================================
# ROTAS
# ============================================

@app.post("/cadastrar")
def cadastrar(user: UsuarioCadastro):
    # Verifica se e-mail já existe
    existente = supabase.table("usuarios").select("*").eq("email", user.email).execute()
    if existente.data:
        raise HTTPException(400, "E-mail já cadastrado")

    # Insere no banco
    data = user.dict()
    supabase.table("usuarios").insert(data).execute()
    return {"mensagem": "Cadastro realizado com sucesso"}

@app.post("/login")
def login(credenciais: LoginRequest):
    # Busca usuário por email e senha
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
