import { useEffect, useRef, useState } from "react";
import "./DocsLibrary.css";
import { fetchDocsLibrary, uploadDoc, deleteDoc, createDocFolder, deleteDocFolder } from "../api.js";

const FOLDER_ICONS = {
  soccer: "sports_soccer",
  basketball: "sports_basketball",
  nfl: "sports_football",
  tennis: "sports_tennis",
  cricket: "sports_cricket",
  formula1: "sports_motorsports",
  olympics: "sprint",
};

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function FolderCard({ folder, label, files, custom, onUpload, onDelete, onDeleteFolder, busyFolder }) {
  const fileInputRef = useRef(null);
  const isBusy = busyFolder === folder;
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  return (
    <div className="docs-card">
      <div className="docs-card-head">
        <span className="docs-card-icon">
          <span className="material-symbols-outlined">{FOLDER_ICONS[folder] || "folder"}</span>
        </span>
        <div>
          <h3 className="docs-card-title">
            {label}
            {custom && <span className="docs-card-custom-tag">custom</span>}
          </h3>
          <span className="docs-card-path">local-docs/{folder}/</span>
        </div>

        <div className="docs-card-actions">
          <button
            className="docs-add-btn"
            onClick={() => fileInputRef.current?.click()}
            disabled={isBusy}
            title="Adicionar ficheiro"
          >
            <span className="material-symbols-outlined">add</span>
          </button>
          {custom && (
            <button
              className="docs-folder-delete-btn"
              onClick={() => setConfirmingDelete(true)}
              disabled={isBusy}
              title="Apagar pasta"
            >
              <span className="material-symbols-outlined">delete</span>
            </button>
          )}
        </div>

        <input
          ref={fileInputRef}
          type="file"
          hidden
          onChange={(e) => {
            if (e.target.files?.[0]) onUpload(folder, e.target.files[0]);
            e.target.value = "";
          }}
        />
      </div>

      {confirmingDelete && (
        <div className="docs-confirm-bar">
          <span>
            Apagar "{label}" e os {files.length} ficheiro{files.length === 1 ? "" : "s"} dentro dela?
          </span>
          <div className="docs-confirm-actions">
            <button
              className="docs-confirm-yes"
              onClick={() => {
                setConfirmingDelete(false);
                onDeleteFolder(folder);
              }}
            >
              Apagar
            </button>
            <button className="docs-confirm-no" onClick={() => setConfirmingDelete(false)}>
              Cancelar
            </button>
          </div>
        </div>
      )}

      <div className="docs-file-list">
        {files.length === 0 && <p className="docs-empty">Sem ficheiros nesta pasta.</p>}
        {files.map((f) => (
          <div className="docs-file-row" key={f.name}>
            <span className="material-symbols-outlined docs-file-icon">description</span>
            <span className="docs-file-name" title={f.name}>{f.name}</span>
            <span className="docs-file-size">{formatSize(f.size)}</span>
            <button
              className="docs-file-delete"
              onClick={() => onDelete(folder, f.name)}
              aria-label={`Apagar ${f.name}`}
            >
              <span className="material-symbols-outlined">delete</span>
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function DocsLibrary({ onBack }) {
  const [library, setLibrary] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyFolder, setBusyFolder] = useState(null);
  const [error, setError] = useState("");
  const [creatingFolder, setCreatingFolder] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");

  function load() {
    fetchDocsLibrary()
      .then(setLibrary)
      .catch(() => setError("Não foi possível carregar a biblioteca de documentos."))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  async function handleUpload(folder, file) {
    setBusyFolder(folder);
    setError("");
    try {
      await uploadDoc(folder, file);
      load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusyFolder(null);
    }
  }

  async function handleDelete(folder, filename) {
    setBusyFolder(folder);
    setError("");
    try {
      await deleteDoc(folder, filename);
      load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusyFolder(null);
    }
  }

  async function handleDeleteFolder(folder) {
    setBusyFolder(folder);
    setError("");
    try {
      await deleteDocFolder(folder);
      load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusyFolder(null);
    }
  }

  async function handleCreateFolder(e) {
    e.preventDefault();
    const name = newFolderName.trim();
    if (!name) return;
    setError("");
    try {
      await createDocFolder(name);
      setNewFolderName("");
      setCreatingFolder(false);
      load();
    } catch (e2) {
      setError(e2.message);
    }
  }

  return (
    <div className="docs-library">
      <button className="docs-back" onClick={onBack}>
        <span className="material-symbols-outlined">arrow_back</span> Voltar ao chat
      </button>

      <header className="docs-header">
        <div className="docs-header-top">
          <h1>
            <span className="material-symbols-outlined">folder_managed</span> Documentos Locais
          </h1>
          {!creatingFolder && (
            <button className="docs-new-folder-btn" onClick={() => setCreatingFolder(true)}>
              <span className="material-symbols-outlined">create_new_folder</span> Nova pasta
            </button>
          )}
        </div>
        <p>Adiciona ou remove ficheiros da base de conhecimento por desporto, sem mexer na pasta manualmente.</p>

        {creatingFolder && (
          <form className="docs-new-folder-form" onSubmit={handleCreateFolder}>
            <input
              autoFocus
              className="docs-new-folder-input"
              placeholder="Nome da pasta (ex: voleibol)"
              value={newFolderName}
              onChange={(e) => setNewFolderName(e.target.value)}
            />
            <button type="submit" className="docs-new-folder-confirm">Criar</button>
            <button
              type="button"
              className="docs-new-folder-cancel"
              onClick={() => {
                setCreatingFolder(false);
                setNewFolderName("");
              }}
            >
              Cancelar
            </button>
          </form>
        )}
      </header>

      {error && <div className="docs-error">{error}</div>}

      {loading ? (
        <p className="docs-loading">A carregar...</p>
      ) : (
        <div className="docs-grid">
          {library.map((entry) => (
            <FolderCard
              key={entry.folder}
              folder={entry.folder}
              label={entry.label}
              files={entry.files}
              custom={entry.custom}
              onUpload={handleUpload}
              onDelete={handleDelete}
              onDeleteFolder={handleDeleteFolder}
              busyFolder={busyFolder}
            />
          ))}
        </div>
      )}
    </div>
  );
}