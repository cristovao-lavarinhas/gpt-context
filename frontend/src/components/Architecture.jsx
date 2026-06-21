import "./Architecture.css";

function Section({ icon, title, children }) {
  return (
    <section className="arch-section">
      <h2 className="arch-section-title">
        <span className="material-symbols-outlined">{icon}</span> {title}
      </h2>
      <div className="arch-section-body">{children}</div>
    </section>
  );
}

function Card({ icon, title, children }) {
  return (
    <div className="arch-card">
      <div className="arch-card-head">
        <span className="arch-card-icon">
          <span className="material-symbols-outlined">{icon}</span>
        </span>
        <h3 className="arch-card-title">{title}</h3>
      </div>
      <div className="arch-card-body">{children}</div>
    </div>
  );
}

export default function Architecture({ onBack }) {
  return (
    <div className="architecture">
      <button className="arch-back" onClick={onBack}>
        <span className="material-symbols-outlined">arrow_back</span> Voltar ao chat
      </button>

      <header className="arch-header">
        <h1>
          <span className="material-symbols-outlined">settings</span> Arquitetura do Sistema
        </h1>
        <p>
          <strong>SportSphere</strong> — Assistente Desportivo com RAG Local
        </p>
      </header>

      <Section icon="lan" title="Como Funciona (Frontend + Backend)">
        <p className="arch-intro-text">
          A app é dividida em dois processos separados que correm em paralelo. O <strong>frontend</strong> (React)
          só desenha a interface no browser — não tem permissões para aceder a ficheiros locais ou chamar o Ollama
          diretamente. Por isso, toda a lógica (RAG, OCR, chamadas ao modelo) vive no <strong>backend</strong> (FastAPI),
          que o frontend contacta via pedidos HTTP.
        </p>

        <div className="arch-flow">
          <div className="arch-flow-node">
            <span className="material-symbols-outlined">browser_updated</span>
            <span>React<br /><small>frontend :5173</small></span>
          </div>
          <span className="arch-flow-arrow material-symbols-outlined">arrow_forward</span>
          <div className="arch-flow-node">
            <span className="material-symbols-outlined">dns</span>
            <span>FastAPI<br /><small>backend :8000</small></span>
          </div>
          <span className="arch-flow-arrow material-symbols-outlined">arrow_forward</span>
          <div className="arch-flow-node">
            <span className="material-symbols-outlined">memory</span>
            <span>Ollama<br /><small>modelo local</small></span>
          </div>
        </div>

        <p className="arch-intro-note">
          Por isso é preciso correr os dois: <code>uvicorn main:app</code> (backend) e <code>npm run dev</code> (frontend),
          cada um no seu terminal.
        </p>
      </Section>

      <Section icon="devices" title="Interface do Utilizador">
        <div className="arch-grid arch-grid-2">
          <Card icon="chat_bubble" title="Chat Interface">
            <ul>
              <li>Input de texto com streaming</li>
              <li>Histórico persistente em JSON</li>
              <li>Sugestões contextuais inteligentes</li>
            </ul>
          </Card>
          <Card icon="attach_file" title="Upload de Ficheiros">
            <ul>
              <li>PDF, DOCX, TXT, CSV, JSON</li>
              <li>Imagens (PNG, JPG, GIF, TIFF)</li>
              <li>OCR integrado automático</li>
            </ul>
          </Card>
        </div>
      </Section>

      <Section icon="sync" title="Pipeline de Processamento">
        <div className="arch-grid arch-grid-3">
          <Card icon="search" title="Deteção de Desporto">
            <p>Keywords em PT/EN detetam o desporto e filtram a pasta correta de documentos.</p>
          </Card>
          <Card icon="document_scanner" title="OCR Engine">
            <p className="arch-card-label">Prioridade:</p>
            <ol>
              <li>Tesseract (offline, rápido)</li>
              <li>Ollama Vision (local)</li>
              <li>Mensagem de erro com instruções</li>
            </ol>
          </Card>
          <Card icon="description" title="Parser Documentos">
            <p>pypdf para PDFs • python-docx para Word • Leitura direta para texto/CSV</p>
          </Card>
        </div>
      </Section>

      <Section icon="hub" title="RAG — Retrieval-Augmented Generation">
        <div className="arch-grid arch-grid-3">
          <Card icon="content_cut" title="Chunking">
            <p>Texto dividido em blocos de 900 caracteres com 150 de sobreposição para contexto otimizado.</p>
          </Card>
          <Card icon="sell" title="Tokenização + Scoring">
            <p>Normalização Unicode, bigrams, cobertura léxica cruzada entre português ↔ inglês.</p>
          </Card>
          <Card icon="translate" title="Tradução Bilingue">
            <p>Query traduzida PT→EN via Ollama para expandir tokens de busca em docs ingleses.</p>
          </Card>
        </div>
      </Section>

      <Section icon="smart_toy" title="Geração de Resposta">
        <div className="arch-grid arch-grid-2">
          <Card icon="smart_toy" title="Ollama LLM (Local)">
            <ul>
              <li>Modelo: qwen2.5:3b (ou outro configurado)</li>
              <li>System prompt dinâmico com contexto RAG</li>
              <li>Regulamentos desportivos como fallback</li>
              <li>Streaming via SSE para UX fluida</li>
            </ul>
          </Card>
          <Card icon="folder" title="local-docs/">
            <ul>
              <li><code>soccer/</code> — Regras e eventos de futebol</li>
              <li><code>formula1/</code> — F1, pneus, estratégias</li>
              <li><code>basketball/</code> — NBA, FIBA, regulamentos</li>
              <li><code>tennis/</code> — Grand Slams, rankings</li>
              <li><code>olympics/</code> — Atletismo e eventos</li>
              <li>Indexados com cache de 60s</li>
            </ul>
          </Card>
        </div>
      </Section>

      <Section icon="construction" title="Tech Stack">
        <div className="arch-grid arch-grid-4 arch-tech-stack">
          <div>
            <p className="arch-tech-col-title">Backend</p>
            <p>Python 3.11+</p>
            <p>FastAPI</p>
            <p>Ollama</p>
          </div>
          <div>
            <p className="arch-tech-col-title">Frontend</p>
            <p>React</p>
            <p>Vite</p>
          </div>
          <div>
            <p className="arch-tech-col-title">Document Parsing</p>
            <p>pypdf</p>
            <p>python-docx</p>
            <p>Pillow</p>
          </div>
          <div>
            <p className="arch-tech-col-title">OCR</p>
            <p>Tesseract</p>
            <p>pytesseract</p>
            <p>Ollama Vision</p>
          </div>
          <div>
            <p className="arch-tech-col-title">Storage</p>
            <p>JSON (chat history)</p>
            <p>Local-docs (offline)</p>
          </div>
        </div>
      </Section>

      <Section icon="push_pin" title="Notas de Arquitetura">
        <div className="arch-grid arch-grid-2">
          <Card icon="lock" title="100% Offline">
            <p>Nenhum dado sai do computador. Tudo corre localmente via Ollama.</p>
          </Card>
          <Card icon="layers" title="OCR Cascata">
            <p>Tesseract → Ollama Vision → mensagem de erro com instruções</p>
          </Card>
          <Card icon="bar_chart" title="RAG Scoring">
            <p>65% similaridade léxica • 15% cobertura • 15% bigrams • 5% fonte</p>
          </Card>
          <Card icon="save" title="Persistência">
            <p>Histórico guardado em <code>chat_history.json</code> entre sessões</p>
          </Card>
        </div>
      </Section>
    </div>
  );
}