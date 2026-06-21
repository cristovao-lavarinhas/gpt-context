import "./Welcome.css";
import InputBar from "./InputBar.jsx";
import logoLight from "../../assets/logo.png";
import logoDark from "../../assets/logo-dark.png";

const SUGGESTIONS = [
  { title: "Regras da NBA", label: "e detalhes da FIBA", icon: "sports_basketball", prompt: "Quais são as principais regras do basquetebol da NBA e da FIBA?" },
  { title: "Torneios Grand Slam", label: "como funcionam", icon: "sports_tennis", prompt: "Explica como funcionam os torneios Grand Slam de ténis." },
  { title: "Atletismo Olímpico", label: "recordes mundiais", icon: "sprint", prompt: "Quais são os recordes mundiais de atletismo mais recentes?" },
  { title: "Fórmula 1", label: "pneus e bandeiras", icon: "sports_motorsports", prompt: "Explica o significado das bandeiras e os tipos de pneus na Fórmula 1." },
];

export default function Welcome({ onPick, isStreaming, uploadedFileName, onAttach, onRemoveAttachment, theme }) {
  const logo = theme === "dark" ? logoDark : logoLight;

  return (
    <div className="welcome">
      <div className="welcome-content">
        <img src={logo} alt="SportSphere" className="welcome-mark" />

        <p className="welcome-lead">
          Analisa eventos desportivos com confiança usando um assistente especializado em
          estatísticas, regulamentos e logística.
        </p>

        <span className="welcome-kb-label">Base de Conhecimento Local</span>

        <div className="suggestion-grid">
          {SUGGESTIONS.map((s) => (
            <button key={s.title} className="ctr-btn suggestion-card" onClick={() => onPick(s.prompt)}>
              <span className="suggestion-icon">
                <span className="material-symbols-outlined">{s.icon}</span>
              </span>
              <span className="suggestion-title">{s.title}</span>
              <span className="suggestion-label">{s.label}</span>
            </button>
          ))}
        </div>
      </div>

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
    </div>
  );
}