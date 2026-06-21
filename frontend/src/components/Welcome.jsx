import "./Welcome.css";
import InputBar from "./InputBar.jsx";

const SUGGESTIONS = [
  { title: "Regras da NBA", label: "e detalhes da FIBA", prompt: "Quais são as principais regras do basquetebol da NBA e da FIBA?" },
  { title: "Torneios Grand Slam", label: "como funcionam", prompt: "Explica como funcionam os torneios Grand Slam de ténis." },
  { title: "Atletismo Olímpico", label: "recordes mundiais", prompt: "Quais são os recordes mundiais de atletismo mais recentes?" },
  { title: "Fórmula 1", label: "pneus e bandeiras", prompt: "Explica o significado das bandeiras e os tipos de pneus na Fórmula 1." },
];

export default function Welcome({ onPick, isStreaming, uploadedFileName, onAttach, onRemoveAttachment }) {
  return (
    <div className="welcome">
      <div className="welcome-mark" aria-hidden="true" />
      <h1 className="welcome-title">SportSphere</h1>
      <p className="welcome-lead">
        Analisa eventos desportivos com confiança usando um assistente especializado em
        estatísticas, regulamentos e logística.
      </p>
      <p className="welcome-sub">
        Pergunta diretamente sobre os desportos suportados (Basquetebol, Ténis, Atletismo,
        Fórmula 1) e o assistente responde com base nos documentos locais.
      </p>

      <div className="welcome-input">
        <InputBar
          isStreaming={isStreaming}
          uploadedFileName={uploadedFileName}
          onSend={onPick}
          onAttach={onAttach}
          onRemoveAttachment={onRemoveAttachment}
          autoFocus
        />
      </div>

      <div className="suggestion-grid">
        {SUGGESTIONS.map((s) => (
          <button key={s.title} className="ctr-btn suggestion-card" onClick={() => onPick(s.prompt)}>
            <span className="suggestion-title">{s.title}</span>
            <span className="suggestion-label">{s.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}