import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  BrainCircuit,
  Send,
  Sparkles,
  Bot,
  User,
  FileText,
  AlertCircle,
  Loader2,
  RefreshCw,
  X,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Languages,
} from "lucide-react";
import { api } from "../services/api";
import { t, SUPPORTED_LANGUAGES } from "../services/translations";

const SUGGESTED_PROMPTS_BY_LANG = {
  en: [
    "What are the main security guidelines for employees?",
    "Summarize the company compliance requirements.",
    "What is the standard procedure in the operations playbook?",
    "What documents are currently indexed in the knowledge base?",
  ],
  ta: [
    "ஊழியர்களுக்கான முக்கிய பாதுகாப்பு வழிகாட்டுதல்கள் யாவை?",
    "நிறுவனத்தின் இணக்கத் தேவைகளைச் சுருக்கமாகக் கூறுக.",
    "செயல்பாட்டு கையேட்டின் நிலையான நடைமுறை என்ன?",
    "தற்போது ஆவணக் களஞ்சியத்தில் உள்ள ஆவணங்கள் எவை?",
  ],
  hi: [
    "कर्मचारियों के लिए मुख्य सुरक्षा दिशानिर्देश क्या हैं?",
    "कंपनी अनुपालन आवश्यकताओं का सारांश दें।",
    "संचालन नियमावली में मानक प्रक्रिया क्या है?",
    "वर्तमान में ज्ञान आधार में कौन से दस्तावेज़ शामिल हैं?",
  ],
};

function stripCitationsForSpeech(text) {
  if (!text) return "";
  return text
    .replace(/\[Source\s+\d+[^\]]*\]/gi, "")
    .replace(/\(Page\s+\d+\)/gi, "")
    .replace(/\bSource\s+\d+\b/gi, "")
    .replace(/[*_#`]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

export default function AIAssistant({
  theme,
  dark,
  documents = [],
  currentLang = "en",
  autoRead = false,
  speechRate = 1.0,
}) {
  const [messages, setMessages] = useState([
    {
      id: "welcome",
      role: "assistant",
      text: t("assistantWelcome", currentLang),
      sources: [],
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [sessionId, setSessionId] = useState(null);
  const [selectedDocId, setSelectedDocId] = useState(null);
  const [targetLang, setTargetLang] = useState(currentLang || "en");

  // Voice States
  const [isListening, setIsListening] = useState(false);
  const [speakingId, setSpeakingId] = useState(null);
  const [voiceError, setVoiceError] = useState("");
  const [isAutoRead, setIsAutoRead] = useState(autoRead);

  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);

  const indexedDocs = (documents || []).filter((d) => d.status === "indexed");

  // Deduplicate documents for dropdown so user sees unique filenames pointing to latest ID
  const uniqueDocsForSelector = [];
  const seenSelectorFilenames = new Set();
  const sortedIndexedDocs = [...indexedDocs].sort((a, b) => (b.id || 0) - (a.id || 0));
  for (const doc of sortedIndexedDocs) {
    const key = (doc.filename || "").toLowerCase().trim();
    if (!seenSelectorFilenames.has(key)) {
      seenSelectorFilenames.add(key);
      uniqueDocsForSelector.push(doc);
    }
  }
  uniqueDocsForSelector.sort((a, b) => (a.filename || "").localeCompare(b.filename || ""));

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  useEffect(() => {
    setTargetLang(currentLang);
  }, [currentLang]);

  // Clean up speech synthesis and recognition on unmount
  useEffect(() => {
    return () => {
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
    };
  }, []);

  // Voice Recognition Handler (Speech-to-Text)
  function toggleListening() {
    setVoiceError("");
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setVoiceError(t("voiceMicUnsupported", currentLang));
      return;
    }

    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognitionRef.current = recognition;

      // Select proper language dialect
      let speechCode = "en-US";
      if (targetLang === "ta") speechCode = "ta-IN";
      else if (targetLang === "hi") speechCode = "hi-IN";

      recognition.lang = speechCode;
      recognition.continuous = false;
      recognition.interimResults = true;

      recognition.onstart = () => {
        setIsListening(true);
        setVoiceError("");
      };

      recognition.onresult = (event) => {
        const transcript = Array.from(event.results)
          .map((result) => result[0].transcript)
          .join("");
        setInput(transcript);
      };

      recognition.onerror = (event) => {
        setIsListening(false);
        if (event.error === "not-allowed" || event.error === "service-not-allowed") {
          setVoiceError(t("voiceMicDenied", currentLang));
        } else if (event.error !== "no-speech") {
          setVoiceError(`Voice input error: ${event.error}`);
        }
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognition.start();
    } catch (err) {
      setIsListening(false);
      setVoiceError(err.message || "Failed to start speech recognition.");
    }
  }

  // Voice Output Handler (Text-to-Speech)
  function speakMessage(text, msgId) {
    if (!window.speechSynthesis) {
      setVoiceError(t("voiceUnsupportedTTS", currentLang));
      return;
    }

    if (speakingId === msgId) {
      window.speechSynthesis.cancel();
      setSpeakingId(null);
      return;
    }

    window.speechSynthesis.cancel();
    const cleanText = stripCitationsForSpeech(text);
    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = speechRate || 1.0;

    // Attempt to match installed system voice for selected language
    const voices = window.speechSynthesis.getVoices() || [];
    let langPrefix = targetLang === "ta" ? "ta" : targetLang === "hi" ? "hi" : "en";
    const matchedVoice = voices.find((v) => v.lang.toLowerCase().startsWith(langPrefix));
    if (matchedVoice) {
      utterance.voice = matchedVoice;
    }

    utterance.onend = () => setSpeakingId(null);
    utterance.onerror = () => setSpeakingId(null);

    setSpeakingId(msgId);
    window.speechSynthesis.speak(utterance);
  }

  async function handleSend(customText = null) {
    const questionText = (customText || input).trim();
    if (!questionText || loading) return;

    // Stop active speech playback if any
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
      setSpeakingId(null);
    }

    setError("");
    setVoiceError("");
    const userMsg = {
      id: "user-" + Date.now(),
      role: "user",
      text: questionText,
      sources: [],
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const response = await api.askAssistant(questionText, {
        topK: 5,
        documentId: selectedDocId,
        sessionId: sessionId,
        language: targetLang,
      });

      if (response.session_id) {
        setSessionId(response.session_id);
      }

      const botMsgId = "assistant-" + Date.now();
      const botMsg = {
        id: botMsgId,
        role: "assistant",
        text: response.answer || t("assistantNoEvidence", currentLang),
        sources: response.sources || [],
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, botMsg]);

      // Auto-read if enabled
      if (isAutoRead && botMsg.text) {
        speakMessage(botMsg.text, botMsgId);
      }
    } catch (err) {
      console.error("AI Assistant request failed:", err);
      setError(err.message || "Failed to communicate with AI Assistant.");
      const errorMsg = {
        id: "error-" + Date.now(),
        role: "assistant",
        text: `⚠️ Error: ${err.message || "Could not retrieve answer. Please verify backend connection and Cohere API key."}`,
        sources: [],
        isError: true,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function clearChat() {
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
      setSpeakingId(null);
    }
    setMessages([
      {
        id: "welcome-" + Date.now(),
        role: "assistant",
        text: t("assistantWelcome", currentLang),
        sources: [],
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    ]);
    setError("");
    setVoiceError("");
    setSessionId(null);
  }

  const suggestedPrompts =
    SUGGESTED_PROMPTS_BY_LANG[targetLang] || SUGGESTED_PROMPTS_BY_LANG["en"];

  return (
    <div
      className="flex h-[calc(100vh-12rem)] min-h-[520px] flex-col rounded-3xl border backdrop-blur-2xl transition-all duration-300 overflow-hidden shadow-2xl"
      style={{ borderColor: dark ? "rgba(255,255,255,0.1)" : "rgba(226,232,240,1)" }}
    >
      {/* Top Header */}
      <div className={`flex flex-wrap items-center justify-between gap-3 border-b px-4 sm:px-6 py-3.5 ${theme.panel}`}>
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-gradient-to-br from-blue-500 to-cyan-400 p-2 text-white shadow-md shadow-cyan-500/20">
            <BrainCircuit size={22} />
          </div>
          <div>
            <h3 className="text-sm sm:text-base font-bold tracking-tight">
              {t("assistantTitle", currentLang)}
            </h3>
            <p className={`text-[11px] sm:text-xs ${theme.muted}`}>
              {t("assistantSubtitle", currentLang)}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          {/* Target Response Language Selector */}
          <div className="flex items-center gap-1.5 text-xs">
            <Languages size={14} className="text-cyan-400" />
            <select
              value={targetLang}
              onChange={(e) => setTargetLang(e.target.value)}
              className={`rounded-xl border px-2.5 py-1.5 text-xs outline-none transition cursor-pointer ${
                dark
                  ? "bg-slate-900 text-cyan-200 border-cyan-500/30 hover:border-cyan-400"
                  : "bg-white text-slate-800 border-slate-300 hover:border-sky-400"
              }`}
              title="Select AI response language"
            >
              {SUPPORTED_LANGUAGES.map((l) => (
                <option key={l.code} value={l.code} className="bg-slate-900 text-white">
                  {l.nativeName} ({l.code.toUpperCase()})
                </option>
              ))}
            </select>
          </div>

          {/* Document Scope Selector */}
          <div className="flex items-center gap-1.5">
            <select
              value={selectedDocId || ""}
              onChange={(e) => setSelectedDocId(e.target.value ? Number(e.target.value) : null)}
              className={`rounded-xl border px-3 py-1.5 text-xs outline-none transition cursor-pointer max-w-[130px] sm:max-w-[200px] truncate ${
                dark
                  ? "bg-slate-900 text-cyan-200 border-cyan-500/30 hover:border-cyan-400 focus:border-cyan-400"
                  : "bg-white text-slate-800 border-slate-300 hover:border-sky-400 focus:border-sky-500"
              }`}
              title="Filter by source document"
            >
              <option value="" className={dark ? "bg-slate-900 text-slate-200" : "bg-white text-slate-800"}>
                {t("assistantAllSources", currentLang)}
              </option>
              {uniqueDocsForSelector.map((doc) => (
                <option
                  key={doc.id}
                  value={doc.id}
                  className={dark ? "bg-slate-900 text-slate-100" : "bg-white text-slate-800"}
                >
                  {doc.filename}
                </option>
              ))}
            </select>
            {selectedDocId && (
              <button
                type="button"
                onClick={() => setSelectedDocId(null)}
                title="Reset filter to all documents"
                className={`rounded-lg border p-1 text-[11px] transition cursor-pointer ${
                  dark
                    ? "border-cyan-500/30 bg-cyan-500/10 text-cyan-300 hover:bg-cyan-500/20"
                    : "border-sky-200 bg-sky-50 text-sky-700 hover:bg-sky-100"
                }`}
              >
                <X size={12} />
              </button>
            )}
          </div>

          {/* Auto-read Toggle */}
          <button
            type="button"
            onClick={() => setIsAutoRead(!isAutoRead)}
            title={isAutoRead ? "Auto-read enabled (click to disable)" : "Auto-read disabled (click to enable)"}
            className={`flex items-center gap-1.5 rounded-xl border px-2.5 py-1.5 text-xs transition cursor-pointer ${
              isAutoRead
                ? "border-cyan-400 bg-cyan-500/20 text-cyan-300"
                : `${theme.input} ${theme.muted} hover:text-cyan-400`
            }`}
          >
            {isAutoRead ? <Volume2 size={14} className="text-cyan-400" /> : <VolumeX size={14} />}
            <span className="hidden md:inline">{t("voiceAutoRead", currentLang)}</span>
          </button>

          {/* Clear Chat */}
          <button
            onClick={clearChat}
            title={t("assistantClear", currentLang)}
            className={`flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs transition hover:scale-105 cursor-pointer ${theme.input} ${theme.muted} hover:text-cyan-400`}
          >
            <RefreshCw size={13} /> <span className="hidden sm:inline">{t("assistantClear", currentLang)}</span>
          </button>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
        {messages.map((msg) => (
          <motion.div
            key={msg.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className={`flex items-start gap-3 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
          >
            {/* Avatar */}
            <div
              className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl shadow-md ${
                msg.role === "user"
                  ? "bg-gradient-to-br from-cyan-500 to-blue-600 text-white"
                  : msg.isError
                  ? "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                  : "bg-gradient-to-br from-blue-600 to-cyan-400 text-white"
              }`}
            >
              {msg.role === "user" ? <User size={18} /> : <Bot size={18} />}
            </div>

            {/* Message Bubble */}
            <div
              className={`relative max-w-[85%] sm:max-w-[78%] rounded-2xl p-4 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-gradient-to-r from-blue-600 to-cyan-600 text-white shadow-lg shadow-cyan-500/10"
                  : msg.isError
                  ? "border border-rose-500/30 bg-rose-500/10 text-rose-300"
                  : `border backdrop-blur-xl ${theme.panel}`
              }`}
            >
              {/* Text-to-speech speaker button on assistant messages */}
              {msg.role === "assistant" && !msg.isError && (
                <div className="absolute right-3 top-3">
                  <button
                    type="button"
                    onClick={() => speakMessage(msg.text, msg.id)}
                    title={speakingId === msg.id ? t("voiceStop", currentLang) : t("voicePlay", currentLang)}
                    className={`rounded-lg p-1.5 transition cursor-pointer ${
                      speakingId === msg.id
                        ? "bg-cyan-500 text-white shadow-md shadow-cyan-500/30 animate-pulse"
                        : "hover:bg-cyan-400/10 text-cyan-400"
                    }`}
                  >
                    {speakingId === msg.id ? <VolumeX size={15} /> : <Volume2 size={15} />}
                  </button>
                </div>
              )}

              <p className="whitespace-pre-wrap pr-6">{msg.text}</p>

              {/* Source citations */}
              {(() => {
                if (!msg.sources || msg.sources.length === 0) return null;
                const uniqueSources = [];
                const seenSourceKeys = new Set();
                for (const src of msg.sources) {
                  const normName = (src.filename || "").toLowerCase().replace(/[\s_]+/g, "_").trim();
                  const key = `${normName}_${src.page_number || 1}`;
                  if (!seenSourceKeys.has(key)) {
                    seenSourceKeys.add(key);
                    uniqueSources.push(src);
                  }
                }
                if (uniqueSources.length === 0) return null;
                return (
                  <div className="mt-3.5 pt-3 border-t border-cyan-400/20">
                    <p className="text-[11px] font-semibold tracking-wider uppercase text-cyan-400 flex items-center gap-1 mb-2">
                      <Sparkles size={12} /> {t("assistantSourcesHeading", currentLang)} ({uniqueSources.length})
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {uniqueSources.map((src, sIdx) => (
                        <div
                          key={sIdx}
                          className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs transition duration-200 ${
                            dark
                              ? "border-cyan-400/30 bg-cyan-400/10 text-cyan-200"
                              : "border-sky-300 bg-sky-50 text-sky-800"
                          }`}
                        >
                          <FileText size={13} className="text-cyan-400" />
                          <span className="font-medium truncate max-w-[180px]">{src.filename}</span>
                          <span className="rounded bg-cyan-500/20 px-1 py-0.2 text-[10px] font-semibold text-cyan-300">
                            {t("assistantPage", currentLang)} {src.page_number}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })()}

              <span className={`mt-2 block text-[10px] text-right opacity-60`}>
                {msg.timestamp}
              </span>
            </div>
          </motion.div>
        ))}

        {/* Loading Indicator */}
        {loading && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-3"
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-cyan-400 text-white">
              <Bot size={18} />
            </div>
            <div className={`flex items-center gap-2 rounded-2xl border px-4 py-3 text-sm ${theme.panel}`}>
              <Loader2 className="animate-spin text-cyan-400" size={16} />
              <span className={theme.muted}>{t("assistantSending", currentLang)}</span>
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Questions */}
      {messages.length <= 2 && (
        <div className="px-4 pb-2">
          <p className={`text-[11px] uppercase tracking-wider mb-2 font-semibold ${theme.subtle}`}>
            {t("assistantSuggestedHeading", currentLang)}:
          </p>
          <div className="flex flex-wrap gap-2">
            {suggestedPrompts.map((prompt, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(prompt)}
                disabled={loading}
                className={`rounded-xl border px-3 py-1.5 text-xs text-left transition hover:scale-102 hover:border-cyan-400/40 cursor-pointer ${theme.input} ${theme.muted}`}
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Voice or General Error Notification */}
      <AnimatePresence>
        {(error || voiceError) && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="flex items-center justify-between gap-2 border-t border-rose-500/20 bg-rose-500/10 px-4 py-2 text-xs text-rose-400"
          >
            <div className="flex items-center gap-2 truncate">
              <AlertCircle size={14} className="shrink-0" />
              <span className="truncate">{error || voiceError}</span>
            </div>
            <button
              onClick={() => {
                setError("");
                setVoiceError("");
              }}
              className="text-rose-400 hover:text-white cursor-pointer"
            >
              <X size={13} />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Voice Listening Active Indicator */}
      {isListening && (
        <div className="flex items-center justify-between border-t border-cyan-400/30 bg-cyan-500/10 px-4 py-2 text-xs text-cyan-300 animate-pulse">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-red-500 animate-ping" />
            <span>{t("voiceMicListening", currentLang)} ({targetLang.toUpperCase()})</span>
          </div>
          <button
            type="button"
            onClick={toggleListening}
            className="rounded bg-red-500/20 px-2 py-0.5 text-[11px] text-red-300 hover:bg-red-500/30 cursor-pointer"
          >
            {t("voiceMicStop", currentLang)}
          </button>
        </div>
      )}

      {/* Input Bar with Microphone & Send */}
      <div className={`border-t p-3 sm:p-4 ${theme.panel}`}>
        <div className="relative flex items-center gap-2">
          {/* Microphone Voice Input Button */}
          <button
            type="button"
            onClick={toggleListening}
            title={isListening ? t("voiceMicStop", currentLang) : t("voiceMicStart", currentLang)}
            className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border transition duration-200 cursor-pointer ${
              isListening
                ? "border-red-500 bg-red-500/20 text-red-400 shadow-lg shadow-red-500/20 animate-pulse"
                : `${theme.input} ${theme.muted} hover:border-cyan-400/50 hover:text-cyan-400 hover:scale-105`
            }`}
          >
            {isListening ? <MicOff size={18} className="text-red-400" /> : <Mic size={18} />}
          </button>

          {/* Text Area */}
          <div className="relative flex-1">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={t("assistantPlaceholder", currentLang)}
              rows={1}
              disabled={loading}
              className={`w-full resize-none rounded-2xl border py-3 pl-4 pr-12 text-sm outline-none transition focus:ring-2 focus:ring-cyan-400/20 ${
                theme.field || theme.input
              }`}
            />
            <button
              onClick={() => handleSend()}
              disabled={loading || !input.trim()}
              title="Send Question"
              className="absolute right-2 top-1/2 -translate-y-1/2 flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 text-white shadow-md shadow-cyan-500/20 transition duration-200 hover:scale-105 disabled:opacity-40 disabled:hover:scale-100 cursor-pointer"
            >
              {loading ? <Loader2 className="animate-spin" size={15} /> : <Send size={15} />}
            </button>
          </div>
        </div>

        <p className={`mt-2 text-center text-[11px] ${theme.subtle}`}>
          KnowledgeHub AI · Grounded in confidential company documents · Multilingual Voice Enabled
        </p>
      </div>
    </div>
  );
}
