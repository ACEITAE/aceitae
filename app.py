from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt, JWTError
import os

# ==================================================
# CONFIG
# ==================================================

SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

app = FastAPI(
    title="ACEITAÊ API",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================================================
# BANCO (MEMÓRIA)
# ==================================================

usuarios_db = []
produtos_db = []
ofertas_db = []

contador_usuario = 1
contador_produto = 1
contador_oferta = 1

# ==================================================
# SEGURANÇA
# ==================================================

def hash_senha(senha):
    return pwd_context.hash(senha)

def verificar_senha(senha, hash):
    return pwd_context.verify(senha, hash)

def criar_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_usuario_logado(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload.get("sub"))
    except:
        raise HTTPException(status_code=401, detail="Token inválido")

# ==================================================
# MODELOS
# ==================================================

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

# ==================================================
# CADASTRO
# ==================================================

@app.post("/cadastrar")
def cadastrar(usuario: UsuarioCadastro):
    global contador_usuario

    for u in usuarios_db:
        if u["email"] == usuario.email:
            raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    if usuario.tipo == "vendedor" and not usuario.cpf:
        raise HTTPException(status_code=400, detail="CPF obrigatório")

    novo_usuario = {
        "id": contador_usuario,
        "nome": usuario.nome,
        "email": usuario.email,
        "telefone": usuario.telefone,
        "tipo": usuario.tipo,
        "senha": hash_senha(usuario.senha),
        "cpf": usuario.cpf,
        "pix": usuario.pix,
        "endereco": usuario.endereco
    }

    usuarios_db.append(novo_usuario)
    contador_usuario += 1

    return {"mensagem": "Cadastro realizado!", "usuario_id": novo_usuario["id"]}

# ==================================================
# LOGIN
# ==================================================

@app.post("/login")
def login(usuario: LoginData):
    for u in usuarios_db:
        if u["email"] == usuario.email:
            if verificar_senha(usuario.senha, u["senha"]):
                token = criar_token({
                    "sub": str(u["id"]),
                    "nome": u["nome"]
                })

                return {
                    "access_token": token,
                    "token_type": "bearer",
                    "usuario_id": u["id"],
                    "nome": u["nome"],
                    "tipo": u["tipo"]
                }

    raise HTTPException(status_code=401, detail="Credenciais inválidas")

# ==================================================
# CRIAR PRODUTO (PROTEGIDO)
# ==================================================

@app.post("/produtos")
def criar_produto(produto: ProdutoCadastro, user_id: int = Depends(get_usuario_logado)):
    global contador_produto

    vendedor = next((u for u in usuarios_db if u["id"] == user_id), None)

    if not vendedor:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    valor_exposicao = round(produto.valor_pretendido * 1.10, 2)

    novo_produto = {
        "id": contador_produto,
        "vendedor_id": user_id,
        "vendedor_nome": vendedor["nome"],
        "nome": produto.nome,
        "descricao": produto.descricao,
        "categoria": produto.categoria,
        "valor_pretendido": produto.valor_pretendido,
        "valor_exposicao": valor_exposicao,
        "status": "aguardando_vistoria",
        "fotos": produto.fotos or [],
        "video": produto.video,
        "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M")
    }

    produtos_db.append(novo_produto)
    contador_produto += 1

    return {"produto_id": novo_produto["id"]}

# ==================================================
# LISTAR PRODUTOS
# ==================================================

@app.get("/produtos")
def listar_produtos(status: str = None):
    produtos = [p for p in produtos_db if status is None or p["status"] == status]
    return {"produtos": produtos}

# ==================================================
# APROVAR PRODUTO
# ==================================================

@app.put("/produtos/{produto_id}/aprovar")
def aprovar_produto(produto_id: int):
    for p in produtos_db:
        if p["id"] == produto_id:
            p["status"] = "aprovado"
            return {"mensagem": "Produto aprovado"}

    raise HTTPException(status_code=404, detail="Produto não encontrado")

# ==================================================
# FAZER OFERTA (PROTEGIDO)
# ==================================================

@app.post("/ofertas")
def fazer_oferta(oferta: OfertaCadastro, user_id: int = Depends(get_usuario_logado)):
    global contador_oferta

    produto = next((p for p in produtos_db if p["id"] == oferta.produto_id), None)

    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    if produto["status"] == "vendido":
        raise HTTPException(status_code=400, detail="Produto já vendido")

    if produto["status"] != "aprovado":
        raise HTTPException(status_code=400, detail="Produto indisponível")

    valor_oferta = oferta.valor
    valor_pretendido = produto["valor_pretendido"]

    if valor_oferta >= valor_pretendido:
        produto["status"] = "vendido"
        status_oferta = "venda_automatica"
        mensagem = "Venda automática realizada!"
    else:
        status_oferta = "pendente"
        mensagem = "Oferta enviada!"

    nova_oferta = {
        "id": contador_oferta,
        "produto_id": produto["id"],
        "comprador_id": user_id,
        "valor": valor_oferta,
        "status": status_oferta,
        "condicional": valor_oferta < valor_pretendido,
        "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M")
    }

    ofertas_db.append(nova_oferta)
    contador_oferta += 1

    return {"mensagem": mensagem, "status": status_oferta}

# ==================================================
# ROOT
# ==================================================

@app.get("/")
def root():
    return {"mensagem": "ACEITAÊ rodando 🚀"}

@app.get("/health")
def health():
    return {"status": "online"}
