from supabase import create_client, Client

SUPABASE_URL = "https://gkmzczraggmjeizszenh.supabase.co"
SUPABASE_KEY = "sb_publishable_kmIUj96K0A_-qNOY5E4_9g_hVNssgix"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("✅ Conectado ao Supabase!")