import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "./ChatPanel.css";
import InputBar from "./InputBar.jsx";

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard indisponível, ignora silenciosamente
    }
  }

  return (
    <button className="msg-action-btn" onClick={handleCopy} title="Copiar resposta">
      <span className="material-symbols-outlined">{copied ? "check" : "content_copy"}</span>
    </button>
  );
}

function UserMessage({ content, index, isStreaming, onEditResend }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(content);
  const textareaRef = useRef(null);

  useEffect(() => {
    if (editing) {
      textareaRef.current?.focus();
      textareaRef.current?.setSelectionRange(draft.length, draft.length);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editing]);

  function submitEdit() {
    const text = draft.trim();
    if (!text || isStreaming) return;
    setEditing(false);
    onEditResend(index, text);
  }

  if (editing) {
    return (
      <div className="msg-edit-box">
        <textarea
          ref={textareaRef}
          className="msg-edit-textarea"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submitEdit();
            }
            if (e.key === "Escape") {
              setDraft(content);
              setEditing(false);
            }
          }}
          rows={Math.min(8, Math.max(2, draft.split("\n").length))}
        />
        <div className="msg-edit-actions">
          <button className="msg-edit-cancel" onClick={() => { setDraft(content); setEditing(false); }}>
            Cancelar
          </button>
          <button className="msg-edit-confirm" onClick={submitEdit} disabled={isStreaming || !draft.trim()}>
            Reenviar
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="msg-bubble-wrap">
      <div className="msg-bubble">{content}</div>
      <div className="msg-actions msg-actions-user">
        <button
          className="msg-action-btn"
          onClick={() => setEditing(true)}
          title="Editar e reenviar"
          disabled={isStreaming}
        >
          <span className="material-symbols-outlined">edit</span>
        </button>
      </div>
    </div>
  );
}

function AssistantMessage({ content, isLast, isStreaming }) {
  const showPlaceholder = !content && isStreaming && isLast;
  return (
    <div className="msg-bubble-wrap">
      <div className="msg-bubble msg-bubble-assistant">
        {showPlaceholder ? (
          "···"
        ) : (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        )}
      </div>
      {content && (
        <div className="msg-actions">
          <CopyButton text={content} />
        </div>
      )}
    </div>
  );
}

export default function ChatPanel({
  messages,
  isStreaming,
  activeFolders,
  activeSources,
  activeExcerpts,
  uploadedFileName,
  onSend,
  onStop,
  onEditResend,
  onAttach,
  onRemoveAttachment,
}) {
  const scrollRef = useRef(null);
  const [sourcesExpanded, setSourcesExpanded] = useState(false);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    setSourcesExpanded(false);
  }, [activeSources]);

  return (
    <div className="chat-panel">
      <div className="chat-scroll" ref={scrollRef}>
        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="msg-row msg-user">
              <UserMessage
                content={m.content}
                index={i}
                isStreaming={isStreaming}
                onEditResend={onEditResend}
              />
            </div>
          ) : (
            <div key={i} className="msg-row msg-assistant">
              <AssistantMessage content={m.content} isLast={i === messages.length - 1} isStreaming={isStreaming} />
            </div>
          )
        )}
      </div>

      {(activeFolders?.length > 0 || isStreaming) && (
        <div className="scope-wrap">
          <button
            className="scope-chip"
            onClick={() => setSourcesExpanded((v) => !v)}
            disabled={!activeExcerpts?.length}
          >
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
            {activeExcerpts?.length > 0 && (
              <span className="material-symbols-outlined scope-expand-icon">
                {sourcesExpanded ? "expand_less" : "expand_more"}
              </span>
            )}
          </button>

          {sourcesExpanded && activeExcerpts?.length > 0 && (
            <div className="scope-excerpts">
              {activeExcerpts.map((ex, i) => (
                <div className="scope-excerpt" key={i}>
                  <span className="scope-excerpt-source">{ex.source}</span>
                  <p className="scope-excerpt-text">{ex.text}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="chat-input-bar">
        <InputBar
          isStreaming={isStreaming}
          uploadedFileName={uploadedFileName}
          onSend={onSend}
          onStop={onStop}
          onAttach={onAttach}
          onRemoveAttachment={onRemoveAttachment}
        />
      </div>
    </div>
  );
}