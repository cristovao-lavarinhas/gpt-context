import "./Sidebar.css";

export default function Sidebar({
  history,
  activeChatId,
  ollamaOnline,
  modelName,
  onNewChat,
  onLoadChat,
  onDeleteChat,
}) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="sidebar-brand-mark" aria-hidden="true" />
        <span className="sidebar-brand-name">
          Sport<span className="sidebar-brand-accent">Sphere</span>
        </span>
      </div>

      <button className="sb-btn new-chat-btn" onClick={onNewChat}>
        <span className="sb-icon">＋</span> Nova conversa
      </button>

      <div className="sidebar-section-label">Histórico</div>

      <nav className="sidebar-history">
        {history.length === 0 && (
          <p className="sidebar-empty">As tuas conversas vão aparecer aqui.</p>
        )}
        {history.map((chat) => {
          const isActive = chat.id === activeChatId;
          return (
            <div className={`history-row ${isActive ? "history-row-active" : ""}`} key={chat.id}>
              <button className="sb-btn history-btn" onClick={() => onLoadChat(chat)}>
                {chat.title}
              </button>
              <button
                className="sb-btn history-delete-btn"
                aria-label="Apagar conversa"
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteChat(chat.id);
                }}
              >
                ✕
              </button>
            </div>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <span className={`status-dot ${ollamaOnline ? "status-online" : "status-offline"}`} />
        <span className="status-label">{modelName || "modelo"}</span>
        <span className="status-state">{ollamaOnline ? "disponível" : "offline"}</span>
      </div>
    </aside>
  );
}
