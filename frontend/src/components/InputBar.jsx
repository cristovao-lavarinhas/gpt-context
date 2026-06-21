import { useRef, useState } from "react";
import "./InputBar.css";

export default function InputBar({
  isStreaming,
  uploadedFileName,
  onSend,
  onStop,
  onAttach,
  onRemoveAttachment,
  autoFocus = false,
}) {
  const [input, setInput] = useState("");
  const fileInputRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || isStreaming) return;
    onSend(text);
    setInput("");
  };

  return (
    <form className="input-bar" onSubmit={handleSubmit}>
      {uploadedFileName && (
        <div className="attachment-pill">
          <span className="material-symbols-outlined" style={{ fontSize: "14px" }}>attach_file</span>
          {uploadedFileName}
          <button type="button" className="attachment-remove" onClick={onRemoveAttachment}>
            <span className="material-symbols-outlined" style={{ fontSize: "12px" }}>close</span>
          </button>
        </div>
      )}
      <div className="input-bar-row">
        <button
          type="button"
          className="ib-btn attach-btn"
          onClick={() => fileInputRef.current?.click()}
          aria-label="Anexar ficheiro"
          title="Anexar ficheiro"
        >
          <span className="material-symbols-outlined">attach_file</span>
        </button>
        <input
          ref={fileInputRef}
          type="file"
          hidden
          onChange={(e) => {
            if (e.target.files?.[0]) onAttach(e.target.files[0]);
            e.target.value = "";
          }}
        />
        <input
          className="input-bar-text"
          placeholder="Pergunte sobre eventos, estatísticas, regulamentos..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          autoFocus={autoFocus}
        />
        {isStreaming ? (
          <button
            type="button"
            className="ib-btn send-btn stop-btn"
            onClick={onStop}
            aria-label="Parar geração"
            title="Parar"
          >
            <span className="material-symbols-outlined">stop</span>
          </button>
        ) : (
          <button className="ib-btn send-btn" type="submit" disabled={!input.trim()} aria-label="Enviar">
            <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>arrow_upward</span>
          </button>
        )}
      </div>
    </form>
  );
}