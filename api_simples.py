from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase_config import supabase

app = FastAPI()

# CORS totalmente aberto
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

class LoginData(BaseModel):
    email: str
    senha: str

@app.post("/cadastrar")
def cadastrar(user: Usuario):
    existe = supabase.table("usuarios").select("*").eq("email", user.email).execute()
    if existe.data:
        raise HTTPException(400, "Email já cadastrado")
    supabase.table("usuarios").insert(user.dict()).execute()
    return {"ok": True, "mensagem": "Cadastro realizado"}

@app.post("/login")
def login(credenciais: LoginData):
    resultado = supabase.table("usuarios").select("*").eq("email", credenciais.email).eq("senha", credenciais.senha).execute()
    if not resultado.data:
        raise HTTPException(401, "Email ou senha inválidos")
    user = resultado.data[0]
    return {"id": user["id"], "nome": user["nome"], "tipo": user["tipo"]}

@app.get("/")
def root():
    return {"status": "ACEITAÊ online"}

@app.get("/health")
def health():
    return {"status": "ok"}
