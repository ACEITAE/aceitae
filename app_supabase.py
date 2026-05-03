from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase_config import supabase
from typing import Optional

app = FastAPI()

# ✅ CORS livre
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UsuarioCadastro(BaseModel):
    nome: str
    email: str
    telefone: str
    tipo: str
    senha: str
    cpf: Optional[str] = None
    pix: Optional[str] = None
    endereco: Optional[str] = None

class LoginData(BaseModel):
    email: str
    senha: str

@app.post("/cadastrar")
def cadastrar(usuario: UsuarioCadastro):
    existing = supabase.table("usuarios").select("*").eq("email", usuario.email).execute()
    if existing.data:
        raise HTTPException(400, detail="E-mail já cadastrado")

    data = usuario.dict()
    data["senha"] = usuario.senha  # ⚠️ sem hash por enquanto (para testar)
    result = supabase.table("usuarios").insert(data).execute()
    return {"mensagem": "Cadastro realizado!", "usuario_id": result.data[0]["id"]}

@app.post("/login")
def login(usuario: LoginData):
    result = supabase.table("usuarios").select("*").eq("email", usuario.email).execute()
    if not result.data:
        raise HTTPException(401, detail="Usuário não encontrado")

    user = result.data[0]
    if user["senha"] != usuario.senha:
        raise HTTPException(401, detail="Senha incorreta")

    return {
        "usuario_id": user["id"],
        "nome": user["nome"],
        "tipo": user["tipo"]
    }

@app.get("/health")
def health():
    return {"status": "online"}
