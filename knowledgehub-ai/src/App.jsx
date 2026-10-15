import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  LayoutDashboard,
  Files,
  BrainCircuit,
  Settings,
  Search,
  Bell,
  Sparkles,
  ArrowUpRight,
  Upload,
  ShieldCheck,
  Database,
  MessageSquare,
  ChevronRight,
  Activity,
  Sun,
  Moon,
  FileText,
  Clock3,
  LogOut,
  Trash2,
  RotateCw,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Eye,
  Download,
  Languages,
  Volume2,
  VolumeX,
  Globe,
  User,
} from "lucide-react";
import Login from "./components/Login";
import AIAssistant from "./components/AIAssistant";
import { api } from "./services/api";
import { t, SUPPORTED_LANGUAGES } from "./services/translations";

function formatFileSize(bytes) {
  if (!bytes) return "0 B";
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

function getStatusBadgeClass(status, theme) {
  switch (status?.toLowerCase()) {
    case "indexed":
      return theme.status;
    case "chunked":
    case "extracted":
      return "text-cyan-400 bg-cyan-400/10";
    case "processing":
    case "pending":
      return theme.processing;
    case "failed":
      return "text-rose-400 bg-rose-500/10";
    default:
      return theme.muted + " bg-slate-500/10";
  }
}

export default function App() {
  const [dark, setDark] = useState(true);
  const [currentUser, setCurrentUser] = useState(() => api.getUser());
  const [isLoggedIn, setIsLoggedIn] = useState(() => !!api.getToken());
  const [currentLang, setCurrentLang] = useState(() => localStorage.getItem("kh_language") || "en");
  const [speechRate, setSpeechRate] = useState(() => parseFloat(localStorage.getItem("kh_speech_rate") || "1.0"));
  const [autoRead, setAutoRead] = useState(() => localStorage.getItem("kh_auto_read") === "true");
  const [activeTab, setActiveTab] = useState("Dashboard");
  const [documents, setDocuments] = useState([]);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [reindexingId, setReindexingId] = useState(null);
  const [notification, setNotification] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const fileInputRef = useRef(null);

  const theme = dark
    ? {
        page: "bg-[#07111f] text-slate-100",
        sidebar: "bg-[#091625]/90 border-white/10",
        panel: "border-white/10 bg-white/[0.045]",
        panelHover: "hover:border-cyan-400/40 hover:bg-white/[0.07]",
        muted: "text-slate-400",
        subtle: "text-slate-500",
        input: "border-white/10 bg-white/[0.04]",
        divider: "border-white/10",
        soft: "bg-white/[0.035]",
        line: "bg-white/10",
        hero: "from-[#112b4c] via-[#111d39] to-[#102d40]",
        accent: "text-cyan-300",
        accentBg: "bg-cyan-400/10",
        button:
          "border-cyan-300/20 bg-cyan-300/10 text-cyan-200 hover:bg-cyan-300/20",
        status: "text-emerald-300 bg-emerald-400/10",
        processing: "text-amber-300 bg-amber-400/10",
        glowOne: "bg-blue-600/15",
        glowTwo: "bg-cyan-500/10",
      }
    : {
        page: "bg-[#f3f7fc] text-slate-800",
        sidebar: "bg-white/90 border-slate-200",
        panel: "border-slate-200 bg-white/85",
        panelHover: "hover:border-sky-300 hover:bg-white",
        muted: "text-slate-500",
        subtle: "text-slate-400",
        input: "border-slate-200 bg-white",
        divider: "border-slate-200",
        soft: "bg-slate-50",
        line: "bg-slate-200",
        hero: "from-[#dceeff] via-[#e9edff] to-[#d8f7fa]",
        accent: "text-sky-700",
        accentBg: "bg-sky-500/10",
        button: "border-sky-200 bg-sky-50 text-sky-700 hover:bg-sky-100",
        status: "text-emerald-700 bg-emerald-50",
        processing: "text-amber-700 bg-amber-50",
        glowOne: "bg-blue-400/15",
        glowTwo: "bg-cyan-300/20",
      };

  async function loadDocuments() {
    try {
      setLoadingDocs(true);
      const docs = await api.getDocuments();
      setDocuments(docs || []);
    } catch (err) {
      console.warn("Failed to load documents:", err.message);
    } finally {
      setLoadingDocs(false);
    }
  }

  // Session validation on mount
  useEffect(() => {
    async function checkAuthSession() {
      if (api.getToken()) {
        try {
          const user = await api.getMe();
          setCurrentUser(user);
          setIsLoggedIn(true);
        } catch (err) {
          console.warn("Session check failed or expired:", err.message);
          api.clearToken();
          setCurrentUser(null);
          setIsLoggedIn(false);
        }
      }
    }
    checkAuthSession();
  }, []);

  useEffect(() => {
    if (isLoggedIn) {
      loadDocuments();
    }
  }, [isLoggedIn]);

  useEffect(() => {
    if (notification) {
      const timer = setTimeout(() => setNotification(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [notification]);

  function handleLanguageChange(langCode) {
    setCurrentLang(langCode);
    localStorage.setItem("kh_language", langCode);
  }

  function handleSpeechRateChange(val) {
    setSpeechRate(val);
    localStorage.setItem("kh_speech_rate", val.toString());
  }

  function handleAutoReadToggle() {
    const next = !autoRead;
    setAutoRead(next);
    localStorage.setItem("kh_auto_read", next.toString());
  }

  function handleTestSpeech() {
    if (!window.speechSynthesis) {
      setNotification({
        type: "error",
        message: t("voiceUnsupportedTTS", currentLang),
      });
      return;
    }
    window.speechSynthesis.cancel();
    const phrase = t("voiceTestPhrase", currentLang);
    const utterance = new SpeechSynthesisUtterance(phrase);
    utterance.rate = speechRate;
    const voiceLang = currentLang === "ta" ? "ta-IN" : currentLang === "hi" ? "hi-IN" : "en-US";
    utterance.lang = voiceLang;
    window.speechSynthesis.speak(utterance);
    setNotification({
      type: "success",
      message: `Playing voice test in ${currentLang.toUpperCase()} (${speechRate}x speed)...`,
    });
  }

  async function handleLogout() {
    try {
      await api.logout();
    } catch (err) {
      console.warn("Logout error:", err.message);
    } finally {
      api.clearToken();
      setCurrentUser(null);
      setIsLoggedIn(false);
      setActiveTab("Dashboard");
      setNotification({
        type: "success",
        message: "You have been safely signed out.",
      });
    }
  }

  async function handleFileUpload(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    if (currentUser?.role === "viewer") {
      setNotification({
        type: "error",
        message: "Access Denied: Viewer accounts have read-only access. Only Admin or Editor roles can upload documents.",
      });
      event.target.value = "";
      return;
    }

    const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (![".pdf", ".docx"].includes(ext)) {
      setNotification({
        type: "error",
        message: "Only PDF and DOCX files are supported.",
      });
      event.target.value = "";
      return;
    }
    setUploading(true);
    try {
      const result = await api.uploadDocument(file);
      setNotification({
        type: "success",
        message: `Successfully processed "${file.name}" into ${result.chunk_count || 0} chunks!`,
      });
    } catch (err) {
      setNotification({
        type: "error",
        message: `Upload failed: ${err.message}`,
      });
    } finally {
      setUploading(false);
      event.target.value = "";
      await loadDocuments();
    }
  }

  async function handleDeleteDoc(id, filename) {
    if (currentUser?.role === "viewer") {
      setNotification({
        type: "error",
        message: "Access Denied: Viewer accounts have read-only access. Only Admin or Editor roles can delete documents.",
      });
      return;
    }
    if (
      !window.confirm(
        `Are you sure you want to delete "${filename}"? All vectors and chunks will be permanently purged.`
      )
    ) {
      return;
    }
    try {
      await api.deleteDocument(id);
      setNotification({
        type: "success",
        message: `Deleted "${filename}" and purged its vector embeddings.`,
      });
      await loadDocuments();
    } catch (err) {
      setNotification({
        type: "error",
        message: `Delete failed: ${err.message}`,
      });
    }
  }

  async function handleReindexDoc(id, filename) {
    if (currentUser?.role === "viewer") {
      setNotification({
        type: "error",
        message: "Access Denied: Viewer accounts have read-only access. Only Admin or Editor roles can re-index documents.",
      });
      return;
    }
    setReindexingId(id);
    try {
      const res = await api.indexDocument(id);
      setNotification({
        type: "success",
        message: `Re-indexed "${filename}" (${res.chunks_indexed} vectors updated in ChromaDB).`,
      });
      await loadDocuments();
    } catch (err) {
      setNotification({
        type: "error",
        message: `Re-indexing failed: ${err.message}`,
      });
    } finally {
      setReindexingId(null);
    }
  }

  const indexedCount = documents.filter((d) => d.status === "indexed").length;
  const failedCount = documents.filter((d) => d.status === "failed").length;
  const stats = [
    {
      label: "Total Documents",
      value: documents.length > 0 ? documents.length.toString() : "0",
      change: documents.length > 0 ? "Live API" : "Empty",
      icon: Files,
    },
    {
      label: "Indexed in ChromaDB",
      value: indexedCount.toString(),
      change:
        documents.length > 0
          ? `${Math.round((indexedCount / Math.max(1, documents.length)) * 100)}%`
          : "0%",
      icon: ShieldCheck,
    },
    {
      label: "Failed Ingestion",
      value: failedCount.toString(),
      change: failedCount > 0 ? `${failedCount} Requires Attention` : "0 Errors",
      icon: AlertCircle,
    },
    {
      label: "AI Conversations",
      value: "Live",
      change: "Cohere RAG",
      icon: MessageSquare,
    },
  ];

  const navItems = [
    { name: "Dashboard", label: t("navDashboard", currentLang), icon: LayoutDashboard },
    { name: "Documents", label: t("kbTitle", currentLang) || "Documents", icon: Files },
    { name: "AI Assistant", label: t("navAIAssistant", currentLang), icon: MessageSquare },
    { name: "Knowledge Base", label: t("navKnowledgeBase", currentLang), icon: Database },
    { name: "Activity", label: t("navActivity", currentLang), icon: Activity },
    { name: "Settings", label: t("navSettings", currentLang), icon: Settings },
  ];

  const filteredDocs = documents.filter((d) =>
    (d.filename || "").toLowerCase().includes(searchQuery.toLowerCase())
  );

  const headerTitles = {
    Dashboard: {
      badge: "WORKSPACE / OVERVIEW",
      title: "Your intelligent workspace.",
      desc: "Discover the knowledge hidden in your company documents.",
    },
    Documents: {
      badge: "WORKSPACE / REPOSITORY",
      title: "Document Library.",
      desc: "Manage, inspect, re-index, and delete uploaded company documents.",
    },
    "AI Assistant": {
      badge: "WORKSPACE / RAG INTELLIGENCE",
      title: "AI Knowledge Assistant.",
      desc: "Grounded question answering with page-level citations powered by Cohere & ChromaDB.",
    },
    "Knowledge Base": {
      badge: "WORKSPACE / VECTOR STORE",
      title: "ChromaDB Knowledge Base.",
      desc: "Vector embeddings and semantic indexing status across all documents.",
    },
    Activity: {
      badge: "WORKSPACE / AUDIT LOG",
      title: "System & Ingestion Activity.",
      desc: "Recent processing, chunking, and embedding pipeline events.",
    },
    Settings: {
      badge: "WORKSPACE / PREFERENCES",
      title: "System & AI Settings.",
      desc: "Configuration, RAG model parameters, and workspace diagnostics.",
    },
  };
  const currentHeader = headerTitles[activeTab] || headerTitles.Dashboard;

  if (!isLoggedIn) {
    return (
      <Login
        currentLang={currentLang}
        onLanguageChange={handleLanguageChange}
        onLogin={(user) => {
          setCurrentUser(user);
          setIsLoggedIn(true);
        }}
      />
    );
  }

  return (
    <div
      className={`relative min-h-screen overflow-hidden transition-colors duration-500 ${theme.page}`}
    >
      {/* Background lights */}
      <div
        className={`pointer-events-none absolute -left-32 top-0 h-96 w-96 rounded-full blur-[120px] ${theme.glowOne}`}
      />
      <div
        className={`pointer-events-none absolute right-0 top-64 h-96 w-96 rounded-full blur-[130px] ${theme.glowTwo}`}
      />

      <div className="relative z-10 flex min-h-screen flex-col md:flex-row">
        {/* Sidebar */}
        <aside
          className={`border-b p-5 backdrop-blur-2xl transition-colors duration-500 md:sticky md:top-0 md:flex md:h-screen md:w-64 md:shrink-0 md:flex-col md:border-b-0 md:border-r ${theme.sidebar}`}
        >
          <div className="mb-9 flex items-center gap-3">
            <div className="rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-300 p-3 text-white shadow-lg shadow-cyan-500/20">
              <BrainCircuit size={25} />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">KnowledgeHub</h1>
              <p className={`text-xs ${theme.muted}`}>
                AI Intelligence Platform
              </p>
            </div>
          </div>

          <p
            className={`mb-3 px-3 text-[10px] font-bold uppercase tracking-[0.24em] ${theme.subtle}`}
          >
            Workspace
          </p>

          <nav className="flex flex-wrap gap-2 md:flex-col">
            {navItems.map((item) => {
              const { name, label, icon: Icon } = item;
              const isActive = activeTab === name;
              return (
                <button
                  key={name}
                  onClick={() => setActiveTab(name)}
                  className={`flex items-center gap-3 rounded-xl px-4 py-3 text-left text-sm transition duration-300 ${
                    isActive
                      ? "bg-gradient-to-r from-blue-500/20 to-cyan-400/10 text-sky-500 ring-1 ring-cyan-400/30 font-medium"
                      : `${theme.muted} hover:bg-sky-400/10 hover:text-sky-500`
                  }`}
                >
                  <Icon size={18} />
                  <span>{label || name}</span>
                  {isActive && (
                    <span className="ml-auto h-2 w-2 rounded-full bg-cyan-400 shadow-[0_0_12px_#22d3ee]" />
                  )}
                </button>
              );
            })}
          </nav>

          {/* User Identity & Role Badge */}
          <div
            className={`mt-auto hidden rounded-2xl border p-4 md:block ${theme.panel}`}
          >
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-cyan-400 text-white font-bold text-sm shadow-md shadow-cyan-500/20 uppercase">
                {currentUser?.full_name ? currentUser.full_name.charAt(0) : "U"}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs font-semibold">{currentUser?.full_name || "Enterprise User"}</p>
                <p className="truncate text-[10px] text-slate-400 font-mono">{currentUser?.email || "user@company.com"}</p>
                <div className="flex items-center gap-1.5 mt-1">
                  <span
                    className={`inline-block h-2 w-2 rounded-full ${
                      currentUser?.role === "admin"
                        ? "bg-rose-400"
                        : currentUser?.role === "editor"
                        ? "bg-amber-400"
                        : "bg-emerald-400"
                    }`}
                  />
                  <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-300">
                    {currentUser?.role || "viewer"} role
                  </span>
                </div>
              </div>
            </div>
          </div>

          <button
            onClick={() => setActiveTab("Settings")}
            className={`mt-5 hidden items-center gap-3 rounded-xl px-4 py-3 text-sm transition md:flex cursor-pointer ${
              activeTab === "Settings"
                ? "bg-gradient-to-r from-blue-500/20 to-cyan-400/10 text-sky-500 ring-1 ring-cyan-400/30 font-medium"
                : `${theme.muted} hover:bg-sky-400/10 hover:text-sky-500`
            }`}
          >
            <Settings size={18} /> {t("navSettings", currentLang)}
          </button>
        </aside>

        {/* Main content */}
        <main className="min-w-0 flex-1 p-4 sm:p-6 lg:p-9">
          <motion.header
            initial={{ opacity: 0, y: -15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mb-8 flex flex-wrap items-center justify-between gap-4"
          >
            <div>
              <p
                className={`text-[10px] font-semibold uppercase tracking-[0.24em] ${theme.accent}`}
              >
                {currentHeader.badge}
              </p>
              <h2 className="mt-3 text-2xl font-bold tracking-tight sm:text-3xl">
                {currentHeader.title}
              </h2>
              <p className={`mt-2 text-sm ${theme.muted}`}>
                {currentHeader.desc}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2 sm:gap-3">
              {/* Language Selector Dropdown */}
              <div className="relative">
                <select
                  value={currentLang}
                  onChange={(e) => handleLanguageChange(e.target.value)}
                  aria-label="Select Interface Language"
                  className={`rounded-xl border px-3 py-2 text-xs font-semibold outline-none transition cursor-pointer appearance-none pr-7 ${theme.input} hover:border-cyan-400/40`}
                >
                  {SUPPORTED_LANGUAGES.map((l) => (
                    <option key={l.code} value={l.code} className="bg-slate-900 text-slate-100">
                      {l.nativeName}
                    </option>
                  ))}
                </select>
                <Globe size={13} className={`pointer-events-none absolute right-2.5 top-3 ${theme.muted}`} />
              </div>

              {/* User Profile Pill */}
              {currentUser && (
                <div
                  onClick={() => setActiveTab("Settings")}
                  title={`Logged in as ${currentUser.full_name} (${currentUser.role}). Click to view settings.`}
                  className={`flex items-center gap-2.5 rounded-xl border px-3 py-1.5 text-xs transition hover:scale-105 cursor-pointer ${theme.input}`}
                >
                  <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-cyan-400/20 text-cyan-300 font-bold text-xs uppercase">
                    {currentUser.full_name ? currentUser.full_name.charAt(0) : "U"}
                  </div>
                  <div className="hidden sm:flex flex-col text-left">
                    <span className="font-semibold text-xs leading-tight truncate max-w-[110px]">
                      {currentUser.full_name}
                    </span>
                    <span
                      className={`text-[10px] font-bold uppercase tracking-wider leading-none mt-0.5 ${
                        currentUser.role === "admin"
                          ? "text-rose-400"
                          : currentUser.role === "editor"
                          ? "text-amber-400"
                          : "text-emerald-400"
                      }`}
                    >
                      {currentUser.role}
                    </span>
                  </div>
                </div>
              )}

              {/* Dark / Light mode toggle */}
              <button
                onClick={() => setDark((previous) => !previous)}
                aria-label={
                  dark ? "Switch to light mode" : "Switch to dark mode"
                }
                title={dark ? "Switch to light mode" : "Switch to dark mode"}
                className={`flex items-center gap-2 rounded-xl border p-2.5 text-sm transition duration-300 hover:scale-105 ${theme.input}`}
              >
                {dark ? <Sun size={18} /> : <Moon size={18} />}
                <span className="hidden sm:inline">
                  {dark ? "Light" : "Dark"}
                </span>
              </button>

              {/* Sign Out */}
              <button
                onClick={handleLogout}
                aria-label="Sign out"
                title="Sign out of KnowledgeHub"
                className={`flex items-center gap-2 rounded-xl border p-2.5 text-xs transition duration-300 hover:scale-105 hover:border-rose-500/40 hover:bg-rose-500/10 hover:text-rose-400 cursor-pointer ${theme.input}`}
              >
                <LogOut size={16} />
                <span className="hidden sm:inline">{t("navSignOut", currentLang)}</span>
              </button>
            </div>
          </motion.header>

          {/* Hidden File Input */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            onChange={handleFileUpload}
            className="hidden"
          />

          {/* Notification Alert Banner */}
          <AnimatePresence>
            {notification && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className={`mb-6 flex items-center justify-between rounded-2xl border p-4 text-sm backdrop-blur-xl ${
                  notification.type === "success"
                    ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                    : "border-rose-500/30 bg-rose-500/10 text-rose-300"
                }`}
              >
                <div className="flex items-center gap-3">
                  {notification.type === "success" ? (
                    <CheckCircle2 size={18} className="shrink-0 text-emerald-400" />
                  ) : (
                    <AlertCircle size={18} className="shrink-0 text-rose-400" />
                  )}
                  <span>{notification.message}</span>
                </div>
                <button
                  onClick={() => setNotification(null)}
                  className="ml-4 cursor-pointer text-xs opacity-70 hover:opacity-100"
                >
                  Dismiss
                </button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Upload Ingestion Status Banner */}
          {uploading && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6 flex items-center gap-3 rounded-2xl border border-cyan-400/30 bg-cyan-400/10 p-4 text-cyan-200"
            >
              <Loader2 className="shrink-0 animate-spin text-cyan-400" size={18} />
              <span className="text-sm font-medium">
                Processing & indexing document (extracting text, page-aware chunking, vector embedding)...
              </span>
            </motion.div>
          )}

          {/* Dynamic Tab Views */}
          {activeTab === "AI Assistant" ? (
            <AIAssistant
              theme={theme}
              dark={dark}
              documents={documents}
              currentLang={currentLang}
              autoRead={autoRead}
              speechRate={speechRate}
            />
          ) : activeTab === "Documents" || activeTab === "Knowledge Base" ? (
            <section className={`rounded-3xl border p-6 backdrop-blur-xl ${theme.panel}`}>
              <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
                <div className="relative min-w-[260px] flex-1">
                  <Search className={`absolute left-3.5 top-3 ${theme.subtle}`} size={17} />
                  <input
                    type="text"
                    placeholder="Filter documents by name..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className={`w-full rounded-xl border py-2.5 pl-10 pr-4 text-sm outline-none transition focus:ring-2 focus:ring-cyan-400/20 ${theme.input}`}
                  />
                </div>

                <div className="flex items-center gap-3">
                  <button
                    onClick={loadDocuments}
                    disabled={loadingDocs}
                    title="Refresh document repository"
                    className={`flex items-center gap-2 rounded-xl border px-3.5 py-2.5 text-xs transition hover:scale-105 ${theme.input} ${theme.muted}`}
                  >
                    <RotateCw size={14} className={loadingDocs ? "animate-spin text-cyan-400" : ""} />
                    <span>Refresh</span>
                  </button>

                  <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploading}
                    className={`flex items-center gap-2 rounded-xl border px-4 py-2.5 text-xs font-semibold transition hover:scale-105 disabled:opacity-50 ${theme.button}`}
                  >
                    {uploading ? (
                      <Loader2 size={15} className="animate-spin" />
                    ) : (
                      <Upload size={15} />
                    )}
                    <span>Upload Document</span>
                  </button>
                </div>
              </div>

              {loadingDocs ? (
                <div className="flex items-center justify-center py-16 gap-3 text-sm">
                  <Loader2 className="animate-spin text-cyan-400" size={22} />
                  <span className={theme.muted}>Loading documents...</span>
                </div>
              ) : filteredDocs.length === 0 ? (
                <div className={`rounded-2xl border border-dashed p-12 text-center ${theme.divider}`}>
                  <Files className={`mx-auto mb-3 ${theme.subtle}`} size={36} />
                  <p className="text-sm font-semibold">No matching documents</p>
                  <p className={`mt-1 text-xs ${theme.muted}`}>
                    {searchQuery
                      ? "No files match your search query."
                      : "Upload PDF or DOCX files to populate your knowledge library."}
                  </p>
                  {searchQuery ? (
                    <button
                      onClick={() => setSearchQuery("")}
                      className={`mt-4 rounded-xl border px-3 py-1.5 text-xs ${theme.button}`}
                    >
                      Clear Filter
                    </button>
                  ) : (
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      className={`mt-4 inline-flex items-center gap-2 rounded-xl border px-4 py-2 text-xs font-semibold ${theme.button}`}
                    >
                      <Upload size={14} /> Upload First File
                    </button>
                  )}
                </div>
              ) : (
                <div className="space-y-3">
                  {filteredDocs.map((doc, index) => (
                    <motion.div
                      key={doc.id || doc.filename || index}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.04 }}
                      className={`flex flex-wrap items-center justify-between gap-4 rounded-2xl border p-4 transition duration-200 ${theme.divider} ${theme.panelHover}`}
                    >
                      <div className="flex min-w-0 items-center gap-3.5">
                        <div className={`rounded-xl p-3.5 ${theme.accentBg} ${theme.accent}`}>
                          <FileText size={24} />
                        </div>
                        <div className="min-w-0">
                          <h4
                            onClick={() => window.open(api.getDocumentFileUrl(doc.id), "_blank")}
                            className="truncate text-sm font-bold cursor-pointer hover:underline hover:text-cyan-400 transition"
                            title="Click to preview or download file"
                          >
                            {doc.filename}
                          </h4>
                          <div className={`mt-1 flex flex-wrap items-center gap-2 text-xs ${theme.muted}`}>
                            <span className="font-semibold text-cyan-400 uppercase tracking-wider text-[11px]">
                              {doc.file_type}
                            </span>
                            <span>•</span>
                            <span>{formatFileSize(doc.file_size)}</span>
                            <span>•</span>
                            <span>
                              {doc.page_count || 1} {doc.page_count === 1 ? "page" : "pages"}
                            </span>
                            <span>•</span>
                            <span>{doc.chunk_count || 0} chunks</span>
                            {doc.created_at && (
                              <>
                                <span>•</span>
                                <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                              </>
                            )}
                          </div>
                          {doc.status === "failed" && doc.error_message && (
                            <p className="mt-1 text-[11px] text-rose-400 font-medium truncate max-w-[420px]" title={doc.error_message}>
                              ⚠️ {doc.error_message}
                            </p>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <span
                          className={`rounded-full px-3 py-1 text-[11px] font-semibold capitalize ${getStatusBadgeClass(doc.status, theme)}`}
                          title={doc.error_message || undefined}
                        >
                          {doc.status}
                        </span>
                        <button
                          onClick={() => window.open(api.getDocumentFileUrl(doc.id), "_blank")}
                          title={doc.file_type === "pdf" ? "Open PDF preview in new tab" : "Download document"}
                          className={`flex items-center gap-1.5 rounded-xl border px-3 py-2 text-xs transition hover:scale-105 cursor-pointer ${theme.input} ${theme.muted} hover:text-cyan-400`}
                        >
                          {doc.file_type === "pdf" ? <Eye size={13} /> : <Download size={13} />}
                          <span className="hidden sm:inline">{doc.file_type === "pdf" ? "View" : "Download"}</span>
                        </button>
                        <button
                          onClick={() => handleReindexDoc(doc.id, doc.filename)}
                          disabled={reindexingId === doc.id}
                          title="Re-index into ChromaDB"
                          className={`flex items-center gap-1.5 rounded-xl border px-3 py-2 text-xs transition hover:scale-105 disabled:opacity-40 cursor-pointer ${theme.input} ${theme.muted} hover:text-cyan-400`}
                        >
                          <RotateCw
                            size={13}
                            className={reindexingId === doc.id ? "animate-spin text-cyan-400" : ""}
                          />
                          <span className="hidden sm:inline">Re-index</span>
                        </button>
                        <button
                          onClick={() => handleDeleteDoc(doc.id, doc.filename)}
                          title="Delete Document"
                          className={`flex items-center gap-1.5 rounded-xl border px-3 py-2 text-xs transition hover:scale-105 hover:border-rose-500/40 hover:bg-rose-500/10 hover:text-rose-400 cursor-pointer ${theme.input} ${theme.muted}`}
                        >
                          <Trash2 size={13} />
                          <span className="hidden sm:inline">Delete</span>
                        </button>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </section>
          ) : activeTab === "Activity" ? (
            <section className={`rounded-3xl border p-6 backdrop-blur-xl ${theme.panel}`}>
              <div className="mb-6 flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-bold">Ingestion & System Activity</h3>
                  <p className={`mt-1 text-xs ${theme.muted}`}>
                    Chronological audit of document uploads, chunk extractions, and vector indexing
                  </p>
                </div>
                <Activity className={theme.accent} size={22} />
              </div>

              {documents.length === 0 ? (
                <div className={`rounded-2xl border border-dashed p-10 text-center ${theme.divider}`}>
                  <Clock3 className={`mx-auto mb-2 ${theme.subtle}`} size={32} />
                  <p className="text-sm font-semibold">No recent activity</p>
                  <p className={`mt-1 text-xs ${theme.muted}`}>
                    Upload a document to see ingestion events here.
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {documents.map((doc, idx) => {
                    const isFailed = doc.status === "failed";
                    return (
                      <div
                        key={doc.id || idx}
                        className={`flex items-start gap-4 rounded-xl border p-4 ${theme.divider} ${theme.soft}`}
                      >
                        <div
                          className={`rounded-lg p-2 ${
                            isFailed ? "bg-rose-500/10 text-rose-400" : "bg-emerald-500/10 text-emerald-400"
                          }`}
                        >
                          {isFailed ? <AlertCircle size={18} /> : <CheckCircle2 size={18} />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-semibold">
                            {isFailed ? "Ingestion Failed: " : "Document Ingested: "}
                            <span className={isFailed ? "text-rose-400" : "text-cyan-400"}>{doc.filename}</span>
                          </p>
                          <p className={`mt-1 text-xs ${theme.muted}`}>
                            {isFailed ? (
                              <span className="text-rose-300">
                                Error: {doc.error_message || "Corrupted file or unreadable content"}
                              </span>
                            ) : (
                              `Parsed ${doc.page_count || 1} pages, generated ${doc.chunk_count || 0} chunks, ChromaDB status: ${doc.status}.`
                            )}
                          </p>
                          <p className={`mt-2 text-[10px] ${theme.subtle}`}>
                            {doc.created_at ? new Date(doc.created_at).toLocaleString() : "Recently"}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </section>
          ) : activeTab === "Settings" ? (
            <section className={`rounded-3xl border p-6 sm:p-8 backdrop-blur-xl ${theme.panel}`}>
              <div className="mb-8 flex items-center justify-between border-b pb-5 border-white/10">
                <div>
                  <h3 className="text-xl font-bold">{t("settingsTitle", currentLang)}</h3>
                  <p className={`mt-1 text-xs ${theme.muted}`}>
                    {t("settingsSubtitle", currentLang)}
                  </p>
                </div>
                <div className={`rounded-xl p-3 ${theme.accentBg} ${theme.accent}`}>
                  <Settings size={22} />
                </div>
              </div>

              <div className="grid gap-6 md:grid-cols-2">
                {/* 1. Language & Regional Settings */}
                <div className={`rounded-2xl border p-5 ${theme.divider} ${theme.soft}`}>
                  <h4 className="flex items-center gap-2 text-sm font-bold text-cyan-400">
                    <Globe size={17} /> {t("settingsSectionLanguage", currentLang)}
                  </h4>
                  <p className={`mt-2 text-xs ${theme.muted}`}>
                    {t("settingsLanguageDesc", currentLang)}
                  </p>
                  <div className="mt-4 grid grid-cols-3 gap-2">
                    {SUPPORTED_LANGUAGES.map((l) => (
                      <button
                        key={l.code}
                        onClick={() => handleLanguageChange(l.code)}
                        className={`flex flex-col items-center justify-center rounded-xl border p-3 text-xs font-semibold transition cursor-pointer ${
                          currentLang === l.code
                            ? "border-cyan-400 bg-cyan-400/20 text-cyan-200 ring-1 ring-cyan-400/40"
                            : `${theme.input} ${theme.muted} hover:border-cyan-400/30 hover:text-white`
                        }`}
                      >
                        <span className="text-sm font-bold">{l.nativeName}</span>
                        <span className="text-[10px] opacity-75 mt-0.5">{l.label}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* 2. Voice & Speech Synthesis */}
                <div className={`rounded-2xl border p-5 ${theme.divider} ${theme.soft}`}>
                  <h4 className="flex items-center gap-2 text-sm font-bold text-cyan-400">
                    <Volume2 size={17} /> {t("settingsSectionVoice", currentLang)}
                  </h4>
                  <p className={`mt-2 text-xs ${theme.muted}`}>
                    {t("settingsVoiceDesc", currentLang)}
                  </p>
                  
                  <div className="mt-4 space-y-4 text-xs">
                    {/* Auto Read Toggle */}
                    <div className="flex items-center justify-between py-1 border-b border-white/5">
                      <div>
                        <p className="font-semibold">{t("voiceAutoRead", currentLang)}</p>
                        <p className={`text-[11px] ${theme.muted}`}>{t("voiceAutoReadDesc", currentLang)}</p>
                      </div>
                      <button
                        onClick={handleAutoReadToggle}
                        className={`relative h-6 w-11 rounded-full transition-colors cursor-pointer ${
                          autoRead ? "bg-cyan-500" : "bg-slate-700"
                        }`}
                      >
                        <span
                          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                            autoRead ? "translate-x-6" : "translate-x-1"
                          }`}
                        />
                      </button>
                    </div>

                    {/* Speech Rate Slider */}
                    <div className="space-y-1.5 py-1 border-b border-white/5">
                      <div className="flex justify-between font-semibold">
                        <span>{t("voiceRate", currentLang)}</span>
                        <span className="text-cyan-400 font-mono">{speechRate}x</span>
                      </div>
                      <input
                        type="range"
                        min="0.75"
                        max="1.5"
                        step="0.25"
                        value={speechRate}
                        onChange={(e) => handleSpeechRateChange(parseFloat(e.target.value))}
                        className="w-full accent-cyan-400 cursor-pointer"
                      />
                      <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                        <span>0.75x (Slower)</span>
                        <span>1.0x (Normal)</span>
                        <span>1.5x (Faster)</span>
                      </div>
                    </div>

                    {/* Test Voice Playback Button */}
                    <div className="flex justify-end pt-1">
                      <button
                        onClick={handleTestSpeech}
                        className={`flex items-center gap-2 rounded-xl border px-3 py-1.5 text-xs font-semibold transition cursor-pointer ${theme.button}`}
                      >
                        <Volume2 size={14} />
                        <span>{t("voiceTest", currentLang)}</span>
                      </button>
                    </div>
                  </div>
                </div>

                {/* 3. User Profile & RBAC Profile */}
                <div className={`rounded-2xl border p-5 ${theme.divider} ${theme.soft}`}>
                  <h4 className="flex items-center gap-2 text-sm font-bold text-cyan-400">
                    <ShieldCheck size={17} /> {t("settingsSectionProfile", currentLang)}
                  </h4>
                  <div className="mt-4 space-y-3 text-xs">
                    <div className="flex items-center justify-between py-1.5 border-b border-white/5">
                      <span className={theme.muted}>Full Name</span>
                      <span className="font-semibold text-slate-200">{currentUser?.full_name || "Enterprise User"}</span>
                    </div>
                    <div className="flex items-center justify-between py-1.5 border-b border-white/5">
                      <span className={theme.muted}>Email Address</span>
                      <span className="font-mono text-slate-300">{currentUser?.email || "user@example.com"}</span>
                    </div>
                    <div className="flex items-center justify-between py-1.5 border-b border-white/5">
                      <span className={theme.muted}>{t("settingsRole", currentLang)}</span>
                      <span
                        className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                          currentUser?.role === "admin"
                            ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                            : currentUser?.role === "editor"
                            ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                            : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                        }`}
                      >
                        {currentUser?.role || "viewer"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between py-1.5 border-b border-white/5">
                      <span className={theme.muted}>Authentication</span>
                      <span className="font-semibold text-emerald-400">Bearer Token (SHA-256 Validated)</span>
                    </div>
                    <div className="flex items-center justify-between py-1.5">
                      <span className={theme.muted}>Permissions</span>
                      <span className="text-[11px] text-slate-300">
                        {currentUser?.role === "admin"
                          ? "Full Admin (Upload, Index, Purge, Query)"
                          : currentUser?.role === "editor"
                          ? "Editor (Upload, Index, Query)"
                          : "Viewer (Read-Only Q&A, Search)"}
                      </span>
                    </div>
                  </div>
                  <div className="mt-5 pt-3 border-t border-white/10 flex justify-end">
                    <button
                      onClick={handleLogout}
                      className="flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-2 text-xs font-semibold text-rose-300 transition hover:bg-rose-500/20 cursor-pointer"
                    >
                      <LogOut size={14} /> {t("navSignOut", currentLang)}
                    </button>
                  </div>
                </div>

                {/* 4. Appearance & Visual Theme */}
                <div className={`rounded-2xl border p-5 ${theme.divider} ${theme.soft}`}>
                  <h4 className="flex items-center gap-2 text-sm font-bold text-cyan-400">
                    <Sparkles size={17} /> Appearance & Visual Theme
                  </h4>
                  <p className={`mt-2 text-xs ${theme.muted}`}>
                    Toggle between the high-contrast holographic theme and the corporate light theme.
                  </p>
                  <div className="mt-4 flex items-center justify-between">
                    <span className="text-xs font-medium">
                      Active: {dark ? "Holographic Dark Mode" : "Executive Light Mode"}
                    </span>
                    <button
                      onClick={() => setDark(!dark)}
                      className={`flex items-center gap-2 rounded-xl border px-4 py-2 text-xs font-semibold transition cursor-pointer ${theme.button}`}
                    >
                      {dark ? <Sun size={15} /> : <Moon size={15} />}
                      <span>Switch to {dark ? "Light" : "Dark"}</span>
                    </button>
                  </div>
                </div>

                {/* 5. AI & RAG Engine Parameters */}
                <div className={`rounded-2xl border p-5 ${theme.divider} ${theme.soft}`}>
                  <h4 className="flex items-center gap-2 text-sm font-bold text-cyan-400">
                    <BrainCircuit size={17} /> AI & RAG Engine Configuration
                  </h4>
                  <div className="mt-4 space-y-3 text-xs">
                    <div className="flex justify-between py-1.5 border-b border-white/5">
                      <span className={theme.muted}>Embedding Model</span>
                      <span className="font-semibold">Cohere embed-english-v3.0 (1024-dim)</span>
                    </div>
                    <div className="flex justify-between py-1.5 border-b border-white/5">
                      <span className={theme.muted}>Chat Generation Model</span>
                      <span className="font-semibold">Cohere command-r-08-2024</span>
                    </div>
                    <div className="flex justify-between py-1.5 border-b border-white/5">
                      <span className={theme.muted}>Vector Storage</span>
                      <span className="font-semibold">ChromaDB Persistent (Cosine Similarity)</span>
                    </div>
                    <div className="flex justify-between py-1.5 border-b border-white/5">
                      <span className={theme.muted}>Chunking Strategy</span>
                      <span className="font-semibold">Sliding Window (500 tokens / 50 overlap)</span>
                    </div>
                    <div className="flex justify-between py-1.5 border-b border-white/5">
                      <span className={theme.muted}>Duplicate Protection</span>
                      <span className="font-semibold text-emerald-400">SHA-256 Content Hash (Active)</span>
                    </div>
                    <div className="flex justify-between py-1.5">
                      <span className={theme.muted}>Multilingual RAG Support</span>
                      <span className="font-semibold text-cyan-300">English (en), Tamil (ta), Hindi (hi)</span>
                    </div>
                  </div>
                </div>

                {/* 6. Infrastructure & Database */}
                <div className={`rounded-2xl border p-5 ${theme.divider} ${theme.soft}`}>
                  <h4 className="flex items-center gap-2 text-sm font-bold text-cyan-400">
                    <Database size={17} /> Storage & Backend Diagnostics
                  </h4>
                  <div className="mt-4 space-y-3 text-xs">
                    <div className="flex justify-between py-1.5 border-b border-white/5">
                      <span className={theme.muted}>API Endpoint</span>
                      <span className="font-semibold truncate max-w-[200px]">{api.baseUrl}</span>
                    </div>
                    <div className="flex justify-between py-1.5 border-b border-white/5">
                      <span className={theme.muted}>Metadata Database</span>
                      <span className="font-semibold">SQLite (knowledgehub.db)</span>
                    </div>
                    <div className="flex justify-between py-1.5 border-b border-white/5">
                      <span className={theme.muted}>File Upload Directory</span>
                      <span className="font-semibold">data/uploads/ (Traversal Protected)</span>
                    </div>
                    <div className="flex justify-between py-1.5 border-b border-white/5">
                      <span className={theme.muted}>Total Documents Ingested</span>
                      <span className="font-semibold">{documents.length}</span>
                    </div>
                    <div className="flex justify-between py-1.5 border-b border-white/5">
                      <span className={theme.muted}>Successfully Indexed Chunks</span>
                      <span className="font-semibold text-emerald-400">
                        {documents.reduce((acc, d) => acc + (d.chunk_count || 0), 0)} chunks
                      </span>
                    </div>
                    <div className="flex justify-between py-1.5">
                      <span className={theme.muted}>Supported Document Types</span>
                      <span className="font-semibold">PDF (.pdf), Word (.docx)</span>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          ) : (
            /* Dashboard View */
            <>
              {/* Hero */}
              <motion.section
                initial={{ opacity: 0, y: 22 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.65 }}
                className={`group relative mb-8 overflow-hidden rounded-3xl border border-cyan-400/20 bg-gradient-to-br p-6 shadow-2xl sm:p-9 ${theme.hero}`}
              >
                <div className="pointer-events-none absolute -right-16 -top-24 h-72 w-72 rounded-full border border-cyan-400/20 transition duration-700 group-hover:scale-125" />
                <div className="pointer-events-none absolute right-12 top-10 h-48 w-48 rounded-full bg-cyan-400/15 blur-[80px]" />

                <div className="relative z-10 flex flex-col items-center justify-between gap-8 md:flex-row">
                  <div className="max-w-xl">
                    <div
                      className={`mb-4 inline-flex items-center gap-2 rounded-full border border-cyan-400/20 px-3 py-1.5 text-xs ${theme.accentBg} ${theme.accent}`}
                    >
                      <Sparkles size={15} /> AI-POWERED KNOWLEDGE
                    </div>
                    <h3 className="text-3xl font-bold leading-tight sm:text-4xl">
                      Knowledge without limits.
                      <br />
                      <span className="bg-gradient-to-r from-blue-500 via-cyan-400 to-sky-500 bg-clip-text text-transparent">
                        Intelligence in motion.
                      </span>
                    </h3>
                    <p className={`mt-4 max-w-lg text-sm leading-6 ${theme.muted}`}>
                      Search your company's documents, discover insights, and get
                      answers connected to their original sources.
                    </p>
                    <button
                      onClick={() => setActiveTab("AI Assistant")}
                      className="mt-6 inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-cyan-500/20 transition duration-300 hover:-translate-y-1 hover:shadow-cyan-500/30 cursor-pointer"
                    >
                      <Sparkles size={17} /> Explore AI Assistant{" "}
                      <ArrowUpRight size={17} />
                    </button>
                  </div>

                  <motion.div
                    animate={{ y: [0, -10, 0], rotate: [0, 2, 0] }}
                    transition={{
                      duration: 5,
                      repeat: Infinity,
                      ease: "easeInOut",
                    }}
                    className="relative flex h-40 w-40 shrink-0 items-center justify-center rounded-[2rem] border border-cyan-300/30 bg-white/10 shadow-2xl shadow-cyan-500/20 backdrop-blur-xl md:mr-6 md:h-48 md:w-48"
                  >
                    <div className="absolute inset-4 rounded-[1.5rem] border border-cyan-300/20" />
                    <div className="flex h-24 w-24 items-center justify-center rounded-3xl bg-gradient-to-br from-blue-500 to-cyan-300 text-white shadow-[0_0_55px_rgba(34,211,238,0.25)]">
                      <BrainCircuit size={55} strokeWidth={1.2} />
                    </div>
                    <Sparkles
                      className="absolute right-5 top-5 text-cyan-300"
                      size={18}
                    />
                  </motion.div>
                </div>
              </motion.section>

              {/* Stats */}
              <section className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {stats.map((stat, index) => {
                  const Icon = stat.icon;

                  return (
                    <motion.article
                      key={stat.label}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.1, duration: 0.45 }}
                      whileHover={{ y: -6, rotateX: 3, rotateY: -3 }}
                      style={{ transformPerspective: 900 }}
                      className={`rounded-2xl border p-5 shadow-xl backdrop-blur-xl transition-colors duration-300 ${theme.panel} ${theme.panelHover}`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className={`text-sm ${theme.muted}`}>
                          {stat.label}
                        </span>
                        <div
                          className={`rounded-xl p-2.5 ${theme.accentBg} ${theme.accent}`}
                        >
                          <Icon size={20} />
                        </div>
                      </div>
                      <p className="mt-5 text-3xl font-bold tracking-tight">
                        {stat.value}
                      </p>
                      <p className="mt-3 text-xs font-semibold text-emerald-500">
                        {stat.change}{" "}
                        <span className={`font-normal ${theme.muted}`}>
                          vs previous period
                        </span>
                      </p>
                      <div
                        className={`mt-5 h-1 overflow-hidden rounded-full ${theme.line}`}
                      >
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${65 + index * 9}%` }}
                          transition={{ duration: 1, delay: 0.3 }}
                          className="h-full rounded-full bg-gradient-to-r from-blue-600 to-cyan-300"
                        />
                      </div>
                    </motion.article>
                  );
                })}
              </section>

              {/* Documents and activity */}
              <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
                <section
                  className={`rounded-2xl border p-5 backdrop-blur-xl sm:p-6 xl:col-span-2 ${theme.panel}`}
                >
                  <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h3 className="text-lg font-bold">Knowledge Library</h3>
                      <p className={`mt-1 text-xs ${theme.muted}`}>
                        Recently added knowledge sources
                      </p>
                    </div>
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      disabled={uploading}
                      className={`inline-flex items-center gap-2 rounded-xl border px-4 py-2.5 text-sm transition hover:scale-105 disabled:opacity-50 cursor-pointer ${theme.button}`}
                    >
                      {uploading ? (
                        <>
                          <Loader2 size={16} className="animate-spin" /> Uploading...
                        </>
                      ) : (
                        <>
                          <Upload size={16} /> Add Document
                        </>
                      )}
                    </button>
                  </div>

                  {loadingDocs ? (
                    <div className="flex items-center justify-center py-12 gap-3 text-sm">
                      <Loader2 className="animate-spin text-cyan-400" size={20} />
                      <span className={theme.muted}>Loading documents...</span>
                    </div>
                  ) : documents.length === 0 ? (
                    <div className={`rounded-xl border border-dashed p-8 text-center ${theme.divider}`}>
                      <div className={`mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl ${theme.accentBg} ${theme.accent}`}>
                        <Files size={24} />
                      </div>
                      <p className="text-sm font-semibold">No documents uploaded yet</p>
                      <p className={`mt-1 text-xs ${theme.muted}`}>
                        Upload PDF or DOCX files to index them into ChromaDB and enable AI Q&A.
                      </p>
                      <button
                        onClick={() => fileInputRef.current?.click()}
                        className={`mt-4 inline-flex items-center gap-2 rounded-xl border px-4 py-2 text-xs font-medium transition hover:scale-105 cursor-pointer ${theme.button}`}
                      >
                        <Upload size={14} /> Upload Your First Document
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {documents.slice(0, 5).map((doc, index) => (
                        <motion.div
                          key={doc.id || doc.filename || index}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: 0.1 + index * 0.05 }}
                          className={`flex flex-wrap items-center justify-between gap-3 rounded-xl border p-4 transition duration-300 ${theme.divider} ${theme.panelHover}`}
                        >
                          <div className="flex min-w-0 items-center gap-3">
                            <div
                              className={`rounded-xl p-3 ${theme.accentBg} ${theme.accent}`}
                            >
                              <FileText size={21} />
                            </div>
                            <div className="min-w-0">
                              <p className="truncate text-sm font-semibold">
                                {doc.filename}
                              </p>
                              <p className={`mt-1 text-xs ${theme.muted}`}>
                                {doc.file_type?.toUpperCase()} · {formatFileSize(doc.file_size)} · {doc.page_count || 1} {doc.page_count === 1 ? "page" : "pages"} · {doc.chunk_count || 0} chunks
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <span
                              className={`rounded-full px-3 py-1 text-[10px] font-semibold capitalize ${getStatusBadgeClass(doc.status, theme)}`}
                            >
                              {doc.status}
                            </span>
                            <button
                              onClick={() => handleReindexDoc(doc.id, doc.filename)}
                              disabled={reindexingId === doc.id}
                              title="Re-index vectors into ChromaDB"
                              className={`rounded-lg p-2 transition hover:bg-cyan-400/15 ${theme.muted} hover:text-cyan-400 disabled:opacity-40 cursor-pointer`}
                            >
                              <RotateCw
                                size={15}
                                className={reindexingId === doc.id ? "animate-spin text-cyan-400" : ""}
                              />
                            </button>
                            <button
                              onClick={() => handleDeleteDoc(doc.id, doc.filename)}
                              title="Delete document and purge vectors"
                              className={`rounded-lg p-2 transition hover:bg-rose-500/15 ${theme.muted} hover:text-rose-400 cursor-pointer`}
                            >
                              <Trash2 size={15} />
                            </button>
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  )}

                  {documents.length > 5 && (
                    <button
                      onClick={() => setActiveTab("Documents")}
                      className={`mt-5 flex w-full items-center justify-center gap-2 rounded-xl border border-dashed py-3 text-sm transition hover:text-sky-500 cursor-pointer ${theme.divider} ${theme.muted}`}
                    >
                      View all {documents.length} documents <ArrowUpRight size={15} />
                    </button>
                  )}
                </section>

                <section
                  className={`rounded-2xl border p-5 backdrop-blur-xl sm:p-6 ${theme.panel}`}
                >
                  <div className="mb-5 flex items-center justify-between">
                    <div>
                      <h3 className="text-lg font-bold">Workspace Insights</h3>
                      <p className={`mt-1 text-xs ${theme.muted}`}>
                        Knowledge at a glance
                      </p>
                    </div>
                    <Activity className={theme.accent} size={21} />
                  </div>

                  <div
                    className={`rounded-xl border p-4 ${theme.divider} ${theme.soft}`}
                  >
                    <div className="flex items-center justify-between">
                      <span className={`text-xs ${theme.muted}`}>
                        Indexed documents
                      </span>
                      <ShieldCheck className="text-emerald-500" size={19} />
                    </div>
                    <p className="mt-3 text-3xl font-bold">
                      {documents.length > 0
                        ? `${Math.round((indexedCount / documents.length) * 100)}%`
                        : "100%"}
                    </p>
                    <p className={`mt-2 text-xs leading-5 ${theme.muted}`}>
                      {documents.length > 0
                        ? `${indexedCount} of ${documents.length} documents indexed into ChromaDB vector database.`
                        : "Ready for PDF and DOCX ingestion."}
                    </p>
                    <div className={`mt-4 h-1.5 rounded-full ${theme.line}`}>
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-blue-600 to-cyan-300"
                        style={{
                          width: `${
                            documents.length > 0
                              ? Math.round((indexedCount / documents.length) * 100)
                              : 100
                          }%`,
                        }}
                      />
                    </div>
                  </div>

                  <div className="mt-5 space-y-4">
                    <div
                      onClick={() => setActiveTab("AI Assistant")}
                      className={`flex cursor-pointer items-start gap-3 rounded-xl p-2 transition hover:bg-cyan-400/5`}
                    >
                      <div
                        className={`rounded-lg p-2 ${theme.accentBg} ${theme.accent}`}
                      >
                        <MessageSquare size={18} />
                      </div>
                      <div>
                        <p className="text-sm font-semibold">Ask your documents</p>
                        <p className={`mt-1 text-xs leading-5 ${theme.muted}`}>
                          Find grounded answers across company files.
                        </p>
                      </div>
                    </div>
                    <div
                      onClick={() => setActiveTab("Activity")}
                      className={`flex cursor-pointer items-start gap-3 rounded-xl p-2 transition hover:bg-cyan-400/5`}
                    >
                      <div
                        className={`rounded-lg p-2 ${theme.accentBg} ${theme.accent}`}
                      >
                        <Clock3 size={18} />
                      </div>
                      <div>
                        <p className="text-sm font-semibold">Recent activity</p>
                        <p className={`mt-1 text-xs leading-5 ${theme.muted}`}>
                          Track pipeline & knowledge updates.
                        </p>
                      </div>
                    </div>
                    <div
                      onClick={() => setActiveTab("Documents")}
                      className={`flex cursor-pointer items-start gap-3 rounded-xl p-2 transition hover:bg-cyan-400/5`}
                    >
                      <div
                        className={`rounded-lg p-2 ${theme.accentBg} ${theme.accent}`}
                      >
                        <Database size={18} />
                      </div>
                      <div>
                        <p className="text-sm font-semibold">Knowledge sources</p>
                        <p className={`mt-1 text-xs leading-5 ${theme.muted}`}>
                          Organize internal company content.
                        </p>
                      </div>
                    </div>
                  </div>
                </section>
              </div>
            </>
          )}

          <footer
            className={`mt-8 flex flex-wrap items-center justify-between gap-2 text-xs ${theme.subtle}`}
          >
            <span>KnowledgeHub AI · Intelligent Company Knowledge</span>
            <span className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-400" />
              Connected to FastAPI RAG Backend
            </span>
          </footer>
        </main>
      </div>
    </div>
  );
}
