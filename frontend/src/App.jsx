import { useEffect, useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import Welcome from "./components/Welcome.jsx";
import ChatPanel from "./components/ChatPanel.jsx";
import { fetchHistory, deleteChat, streamChat, uploadFile, checkHealth } from "./api.js";

export default function App() {
  const [history, setHistory] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeFolders, setActiveFolders] = useState([]);
  const [activeSources, setActiveSources] = useState([]);
  const [health, setHealth] = useState({ ollama_available: false, model: "" });
  const [uploadedFile, setUploadedFile] = useState(null); // { filename, content }

  useEffect(() => {
    fetchHistory().then(setHistory).catch(() => {});
    checkHealth().then(setHealth);
  }, []);

  function handleNewChat() {
    setMessages([]);
    setActiveChatId(null);
    setActiveFolders([]);
    setActiveSources([]);
    setUploadedFile(null);
  }

  function handleLoadChat(chat) {
    setMessages(chat.messages);
    setActiveChatId(chat.id);
    setActiveFolders([]);
    setActiveSources([]);
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

  function handleSend(text) {
    const nextMessages = [...messages, { role: "user", content: text }, { role: "assistant", content: "" }];
    setMessages(nextMessages);
    setIsStreaming(true);
    setActiveFolders([]);
    setActiveSources([]);

    streamChat({
      messages: nextMessages.slice(0, -1),
      chatId: activeChatId,
      uploadedFileContent: uploadedFile?.content || "",
      onScope: (folders, sources) => {
        setActiveFolders(folders || []);
        setActiveSources(sources || []);
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
      onDone: ({ chat_id }) => {
        setIsStreaming(false);
        setActiveChatId(chat_id);
        fetchHistory().then(setHistory).catch(() => {});
      },
      onError: () => {
        setIsStreaming(false);
      },
    });
  }

  const showWelcome = messages.length === 0;

  return (
    <div className="app-shell">
      <Sidebar
        history={history}
        activeChatId={activeChatId}
        ollamaOnline={health.ollama_available}
        modelName={health.model}
        onNewChat={handleNewChat}
        onLoadChat={handleLoadChat}
        onDeleteChat={handleDeleteChat}
      />

      <main className="main-panel">
          {showWelcome ? (
            <Welcome
              onPick={handleSend}
              isStreaming={isStreaming}
              uploadedFileName={uploadedFile?.filename}
              onAttach={handleAttach}
              onRemoveAttachment={() => setUploadedFile(null)}
            />
          ) : (
          <ChatPanel
            messages={messages}
            isStreaming={isStreaming}
            activeFolders={activeFolders}
            activeSources={activeSources}
            uploadedFileName={uploadedFile?.filename}
            onSend={handleSend}
            onAttach={handleAttach}
            onRemoveAttachment={() => setUploadedFile(null)}
          />
        )}
      </main>
    </div>
  );
}
