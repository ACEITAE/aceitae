from supabase import create_client, Client
import os

# ==================================================
# CONFIGURAÇÃO
# ==================================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# ==================================================
# VALIDAÇÃO
# ==================================================

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "❌ SUPABASE_URL e SUPABASE_KEY não configuradas.\n"
        "👉 Configure no Render ou no .env local."
    )

# ==================================================
# CLIENTE
# ==================================================

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    raise RuntimeError(f"Erro ao conectar no Supabase: {str(e)}")

# ==================================================
# LOG CONTROLADO
# ==================================================

if os.getenv("ENV") != "production":
    print("✅ Supabase conectado com sucesso")
