from fastapi import FastAPI, HTTPException, File, UploadFile, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt
from supabase_config import supabase
import uuid

# ================= CONFIG =================
SECRET_KEY = "MUDE_ISSO_NO_RENDER"
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="ACEITAÊ API", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= AUTH =================

def hash_senha(senha):
    return pwd_context.hash(senha)

def verificar_senha(senha, hash):
    return pwd_context.verify(senha, hash)

def criar_token(user_id, nome):
    payload = {
        "sub": str(user_id),
        "nome": nome,
        "exp": datetime.utcnow() + timedelta(hours=2)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_user_id(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Token não enviado")

    token = authorization.replace("Bearer ", "")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except:
        raise HTTPException(status_code=401, detail="Token inválido")

# ================= MODELOS =================

class UsuarioCadastro(BaseModel):
    nome: str
    email: str
    telefone: str
    tipo: str
    senha: str
    cpf: Optional[str] = None
    pix: Optional[str] = None
    endereco: Optional[str] = None

class ProdutoCadastro(BaseModel):
    nome: str
    descricao: str
    categoria: str
    valor_pretendido: float
    fotos: Optional[list] = []
    video: Optional[str] = None

class OfertaCadastro(BaseModel):
    produto_id: int
    valor: float

class LoginData(BaseModel):
    email: str
    senha: str

# ================= CADASTRO =================

@app.post("/cadastrar")
def cadastrar(usuario: UsuarioCadastro):
    existing = supabase.table("usuarios").select("*").eq("email", usuario.email).execute()

    if existing.data:
        raise HTTPException(400, "E-mail já cadastrado")

    data = usuario.dict()
    data["senha"] = hash_senha(usuario.senha)

    result = supabase.table("usuarios").insert(data).execute()

    return {"usuario_id": result.data[0]["id"]}

# ================= LOGIN =================

@app.post("/login")
def login(usuario: LoginData):
    result = supabase.table("usuarios").select("*").eq("email", usuario.email).execute()

    if not result.data:
        raise HTTPException(401, "Usuário não encontrado")

    user = result.data[0]

    if not verificar_senha(usuario.senha, user["senha"]):
        raise HTTPException(401, "Senha incorreta")

    token = criar_token(user["id"], user["nome"])

    return {
        "access_token": token,
        "usuario_id": user["id"],
        "nome": user["nome"],
        "tipo": user["tipo"]
    }

# ================= PRODUTOS =================

@app.post("/produtos")
def criar_produto(produto: ProdutoCadastro, user_id: int = Depends(get_user_id)):

    vendedor = supabase.table("usuarios").select("*").eq("id", user_id).execute()

    if not vendedor.data:
        raise HTTPException(404, "Usuário não encontrado")

    valor_exposicao = round(produto.valor_pretendido * 1.10, 2)

    novo = {
        "vendedor_id": user_id,
        "vendedor_nome": vendedor.data[0]["nome"],
        "nome": produto.nome,
        "descricao": produto.descricao,
        "categoria": produto.categoria,
        "valor_pretendido": produto.valor_pretendido,
        "valor_exposicao": valor_exposicao,
        "status": "aprovado"
    }

    result = supabase.table("produtos").insert(novo).execute()

    return result.data[0]

# ================= LISTAR =================

@app.get("/produtos")
def listar_produtos():
    result = supabase.table("produtos").select("*").execute()
    return {"produtos": result.data}

# ================= OFERTA =================

@app.post("/ofertas")
def oferta(oferta: OfertaCadastro, user_id: int = Depends(get_user_id)):

    produto = supabase.table("produtos").select("*").eq("id", oferta.produto_id).execute()

    if not produto.data:
        raise HTTPException(404, "Produto não encontrado")

    produto = produto.data[0]

    if produto["status"] == "vendido":
        raise HTTPException(400, "Produto já vendido")

    if oferta.valor >= produto["valor_pretendido"]:
        supabase.table("produtos").update({"status": "vendido"}).eq("id", produto["id"]).execute()
        status_oferta = "venda_automatica"
    else:
        status_oferta = "pendente"

    nova = {
        "produto_id": produto["id"],
        "comprador_id": user_id,
        "valor": oferta.valor,
        "status": status_oferta
    }

    result = supabase.table("ofertas").insert(nova).execute()

    return {"status": status_oferta}

# ================= ROOT =================

@app.get("/")
def root():
    return {"msg": "ACEITAÊ online 🚀"}
