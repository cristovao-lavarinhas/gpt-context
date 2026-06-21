const API_BASE = "http://127.0.0.1:8000";

export async function fetchHistory() {
  const res = await fetch(`${API_BASE}/api/history`);
  if (!res.ok) throw new Error("Falha ao carregar histórico");
  return res.json();
}

export async function deleteChat(chatId) {
  const res = await fetch(`${API_BASE}/api/history/${chatId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Falha ao apagar conversa");
  return res.json();
}

export async function uploadFile(file) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/api/upload`, { method: "POST", body: formData });
  if (!res.ok) throw new Error("Falha no upload");
  return res.json();
}

export async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    if (!res.ok) return { ollama_available: false };
    return await res.json();
  } catch {
    return { ollama_available: false };
  }
}

export async function fetchDocsLibrary() {
  const res = await fetch(`${API_BASE}/api/docs`);
  if (!res.ok) throw new Error("Falha ao carregar biblioteca de documentos");
  return res.json();
}

export async function uploadDoc(folder, file) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/api/docs/${folder}/upload`, { method: "POST", body: formData });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Falha no upload");
  }
  return res.json();
}

export async function deleteDoc(folder, filename) {
  const res = await fetch(`${API_BASE}/api/docs/${folder}/${encodeURIComponent(filename)}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Falha ao apagar ficheiro");
  return res.json();
}

export async function createDocFolder(name) {
  const res = await fetch(`${API_BASE}/api/docs/folders`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Falha ao criar pasta");
  }
  return res.json();
}

export async function deleteDocFolder(folder) {
  const res = await fetch(`${API_BASE}/api/docs/folders/${encodeURIComponent(folder)}`, { method: "DELETE" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Falha ao apagar pasta");
  }
  return res.json();
}

/**
 * Streams a chat response from the backend using Server-Sent Events.
 *
 * @param {object} params
 * @param {Array<{role:string, content:string}>} params.messages - full conversation incl. latest user msg
 * @param {number|null} params.chatId
 * @param {string} params.uploadedFileContent
 * @param {(token: string) => void} params.onToken
 * @param {(folders: string[], sources: string[]) => void} params.onScope
 * @param {(payload: {chat_id:number, title:string}) => void} params.onDone
 * @param {(err: Error) => void} params.onError
 */
export function streamChat({
  messages,
  chatId,
  uploadedFileContent = "",
  onToken,
  onScope,
  onDone,
  onError,
}) {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages,
          chat_id: chatId,
          uploaded_file_content: uploadedFileContent,
        }),
        signal: controller.signal,
      });

      if (!res.ok || !res.body) {
        throw new Error("Falha ao contactar o backend.");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";

        for (const frame of frames) {
          const lines = frame.split("\n");
          let event = "message";
          let data = "";
          for (const line of lines) {
            if (line.startsWith("event: ")) event = line.slice(7).trim();
            if (line.startsWith("data: ")) data = line.slice(6);
          }
          if (!data) continue;
          const parsed = JSON.parse(data);

          if (event === "token" && onToken) onToken(parsed.text);
          if (event === "scope" && onScope) onScope(parsed.folders, parsed.sources, parsed.excerpts);
          if (event === "done" && onDone) onDone(parsed);
        }
      }
    } catch (err) {
      if (err.name === "AbortError") {
        if (onDone) onDone({ aborted: true });
      } else if (onError) {
        onError(err);
      }
    }
  })();

  // O caller guarda esta função e chama-a para interromper o stream.
  return () => controller.abort();
}
