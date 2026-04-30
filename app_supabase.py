from fastapi import FastAPI, HTTPException, File, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
from supabase_config import supabase
import uuid

# ==================================================
# CONFIGURAÇÕES
# ==================================================

SECRET_KEY = "SUA_CHAVE_SUPER_SECRETA"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

app = FastAPI(
    title="ACEITAÊ API",
    version="3.0.0"
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
# FUNÇÕES DE SEGURANÇA
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
    existing = supabase.table("usuarios").select("*").eq("email", usuario.email).execute()

    if existing.data:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    data = usuario.dict()
    data["senha"] = hash_senha(usuario.senha)

    result = supabase.table("usuarios").insert(data).execute()

    return {
        "mensagem": "Cadastro realizado!",
        "usuario_id": result.data[0]["id"]
    }

# ==================================================
# LOGIN
# ==================================================

@app.post("/login")
def login(usuario: LoginData):
    result = supabase.table("usuarios").select("*").eq("email", usuario.email).execute()

    if not result.data:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")

    user = result.data[0]

    if not verificar_senha(usuario.senha, user["senha"]):
        raise HTTPException(status_code=401, detail="Senha incorreta")

    token = criar_token({
        "sub": str(user["id"]),
        "nome": user["nome"]
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario_id": user["id"],
        "nome": user["nome"]
    }

# ==================================================
# UPLOAD FOTO
# ==================================================

@app.post("/upload-foto")
async def upload_foto(arquivo: UploadFile = File(...)):

    if arquivo.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Formato inválido")

    conteudo = await arquivo.read()

    if len(conteudo) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Arquivo muito grande")

    nome_arquivo = f"{uuid.uuid4()}.jpg"

    supabase.storage.from_("produtos").upload(
        nome_arquivo,
        conteudo,
        file_options={"content-type": arquivo.content_type}
    )

    url = supabase.storage.from_("produtos").get_public_url(nome_arquivo)

    return {"url": url}

# ==================================================
# CRIAR PRODUTO
# ==================================================

@app.post("/produtos")
def criar_produto(produto: ProdutoCadastro, user_id: int = Depends(get_usuario_logado)):

    vendedor = supabase.table("usuarios").select("*").eq("id", user_id).execute()

    if not vendedor.data:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    valor_exposicao = round(produto.valor_pretendido * 1.10, 2)

    novo_produto = {
        "vendedor_id": user_id,
        "vendedor_nome": vendedor.data[0]["nome"],
        "nome": produto.nome,
        "descricao": produto.descricao,
        "categoria": produto.categoria,
        "valor_pretendido": produto.valor_pretendido,
        "valor_exposicao": valor_exposicao,
        "status": "aguardando_vistoria",
        "fotos": produto.fotos or [],
        "video": produto.video
    }

    result = supabase.table("produtos").insert(novo_produto).execute()

    return {"produto_id": result.data[0]["id"]}

# ==================================================
# LISTAR PRODUTOS
# ==================================================

@app.get("/produtos")
def listar_produtos(status: str = None):
    query = supabase.table("produtos").select("*")

    if status:
        query = query.eq("status", status)

    result = query.execute()
    return {"produtos": result.data}

# ==================================================
# APROVAR PRODUTO
# ==================================================

@app.put("/produtos/{produto_id}/aprovar")
def aprovar_produto(produto_id: int):
    result = supabase.table("produtos").update({"status": "aprovado"}).eq("id", produto_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    return {"mensagem": "Produto aprovado"}

# ==================================================
# FAZER OFERTA
# ==================================================

@app.post("/ofertas")
def fazer_oferta(oferta: OfertaCadastro, user_id: int = Depends(get_usuario_logado)):

    produto = supabase.table("produtos").select("*").eq("id", oferta.produto_id).execute()

    if not produto.data:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    produto = produto.data[0]

    if produto["status"] == "vendido":
        raise HTTPException(status_code=400, detail="Produto já vendido")

    if produto["status"] != "aprovado":
        raise HTTPException(status_code=400, detail="Produto indisponível")

    valor_oferta = oferta.valor
    valor_pretendido = produto["valor_pretendido"]

    if valor_oferta >= valor_pretendido:
        supabase.table("produtos").update({"status": "vendido"}).eq("id", produto["id"]).execute()
        status_oferta = "venda_automatica"
        mensagem = "Venda automática realizada!"
    else:
        status_oferta = "pendente"
        mensagem = "Oferta enviada!"

    nova_oferta = {
        "produto_id": produto["id"],
        "comprador_id": user_id,
        "valor": valor_oferta,
        "status": status_oferta,
        "condicional": valor_oferta < valor_pretendido
    }

    result = supabase.table("ofertas").insert(nova_oferta).execute()

    return {
        "mensagem": mensagem,
        "oferta_id": result.data[0]["id"]
    }

# ==================================================
# ROOT
# ==================================================

@app.get("/")
def root():
    return {
        "mensagem": "ACEITAÊ está no ar!",
        "versao": "3.0.0"
    }

@app.get("/health")
def health():
    return {"status": "online"}
