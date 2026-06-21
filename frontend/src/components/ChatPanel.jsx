import { useEffect, useRef } from "react";
import "./ChatPanel.css";
import InputBar from "./InputBar.jsx";

export default function ChatPanel({
  messages,
  isStreaming,
  activeFolders,
  activeSources,
  uploadedFileName,
  onSend,
  onAttach,
  onRemoveAttachment,
}) {
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  return (
    <div className="chat-panel">
      <div className="chat-scroll" ref={scrollRef}>
        {messages.map((m, i) => (
          <div key={i} className={`msg-row msg-${m.role}`}>
            <div className="msg-bubble">
              {m.content || (isStreaming && i === messages.length - 1 ? "···" : "")}
            </div>
          </div>
        ))}
      </div>

      {(activeFolders?.length > 0 || isStreaming) && (
        <div className="scope-chip">
          <span className="scope-track">
            <span className={`scope-fill ${isStreaming ? "scope-fill-active" : ""}`} />
          </span>
          <span className="scope-label">
            a consultar: {activeFolders?.length ? activeFolders.join(", ") : "todos os documentos"}
            {activeSources?.length > 0 && (
              <span className="scope-sources">
                {" "}
                → {activeSources.map((s) => s.split("/").pop()).join(", ")}
              </span>
            )}
          </span>
        </div>
      )}

      <div className="chat-input-bar">
        <InputBar
          isStreaming={isStreaming}
          uploadedFileName={uploadedFileName}
          onSend={onSend}
          onAttach={onAttach}
          onRemoveAttachment={onRemoveAttachment}
        />
      </div>
    </div>
  );
}