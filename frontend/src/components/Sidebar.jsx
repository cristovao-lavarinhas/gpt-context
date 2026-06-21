import "./Sidebar.css";
import logoDark from "../../assets/logo-dark.png";

export default function Sidebar({
  history,
  activeChatId,
  ollamaOnline,
  modelName,
  theme,
  view,
  onToggleTheme,
  onNewChat,
  onLoadChat,
  onDeleteChat,
  onOpenArchitecture,
  onOpenDocs,
}) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <img src={logoDark} alt="SportSphere" className="sidebar-brand-mark" />
      </div>

      <button className="sb-btn new-chat-btn" onClick={onNewChat}>
        <span className="material-symbols-outlined sb-icon">add</span> Novo Chat
      </button>

      <div className="sidebar-section-label">Recentes</div>

      <nav className="sidebar-history">
        {history.length === 0 && (
          <p className="sidebar-empty">As tuas conversas vão aparecer aqui.</p>
        )}
        {history.map((chat) => {
          const isActive = chat.id === activeChatId && view === "chat";
          return (
            <div className={`history-row ${isActive ? "history-row-active" : ""}`} key={chat.id}>
              <button className="sb-btn history-btn" onClick={() => onLoadChat(chat)}>
                <span className="material-symbols-outlined sb-icon">chat_bubble</span>
                <span className="history-btn-label">{chat.title}</span>
              </button>
              <button
                className="sb-btn history-delete-btn"
                aria-label="Apagar conversa"
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteChat(chat.id);
                }}
              >
                <span className="material-symbols-outlined" style={{ fontSize: "16px" }}>close</span>
              </button>
            </div>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <button
          className={`sb-btn sidebar-footer-link ${view === "architecture" ? "sidebar-footer-link-active" : ""}`}
          onClick={onOpenArchitecture}
        >
          <span className="material-symbols-outlined sb-icon">architecture</span> Arquitetura
        </button>
        <button
          className={`sb-btn sidebar-footer-link ${view === "docs" ? "sidebar-footer-link-active" : ""}`}
          onClick={onOpenDocs}
        >
          <span className="material-symbols-outlined sb-icon">folder_managed</span> Documentos
        </button>
        <button className="sb-btn theme-toggle" onClick={onToggleTheme}>
          <span className="material-symbols-outlined sb-icon">
            {theme === "dark" ? "light_mode" : "dark_mode"}
          </span>
          {theme === "dark" ? "Tema claro" : "Tema escuro"}
        </button>

        <div className="sidebar-status">
          <span className={`status-dot ${ollamaOnline ? "status-online" : "status-offline"}`} />
          <span className="status-label">{modelName || "modelo"}</span>
          <span className="status-state">{ollamaOnline ? "disponível" : "offline"}</span>
        </div>
      </div>
    </aside>
  );
}