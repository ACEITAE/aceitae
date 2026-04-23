from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from supabase_config import supabase

app = FastAPI(
    title="ACEITAÊ API",
    description="Plataforma de venda consignada com ofertas condicionais",
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
    try:
        existing = supabase.table("usuarios").select("*").eq("email", usuario.email).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="E-mail já cadastrado")
        
        data = usuario.dict()
        result = supabase.table("usuarios").insert(data).execute()
        
        return {
            "mensagem": "Cadastro realizado!",
            "usuario_id": result.data[0]["id"],
            "nome": result.data[0]["nome"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================================================
# ROTA DE LOGIN
# ==================================================

# ==================================================
# ROTA DE LOGIN (CORRIGIDA)
# ==================================================

@app.post("/login")
def login(usuario: LoginData):
    try:
        result = supabase.table("usuarios").select("*").eq("email", usuario.email).eq("senha", usuario.senha).execute()
        
        if not result.data:
            raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")
        
        user = result.data[0]
        
        return {
            "mensagem": f"Bem-vindo, {user['nome']}!",
            "usuario_id": user["id"],
            "nome": user["nome"],
            "email": user["email"],
            "tipo": user["tipo"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================================================
# ROTA PARA CRIAR PRODUTO
# ==================================================

@app.post("/produtos")
def criar_produto(produto: ProdutoCadastro, vendedor_id: int):
    try:
        vendedor = supabase.table("usuarios").select("*").eq("id", vendedor_id).eq("tipo", "vendedor").execute()
        if not vendedor.data:
            raise HTTPException(status_code=404, detail="Vendedor não encontrado")
        
        valor_exposicao = round(produto.valor_pretendido * 1.10, 2)
        
        novo_produto = {
            "vendedor_id": vendedor_id,
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
        
        return {
            "mensagem": "Produto cadastrado!",
            "produto_id": result.data[0]["id"],
            "produto": result.data[0]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================================================
# ROTA PARA LISTAR PRODUTOS
# ==================================================

@app.get("/produtos")
def listar_produtos(status: str = None):
    query = supabase.table("produtos").select("*")
    
    if status:
        query = query.eq("status", status)
    
    result = query.execute()
    return {"produtos": result.data, "total": len(result.data)}

# ==================================================
# ROTA PARA APROVAR PRODUTO
# ==================================================

@app.put("/produtos/{produto_id}/aprovar")
def aprovar_produto(produto_id: int):
    result = supabase.table("produtos").update({"status": "aprovado"}).eq("id", produto_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    return {"mensagem": f"Produto '{result.data[0]['nome']}' aprovado!"}

# ==================================================
# ROTA PARA FAZER OFERTA
# ==================================================

@app.post("/ofertas")
def fazer_oferta(oferta: OfertaCadastro, comprador_id: int, comprador_nome: str):
    try:
        produto = supabase.table("produtos").select("*").eq("id", oferta.produto_id).execute()
        if not produto.data:
            raise HTTPException(status_code=404, detail="Produto não encontrado")
        
        produto = produto.data[0]
        
        if produto["status"] != "aprovado":
            raise HTTPException(status_code=400, detail="Produto não está disponível para ofertas")
        
        valor_pretendido = produto["valor_pretendido"]
        valor_oferta = oferta.valor
        
        if valor_oferta >= valor_pretendido:
            status_oferta = "venda_automatica"
            condicional = False
            supabase.table("produtos").update({"status": "vendido"}).eq("id", oferta.produto_id).execute()
            mensagem = f"✅ Venda automática! Produto vendido por R$ {valor_oferta:.2f}"
        else:
            status_oferta = "pendente"
            condicional = True
            mensagem = f"🟡 Oferta condicional enviada! Aguardando vendedor decidir"
        
        nova_oferta = {
            "produto_id": oferta.produto_id,
            "comprador_id": comprador_id,
            "comprador_nome": comprador_nome,
            "valor": valor_oferta,
            "status": status_oferta,
            "condicional": condicional,
            "valor_pretendido": valor_pretendido
        }
        
        result = supabase.table("ofertas").insert(nova_oferta).execute()
        
        return {
            "mensagem": mensagem,
            "oferta_id": result.data[0]["id"],
            "status": status_oferta
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================================================
# ROTA PARA VENDEDOR RESPONDER OFERTA
# ==================================================

@app.put("/ofertas/{oferta_id}/responder")
def responder_oferta(oferta_id: int, acao: str):
    try:
        oferta = supabase.table("ofertas").select("*").eq("id", oferta_id).execute()
        if not oferta.data:
            raise HTTPException(status_code=404, detail="Oferta não encontrada")
        
        oferta = oferta.data[0]
        
        if oferta["status"] != "pendente":
            raise HTTPException(status_code=400, detail="Esta oferta já foi respondida")
        
        valor_oferta = oferta["valor"]
        comissao = round(valor_oferta * 0.10, 2)
        valor_liquido = round(valor_oferta - comissao, 2)
        
        if acao.upper() == "ACEITAÊ":
            supabase.table("ofertas").update({"status": "aceita"}).eq("id", oferta_id).execute()
            supabase.table("produtos").update({"status": "vendido"}).eq("id", oferta["produto_id"]).execute()
            
            mensagem = f"🎉 ACEITAÊ! Venda confirmada!\n\nValor: R$ {valor_oferta:.2f}\nComissão (10%): R$ {comissao:.2f}\nVocê receberá: R$ {valor_liquido:.2f}"
            
            return {"mensagem": mensagem, "status": "aceita"}
        
        elif acao.upper() == "RECUSAR":
            supabase.table("ofertas").update({"status": "recusada"}).eq("id", oferta_id).execute()
            return {"mensagem": "❌ Oferta recusada", "status": "recusada"}
        
        else:
            raise HTTPException(status_code=400, detail="Ação inválida. Use 'ACEITAÊ' ou 'RECUSAR'")
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================================================
# ROTA PARA VENDEDOR VER OFERTAS
# ==================================================

@app.get("/vendedor/{vendedor_id}/ofertas")
def ver_ofertas_do_vendedor(vendedor_id: int):
    try:
        produtos = supabase.table("produtos").select("*").eq("vendedor_id", vendedor_id).execute()
        
        if not produtos.data:
            return {"ofertas": [], "total": 0}
        
        produtos_ids = [p["id"] for p in produtos.data]
        ofertas = supabase.table("ofertas").select("*").in_("produto_id", produtos_ids).execute()
        
        resultado = []
        for oferta in ofertas.data:
            produto = next((p for p in produtos.data if p["id"] == oferta["produto_id"]), None)
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
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================================================
# ROTA PARA LISTAR USUÁRIOS
# ==================================================

@app.get("/usuarios")
def listar_usuarios():
    result = supabase.table("usuarios").select("id, nome, email, tipo").execute()
    return {"usuarios": result.data}

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
    return {"status": "online", "banco": "Supabase"}