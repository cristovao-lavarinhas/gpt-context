import { useRef, useState } from "react";
import "./InputBar.css";

export default function InputBar({
  isStreaming,
  uploadedFileName,
  onSend,
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
          📎 {uploadedFileName}
          <button type="button" className="attachment-remove" onClick={onRemoveAttachment}>
            ✕
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
          📎
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
        <button className="ib-btn send-btn" type="submit" disabled={isStreaming || !input.trim()} aria-label="Enviar">
          ↑
        </button>
      </div>
    </form>
  );
}