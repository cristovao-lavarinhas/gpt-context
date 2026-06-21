"""
Testa o endpoint /api/chat diretamente via HTTP, sem passar pelo frontend.
Isto isola se o problema está no backend (rag.py/main.py/Ollama) ou no
frontend (api.js/ChatPanel.jsx).

Correr (com o uvicorn já a correr noutro terminal):
    python test_chat_endpoint.py
"""

import json
import time
import requests

url = "http://127.0.0.1:8000/api/chat"
payload = {
    "messages": [{"role": "user", "content": "Quais são as principais regras do futebol?"}],
    "chat_id": None,
    "uploaded_file_content": "",
}

print("A enviar pedido para", url)
print("Payload:", json.dumps(payload, ensure_ascii=False))
print("-" * 70)

start = time.time()
try:
    with requests.post(url, json=payload, stream=True, timeout=60) as resp:
        print("Status:", resp.status_code)
        print("Headers:", dict(resp.headers))
        print("-" * 70)

        if resp.status_code != 200:
            print("ERRO — corpo da resposta:")
            print(resp.text)
        else:
            full_text = ""
            for line in resp.iter_lines(decode_unicode=True):
                if line:
                    elapsed = time.time() - start
                    print(f"[{elapsed:6.2f}s] {line}")
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if "text" in data:
                                full_text += data["text"]
                        except Exception:
                            pass

            print("-" * 70)
            print("TEXTO COMPLETO RECEBIDO:")
            print(full_text or "(VAZIO — nenhum token recebido)")

except requests.exceptions.Timeout:
    print(f"⏱️  TIMEOUT ao fim de {time.time() - start:.1f}s — o pedido nunca respondeu.")
except Exception as e:
    print(f"❌ ERRO: {type(e).__name__}: {e}")

print(f"\nTempo total: {time.time() - start:.1f}s")