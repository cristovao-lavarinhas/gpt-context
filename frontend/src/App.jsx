import { useEffect, useRef, useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import Welcome from "./components/Welcome.jsx";
import ChatPanel from "./components/ChatPanel.jsx";
import Architecture from "./components/Architecture.jsx";
import DocsLibrary from "./components/DocsLibrary.jsx";
import { fetchHistory, deleteChat, streamChat, uploadFile, checkHealth } from "./api.js";

export default function App() {
  const [history, setHistory] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeFolders, setActiveFolders] = useState([]);
  const [activeSources, setActiveSources] = useState([]);
  const [activeExcerpts, setActiveExcerpts] = useState([]);
  const [health, setHealth] = useState({ ollama_available: false, model: "" });
  const [uploadedFile, setUploadedFile] = useState(null);
  const [theme, setTheme] = useState(() => localStorage.getItem("sportsphere-theme") || "dark");
  const [view, setView] = useState("chat"); // "chat" | "architecture" | "docs"

  const stopStreamRef = useRef(null);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("sportsphere-theme", theme);
  }, [theme]);

  function toggleTheme() {
    setTheme((t) => (t === "dark" ? "light" : "dark"));
  }

  useEffect(() => {
    fetchHistory().then(setHistory).catch(() => {});
    checkHealth().then(setHealth);
  }, []);

  function handleNewChat() {
    setMessages([]);
    setActiveChatId(null);
    setActiveFolders([]);
    setActiveSources([]);
    setActiveExcerpts([]);
    setUploadedFile(null);
    setView("chat");
  }

  function handleLoadChat(chat) {
    setMessages(chat.messages);
    setActiveChatId(chat.id);
    setActiveFolders([]);
    setActiveSources([]);
    setActiveExcerpts([]);
    setView("chat");
  }

  async function handleDeleteChat(chatId) {
    const updated = await deleteChat(chatId);
    setHistory(updated);
    if (chatId === activeChatId) {
      setMessages([]);
      setActiveChatId(null);
    }
  }

  async function handleAttach(file) {
    const result = await uploadFile(file);
    setUploadedFile(result);
  }

  // baseMessages permite "editar e reenviar": passamos o histórico cortado
  // até à mensagem editada, em vez do `messages` atual completo.
  function handleSend(text, baseMessages = messages) {
    const nextMessages = [...baseMessages, { role: "user", content: text }, { role: "assistant", content: "" }];
    setMessages(nextMessages);
    setIsStreaming(true);
    setActiveFolders([]);
    setActiveSources([]);
    setActiveExcerpts([]);

    stopStreamRef.current = streamChat({
      messages: nextMessages.slice(0, -1),
      chatId: activeChatId,
      uploadedFileContent: uploadedFile?.content || "",
      onScope: (folders, sources, excerpts) => {
        setActiveFolders(folders || []);
        setActiveSources(sources || []);
        setActiveExcerpts(excerpts || []);
      },
      onToken: (token) => {
        setMessages((prev) => {
          const copy = [...prev];
          copy[copy.length - 1] = {
            role: "assistant",
            content: copy[copy.length - 1].content + token,
          };
          return copy;
        });
      },
      onDone: (payload) => {
        setIsStreaming(false);
        stopStreamRef.current = null;
        if (payload?.chat_id) {
          setActiveChatId(payload.chat_id);
          fetchHistory().then(setHistory).catch(() => {});
        }
      },
      onError: () => {
        setIsStreaming(false);
        stopStreamRef.current = null;
      },
    });
  }

  function handleStop() {
    stopStreamRef.current?.();
    stopStreamRef.current = null;
    setIsStreaming(false);
  }

  function handleEditResend(index, newText) {
    handleSend(newText, messages.slice(0, index));
  }

  const showWelcome = messages.length === 0;

  return (
    <div className="app-shell">
      <Sidebar
        history={history}
        activeChatId={activeChatId}
        ollamaOnline={health.ollama_available}
        modelName={health.model}
        theme={theme}
        view={view}
        onToggleTheme={toggleTheme}
        onNewChat={handleNewChat}
        onLoadChat={handleLoadChat}
        onDeleteChat={handleDeleteChat}
        onOpenArchitecture={() => setView("architecture")}
        onOpenDocs={() => setView("docs")}
      />

      <main className="main-panel">
        {view === "architecture" ? (
          <Architecture onBack={() => setView("chat")} />
        ) : view === "docs" ? (
          <DocsLibrary onBack={() => setView("chat")} />
        ) : showWelcome ? (
          <Welcome
            onPick={handleSend}
            isStreaming={isStreaming}
            uploadedFileName={uploadedFile?.filename}
            onAttach={handleAttach}
            onRemoveAttachment={() => setUploadedFile(null)}
            theme={theme}
          />
        ) : (
          <ChatPanel
            messages={messages}
            isStreaming={isStreaming}
            activeFolders={activeFolders}
            activeSources={activeSources}
            activeExcerpts={activeExcerpts}
            uploadedFileName={uploadedFile?.filename}
            onSend={handleSend}
            onStop={handleStop}
            onEditResend={handleEditResend}
            onAttach={handleAttach}
            onRemoveAttachment={() => setUploadedFile(null)}
          />
        )}
      </main>
    </div>
  );
}