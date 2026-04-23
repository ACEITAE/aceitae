from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

app = FastAPI(
    title="ACEITAÊ API",
    description="Plataforma de venda consignada com ofertas condicionais",
    version="1.0.0"
)

# CORS - Permite o frontend acessar a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Bancos de dados em memória
usuarios_db = []
produtos_db = []
ofertas_db = []
contador_usuario = 1
contador_produto = 1
contador_oferta = 1

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
# ROTA DE CADASTRO
# ==================================================

@app.post("/cadastrar")
def cadastrar(usuario: UsuarioCadastro):
    global contador_usuario
    
    for u in usuarios_db:
        if u["email"] == usuario.email:
            raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    
    if usuario.tipo == "vendedor" and not usuario.cpf:
        raise HTTPException(status_code=400, detail="CPF obrigatório para vendedor")
    
    novo_usuario = {
        "id": contador_usuario,
        "nome": usuario.nome,
        "email": usuario.email,
        "telefone": usuario.telefone,
        "tipo": usuario.tipo,
        "senha": usuario.senha,
        "cpf": usuario.cpf,
        "pix": usuario.pix,
        "endereco": usuario.endereco
    }
    
    usuarios_db.append(novo_usuario)
    contador_usuario += 1
    
    return {"mensagem": "Cadastro realizado!", "usuario_id": novo_usuario["id"], "nome": novo_usuario["nome"]}

# ==================================================
# ROTA DE LOGIN
# ==================================================

@app.post("/login")
def login(usuario: LoginData):
    for u in usuarios_db:
        if u["email"] == usuario.email and u["senha"] == usuario.senha:
            return {"mensagem": f"Bem-vindo, {u['nome']}!", "usuario_id": u["id"], "tipo": u["tipo"]}
    
    raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")

# ==================================================
# ROTA PARA CRIAR PRODUTO
# ==================================================

@app.post("/produtos")
def criar_produto(produto: ProdutoCadastro, vendedor_id: int):
    global contador_produto
    
    vendedor = None
    for u in usuarios_db:
        if u["id"] == vendedor_id and u["tipo"] == "vendedor":
            vendedor = u
            break
    
    if not vendedor:
        raise HTTPException(status_code=404, detail="Vendedor não encontrado")
    
    valor_exposicao = round(produto.valor_pretendido * 1.10, 2)
    
    novo_produto = {
        "id": contador_produto,
        "vendedor_id": vendedor_id,
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
    
    return {"mensagem": "Produto cadastrado!", "produto_id": novo_produto["id"], "produto": novo_produto}

# ==================================================
# ROTA PARA LISTAR PRODUTOS
# ==================================================

@app.get("/produtos")
def listar_produtos(status: str = None):
    produtos_filtrados = []
    
    for p in produtos_db:
        if status is None:
            produtos_filtrados.append(p)
        elif p["status"] == status:
            produtos_filtrados.append(p)
    
    return {"produtos": produtos_filtrados, "total": len(produtos_filtrados)}

# ==================================================
# ROTA PARA APROVAR PRODUTO
# ==================================================

@app.put("/produtos/{produto_id}/aprovar")
def aprovar_produto(produto_id: int):
    for p in produtos_db:
        if p["id"] == produto_id:
            p["status"] = "aprovado"
            return {"mensagem": f"Produto '{p['nome']}' aprovado!"}
    
    raise HTTPException(status_code=404, detail="Produto não encontrado")

# ==================================================
# ROTA PARA FAZER OFERTA
# ==================================================

@app.post("/ofertas")
def fazer_oferta(oferta: OfertaCadastro, comprador_id: int, comprador_nome: str):
    global contador_oferta
    
    produto = None
    for p in produtos_db:
        if p["id"] == oferta.produto_id:
            produto = p
            break
    
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    if produto["status"] != "aprovado":
        raise HTTPException(status_code=400, detail="Produto não está disponível para ofertas")
    
    valor_pretendido = produto["valor_pretendido"]
    valor_oferta = oferta.valor
    
    if valor_oferta >= valor_pretendido:
        status_oferta = "venda_automatica"
        condicional = False
        produto["status"] = "vendido"
        mensagem = f"✅ Venda automática! Produto vendido por R$ {valor_oferta:.2f}"
    else:
        status_oferta = "pendente"
        condicional = True
        mensagem = f"🟡 Oferta condicional enviada! Aguardando vendedor decidir"
    
    nova_oferta = {
        "id": contador_oferta,
        "produto_id": oferta.produto_id,
        "comprador_id": comprador_id,
        "comprador_nome": comprador_nome,
        "valor": valor_oferta,
        "status": status_oferta,
        "condicional": condicional,
        "valor_pretendido": valor_pretendido,
        "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    
    ofertas_db.append(nova_oferta)
    contador_oferta += 1
    
    return {"mensagem": mensagem, "oferta_id": nova_oferta["id"], "status": status_oferta}

# ==================================================
# ROTA PARA VENDEDOR RESPONDER OFERTA
# ==================================================

@app.put("/ofertas/{oferta_id}/responder")
def responder_oferta(oferta_id: int, acao: str):
    oferta = None
    for o in ofertas_db:
        if o["id"] == oferta_id:
            oferta = o
            break
    
    if not oferta:
        raise HTTPException(status_code=404, detail="Oferta não encontrada")
    
    if oferta["status"] != "pendente":
        raise HTTPException(status_code=400, detail="Esta oferta já foi respondida")
    
    valor_oferta = oferta["valor"]
    comissao = round(valor_oferta * 0.10, 2)
    valor_liquido = round(valor_oferta - comissao, 2)
    
    if acao.upper() == "ACEITAÊ":
        oferta["status"] = "aceita"
        for p in produtos_db:
            if p["id"] == oferta["produto_id"]:
                p["status"] = "vendido"
                break
        
        mensagem = f"🎉 ACEITAÊ! Venda confirmada!\n\nValor: R$ {valor_oferta:.2f}\nComissão (10%): R$ {comissao:.2f}\nVocê receberá: R$ {valor_liquido:.2f}"
        
        return {"mensagem": mensagem, "status": "aceita"}
    
    elif acao.upper() == "RECUSAR":
        oferta["status"] = "recusada"
        return {"mensagem": "❌ Oferta recusada", "status": "recusada"}
    
    else:
        raise HTTPException(status_code=400, detail="Ação inválida. Use 'ACEITAÊ' ou 'RECUSAR'")

# ==================================================
# ROTA PARA VENDEDOR VER OFERTAS DOS SEUS PRODUTOS
# ==================================================

@app.get("/vendedor/{vendedor_id}/ofertas")
def ver_ofertas_do_vendedor(vendedor_id: int):
    # Buscar produtos do vendedor
    produtos_do_vendedor = [p for p in produtos_db if p["vendedor_id"] == vendedor_id]
    
    if not produtos_do_vendedor:
        return {"ofertas": [], "total": 0, "mensagem": "Você ainda não tem produtos cadastrados"}
    
    # Lista de IDs dos produtos do vendedor
    produtos_ids = [p["id"] for p in produtos_do_vendedor]
    
    # Buscar ofertas para esses produtos
    ofertas_do_vendedor = [o for o in ofertas_db if o["produto_id"] in produtos_ids]
    
    # Buscar informações dos produtos para cada oferta
    resultado = []
    for oferta in ofertas_do_vendedor:
        produto = next((p for p in produtos_do_vendedor if p["id"] == oferta["produto_id"]), None)
        if produto:
            resultado.append({
                "oferta_id": oferta["id"],
                "produto_id": oferta["produto_id"],
                "produto_nome": produto["nome"],
                "produto_descricao": produto["descricao"],
                "comprador_nome": oferta["comprador_nome"],
                "valor_ofertado": oferta["valor"],
                "valor_pretendido": oferta["valor_pretendido"],
                "status": oferta["status"],
                "condicional": oferta["condicional"],
                "criado_em": oferta["criado_em"]
            })
    
    return {"ofertas": resultado, "total": len(resultado)}

# ==================================================
# ROTA PARA LISTAR USUÁRIOS
# ==================================================

@app.get("/usuarios")
def listar_usuarios():
    usuarios_sem_senha = []
    for u in usuarios_db:
        usuarios_sem_senha.append({
            "id": u["id"],
            "nome": u["nome"],
            "email": u["email"],
            "tipo": u["tipo"]
        })
    return {"usuarios": usuarios_sem_senha}

# ==================================================
# ROTA PRINCIPAL
# ==================================================

@app.get("/")
def root():
    return {
        "mensagem": "ACEITAÊ está no ar! 🎉",
        "slogan": "Você oferta, o vendedor decide, a gente garante."
    }

@app.get("/health")
def health():
    return {"status": "online", "banco": "Memoria"}