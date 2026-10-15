import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  BrainCircuit,
  Search,
  ShieldCheck,
  Zap,
  Mail,
  LockKeyhole,
  Eye,
  EyeOff,
  Sun,
  Moon,
  ArrowRight,
  Sparkles,
  FileText,
  User,
  CheckCircle2,
  AlertCircle,
  Loader2,
  KeyRound,
  ArrowLeft,
  Languages,
} from "lucide-react";
import { api } from "../services/api";
import { t, SUPPORTED_LANGUAGES } from "../services/translations";

export default function Login({ onLogin, currentLang = "en", onLanguageChange }) {
  const [dark, setDark] = useState(true);
  const [mode, setMode] = useState("login"); // 'login' | 'register' | 'forgot' | 'reset'
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Form states
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [devResetToken, setDevResetToken] = useState("");
  const [remember, setRemember] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const lang = currentLang || "en";

  const theme = dark
    ? {
        page: "bg-[#06101f] text-white",
        muted: "text-slate-400",
        panel: "border-white/10 bg-white/[0.045]",
        field:
          "border-slate-700 bg-slate-950/50 text-white placeholder:text-slate-500 focus:border-cyan-400",
        glow: "bg-cyan-500/15",
      }
    : {
        page: "bg-[#f2f7ff] text-slate-900",
        muted: "text-slate-500",
        panel: "border-blue-100 bg-white/75",
        field:
          "border-blue-200 bg-white text-slate-900 placeholder:text-slate-400 focus:border-blue-500",
        glow: "bg-blue-300/30",
      };

  function switchMode(newMode) {
    setMode(newMode);
    setError("");
    setSuccessMsg("");
  }

  // Handle Login
  async function handleLogin(e) {
    e.preventDefault();
    setError("");
    setSuccessMsg("");

    if (!email.trim() || !password) {
      setError(t("errFillAll", lang));
      return;
    }

    try {
      setLoading(true);
      const res = await api.login(email.trim(), password, remember);
      if (onLogin) {
        onLogin(res.user);
      }
    } catch (err) {
      setError(err.message || t("errLoginFailed", lang));
    } finally {
      setLoading(false);
    }
  }

  // Handle Registration
  async function handleRegister(e) {
    e.preventDefault();
    setError("");
    setSuccessMsg("");

    if (!fullName.trim() || !email.trim() || !password || !confirmPassword) {
      setError(t("errFillAll", lang));
      return;
    }

    if (password.length < 8) {
      setError(t("errPasswordLength", lang));
      return;
    }

    if (password !== confirmPassword) {
      setError(t("errPasswordMatch", lang));
      return;
    }

    try {
      setLoading(true);
      const res = await api.register(fullName.trim(), email.trim(), password);
      setSuccessMsg(t("msgRegSuccess", lang));
      if (onLogin) {
        setTimeout(() => onLogin(res.user), 1000);
      }
    } catch (err) {
      setError(err.message || "Registration failed.");
    } finally {
      setLoading(false);
    }
  }

  // Handle Forgot Password
  async function handleForgotPassword(e) {
    e.preventDefault();
    setError("");
    setSuccessMsg("");

    if (!email.trim()) {
      setError(t("errFillAll", lang));
      return;
    }

    try {
      setLoading(true);
      const res = await api.forgotPassword(email.trim());
      setSuccessMsg(res.message);
      if (res.dev_reset_token) {
        setDevResetToken(res.dev_reset_token);
      }
    } catch (err) {
      setError(err.message || "Failed to process request.");
    } finally {
      setLoading(false);
    }
  }

  // Handle Reset Password
  async function handleResetPassword(e) {
    e.preventDefault();
    setError("");
    setSuccessMsg("");

    if (!resetToken.trim() || !password || !confirmPassword) {
      setError(t("errFillAll", lang));
      return;
    }

    if (password.length < 8) {
      setError(t("errPasswordLength", lang));
      return;
    }

    if (password !== confirmPassword) {
      setError(t("errPasswordMatch", lang));
      return;
    }

    try {
      setLoading(true);
      const res = await api.resetPassword(resetToken.trim(), password);
      setSuccessMsg(res.message || t("msgResetSuccess", lang));
      setTimeout(() => switchMode("login"), 2500);
    } catch (err) {
      setError(err.message || "Failed to reset password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={`relative min-h-screen overflow-hidden transition-colors duration-500 ${theme.page}`}>
      <div className={`pointer-events-none absolute -left-32 top-20 h-96 w-96 rounded-full blur-[130px] ${theme.glow}`} />
      <div className="pointer-events-none absolute right-0 top-40 h-96 w-96 rounded-full bg-violet-500/10 blur-[130px]" />

      <div className="relative z-10 mx-auto max-w-[1500px] p-4 sm:p-7 lg:p-10">
        {/* Header with Brand, Language Switcher, and Theme Toggle */}
        <header className="mb-10 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="rounded-2xl bg-gradient-to-br from-cyan-400 to-blue-600 p-3 text-white shadow-lg shadow-cyan-500/20">
              <BrainCircuit size={27} />
            </div>
            <div>
              <h1 className="text-lg font-bold sm:text-xl">
                KnowledgeHub <span className="text-cyan-400">AI</span>
              </h1>
              <p className={`text-[10px] uppercase tracking-[0.17em] sm:text-xs ${theme.muted}`}>
                {t("appSubtitle", lang)}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Language Switcher */}
            {onLanguageChange && (
              <div className={`flex items-center gap-1.5 rounded-xl border px-3 py-2 text-xs ${theme.panel}`}>
                <Languages size={15} className="text-cyan-400" />
                <select
                  value={lang}
                  onChange={(e) => onLanguageChange(e.target.value)}
                  className="bg-transparent font-medium outline-none cursor-pointer"
                >
                  {SUPPORTED_LANGUAGES.map((l) => (
                    <option key={l.code} value={l.code} className="bg-slate-900 text-white">
                      {l.nativeName} ({l.code.toUpperCase()})
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Dark / Light Mode */}
            <button
              type="button"
              onClick={() => setDark(!dark)}
              className={`flex items-center gap-2 rounded-xl border p-2.5 sm:p-3 text-sm transition hover:scale-105 cursor-pointer ${theme.panel}`}
              title="Toggle theme"
            >
              {dark ? <Sun size={18} /> : <Moon size={18} />}
              <span className="hidden sm:inline">
                {dark ? t("navLightMode", lang) : t("navDarkMode", lang)}
              </span>
            </button>
          </div>
        </header>

        <div className="grid items-center gap-10 lg:grid-cols-2 lg:gap-16">
          {/* Left: Product overview illustration */}
          <motion.section
            initial={{ opacity: 0, x: -25 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.7 }}
            className="hidden lg:block"
          >
            <p className="mb-5 inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-4 py-2 text-xs text-cyan-400">
              <Sparkles size={15} /> YOUR INTELLIGENT WORKSPACE
            </p>

            <h2 className="max-w-xl text-5xl font-bold leading-tight tracking-tight xl:text-6xl">
              Turn documents into{" "}
              <span className="bg-gradient-to-r from-cyan-400 via-blue-500 to-violet-500 bg-clip-text text-transparent">
                intelligence.
              </span>
            </h2>

            <p className={`mt-6 max-w-lg text-base leading-7 ${theme.muted}`}>
              {t("taglineDesc", lang)}
            </p>

            <div className="mt-9 space-y-5">
              {[
                {
                  icon: Search,
                  title: "Smart Semantic Retrieval",
                  desc: "ChromaDB vector store with exact cosine matching.",
                },
                {
                  icon: ShieldCheck,
                  title: "Grounded Citations",
                  desc: "Exact document and page citations for every fact.",
                },
                {
                  icon: Zap,
                  title: "Multilingual Intelligence",
                  desc: "English, Tamil, and Hindi natural language processing.",
                },
              ].map(({ icon: Icon, title, desc }) => (
                <div key={title} className="flex items-center gap-4">
                  <div className={`rounded-xl border border-cyan-400/15 p-3 text-cyan-400 ${theme.panel}`}>
                    <Icon size={22} />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold">{title}</h3>
                    <p className={`mt-1 text-sm ${theme.muted}`}>{desc}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Floating document illustration */}
            <div className="relative mt-12 flex h-64 items-center justify-center">
              <div className="absolute h-48 w-48 rounded-full border border-cyan-400/20" />
              <div className="absolute h-64 w-64 rounded-full border border-blue-500/15" />

              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 28, repeat: Infinity, ease: "linear" }}
                className="absolute h-56 w-56 rounded-full border border-dashed border-cyan-400/30"
              />

              <motion.div
                animate={{ y: [0, -12, 0], rotateY: [0, 8, 0] }}
                transition={{
                  duration: 4,
                  repeat: Infinity,
                  ease: "easeInOut",
                }}
                style={{ transformPerspective: 800 }}
                className={`relative z-10 flex h-40 w-36 flex-col items-center justify-center rounded-3xl border border-cyan-400/30 shadow-2xl shadow-cyan-500/20 backdrop-blur-xl ${theme.panel}`}
              >
                <div className="rounded-2xl bg-gradient-to-br from-cyan-400 to-blue-600 p-5 text-white">
                  <FileText size={45} />
                </div>
                <div className="mt-4 h-1.5 w-20 rounded-full bg-cyan-400/60" />
                <div className={`mt-2 h-1.5 w-14 rounded-full ${dark ? "bg-white/20" : "bg-blue-200"}`} />
              </motion.div>

              <motion.div
                animate={{ y: [0, -8, 0], x: [0, 5, 0] }}
                transition={{ duration: 3.5, repeat: Infinity }}
                className={`absolute left-[15%] top-12 rounded-2xl border p-4 text-cyan-400 shadow-xl backdrop-blur-xl ${theme.panel}`}
              >
                <Search size={24} />
              </motion.div>

              <motion.div
                animate={{ y: [0, 9, 0], x: [0, -4, 0] }}
                transition={{ duration: 4, repeat: Infinity }}
                className={`absolute bottom-9 right-[16%] rounded-2xl border p-4 text-violet-500 shadow-xl backdrop-blur-xl ${theme.panel}`}
              >
                <BrainCircuit size={25} />
              </motion.div>
            </div>
          </motion.section>

          {/* Right: Authentication Card (Login, Register, Forgot, Reset) */}
          <motion.section
            initial={{ opacity: 0, y: 25 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.1 }}
            className={`mx-auto w-full max-w-lg rounded-3xl border p-6 shadow-2xl backdrop-blur-2xl sm:p-9 ${theme.panel} ${
              dark ? "shadow-blue-950/30" : "shadow-blue-200/40"
            }`}
          >
            <div className="mb-6 text-center">
              <div className="mx-auto mb-3 inline-flex rounded-2xl bg-gradient-to-br from-cyan-400 to-blue-600 p-3 text-white shadow-lg shadow-cyan-500/20">
                <BrainCircuit size={28} />
              </div>
              <h2 className="text-2xl font-bold">
                {mode === "login" && t("authWelcomeBack", lang)}
                {mode === "register" && t("authTabRegister", lang)}
                {mode === "forgot" && t("authTabForgot", lang)}
                {mode === "reset" && t("authTabReset", lang)}
              </h2>
              <p className={`mt-1.5 text-xs sm:text-sm ${theme.muted}`}>
                {mode === "login" && t("authSignInSubtitle", lang)}
                {mode === "register" && t("authRoleNotice", lang)}
                {mode === "forgot" && t("authForgotDesc", lang)}
                {mode === "reset" && t("authResetSubmit", lang)}
              </p>
            </div>

            {/* Navigation Tabs (Login / Register) */}
            {(mode === "login" || mode === "register") && (
              <div className={`mb-6 grid grid-cols-2 border-b ${dark ? "border-white/10" : "border-slate-200"}`}>
                <button
                  type="button"
                  onClick={() => switchMode("login")}
                  className={`py-3 text-center text-sm font-semibold transition cursor-pointer ${
                    mode === "login"
                      ? "border-b-2 border-cyan-400 text-cyan-400"
                      : `${theme.muted} hover:text-cyan-400`
                  }`}
                >
                  {t("authTabSignIn", lang)}
                </button>
                <button
                  type="button"
                  onClick={() => switchMode("register")}
                  className={`py-3 text-center text-sm font-semibold transition cursor-pointer ${
                    mode === "register"
                      ? "border-b-2 border-cyan-400 text-cyan-400"
                      : `${theme.muted} hover:text-cyan-400`
                  }`}
                >
                  {t("authTabRegister", lang)}
                </button>
              </div>
            )}

            {/* Success Alert */}
            {successMsg && (
              <div className="mb-5 flex items-start gap-2.5 rounded-xl border border-emerald-400/30 bg-emerald-400/10 p-3 text-xs sm:text-sm text-emerald-400">
                <CheckCircle2 size={18} className="mt-0.5 shrink-0" />
                <div>
                  <p>{successMsg}</p>
                  {devResetToken && mode === "forgot" && (
                    <div className="mt-2 rounded-lg bg-black/40 p-2 text-xs font-mono">
                      <p className="text-amber-300 font-sans font-semibold mb-1">{t("authDemoNote", lang)}</p>
                      <p className="break-all text-cyan-300">Token: {devResetToken}</p>
                      <button
                        type="button"
                        onClick={() => {
                          setResetToken(devResetToken);
                          switchMode("reset");
                        }}
                        className="mt-2 inline-flex items-center gap-1 rounded bg-cyan-500/20 px-2.5 py-1 text-xs font-sans text-cyan-300 hover:bg-cyan-500/30 cursor-pointer"
                      >
                        <KeyRound size={13} /> {t("authTabReset", lang)} →
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Error Alert */}
            {error && (
              <div className="mb-5 flex items-start gap-2.5 rounded-xl border border-rose-400/30 bg-rose-400/10 p-3 text-xs sm:text-sm text-rose-400">
                <AlertCircle size={18} className="mt-0.5 shrink-0" />
                <p>{error}</p>
              </div>
            )}

            {/* ======================================================= */}
            {/* 1. SIGN IN FORM */}
            {/* ======================================================= */}
            {mode === "login" && (
              <form onSubmit={handleLogin} className="space-y-4">
                <div>
                  <label htmlFor="login-email" className="mb-1.5 block text-xs font-medium">
                    {t("authEmail", lang)}
                  </label>
                  <div className="relative">
                    <Mail className={`absolute left-4 top-1/2 -translate-y-1/2 ${theme.muted}`} size={17} />
                    <input
                      id="login-email"
                      type="email"
                      autoComplete="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder={t("authEmailPlaceholder", lang)}
                      className={`w-full rounded-xl border py-3 pl-11 pr-4 text-sm outline-none transition focus:ring-2 focus:ring-cyan-400/20 ${theme.field}`}
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="login-password" className="mb-1.5 block text-xs font-medium">
                    {t("authPassword", lang)}
                  </label>
                  <div className="relative">
                    <LockKeyhole className={`absolute left-4 top-1/2 -translate-y-1/2 ${theme.muted}`} size={17} />
                    <input
                      id="login-password"
                      type={showPassword ? "text" : "password"}
                      autoComplete="current-password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder={t("authPasswordPlaceholder", lang)}
                      className={`w-full rounded-xl border py-3 pl-11 pr-11 text-sm outline-none transition focus:ring-2 focus:ring-cyan-400/20 ${theme.field}`}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className={`absolute right-3.5 top-1/2 -translate-y-1/2 ${theme.muted} hover:text-cyan-400 cursor-pointer`}
                    >
                      {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                    </button>
                  </div>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
                  <label className="flex cursor-pointer items-center gap-2">
                    <input
                      type="checkbox"
                      checked={remember}
                      onChange={(e) => setRemember(e.target.checked)}
                      className="h-4 w-4 accent-cyan-500 rounded cursor-pointer"
                    />
                    {t("authRememberMe", lang)}
                  </label>
                  <button
                    type="button"
                    onClick={() => switchMode("forgot")}
                    className="font-medium text-cyan-400 hover:underline cursor-pointer"
                  >
                    {t("authForgotPasswordLink", lang)}
                  </button>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="flex w-full items-center justify-center gap-2.5 rounded-xl bg-gradient-to-r from-cyan-500 via-blue-500 to-violet-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-500/20 transition duration-300 hover:-translate-y-0.5 hover:shadow-cyan-500/30 disabled:opacity-50 cursor-pointer"
                >
                  {loading ? <Loader2 size={18} className="animate-spin" /> : <>{t("authSignInButton", lang)} <ArrowRight size={17} /></>}
                </button>
              </form>
            )}

            {/* ======================================================= */}
            {/* 2. REGISTRATION FORM */}
            {/* ======================================================= */}
            {mode === "register" && (
              <form onSubmit={handleRegister} className="space-y-4">
                <div>
                  <label htmlFor="reg-name" className="mb-1.5 block text-xs font-medium">
                    {t("authFullName", lang)}
                  </label>
                  <div className="relative">
                    <User className={`absolute left-4 top-1/2 -translate-y-1/2 ${theme.muted}`} size={17} />
                    <input
                      id="reg-name"
                      type="text"
                      required
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder={t("authFullNamePlaceholder", lang)}
                      className={`w-full rounded-xl border py-3 pl-11 pr-4 text-sm outline-none transition focus:ring-2 focus:ring-cyan-400/20 ${theme.field}`}
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="reg-email" className="mb-1.5 block text-xs font-medium">
                    {t("authEmail", lang)}
                  </label>
                  <div className="relative">
                    <Mail className={`absolute left-4 top-1/2 -translate-y-1/2 ${theme.muted}`} size={17} />
                    <input
                      id="reg-email"
                      type="email"
                      autoComplete="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder={t("authEmailPlaceholder", lang)}
                      className={`w-full rounded-xl border py-3 pl-11 pr-4 text-sm outline-none transition focus:ring-2 focus:ring-cyan-400/20 ${theme.field}`}
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="reg-password" className="mb-1.5 block text-xs font-medium">
                    {t("authPassword", lang)} (Min. 8 characters)
                  </label>
                  <div className="relative">
                    <LockKeyhole className={`absolute left-4 top-1/2 -translate-y-1/2 ${theme.muted}`} size={17} />
                    <input
                      id="reg-password"
                      type={showPassword ? "text" : "password"}
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder={t("authPasswordPlaceholder", lang)}
                      className={`w-full rounded-xl border py-3 pl-11 pr-11 text-sm outline-none transition focus:ring-2 focus:ring-cyan-400/20 ${theme.field}`}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className={`absolute right-3.5 top-1/2 -translate-y-1/2 ${theme.muted} hover:text-cyan-400 cursor-pointer`}
                    >
                      {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                    </button>
                  </div>
                </div>

                <div>
                  <label htmlFor="reg-confirm" className="mb-1.5 block text-xs font-medium">
                    {t("authConfirmPassword", lang)}
                  </label>
                  <div className="relative">
                    <LockKeyhole className={`absolute left-4 top-1/2 -translate-y-1/2 ${theme.muted}`} size={17} />
                    <input
                      id="reg-confirm"
                      type={showConfirmPassword ? "text" : "password"}
                      required
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder={t("authConfirmPasswordPlaceholder", lang)}
                      className={`w-full rounded-xl border py-3 pl-11 pr-11 text-sm outline-none transition focus:ring-2 focus:ring-cyan-400/20 ${theme.field}`}
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className={`absolute right-3.5 top-1/2 -translate-y-1/2 ${theme.muted} hover:text-cyan-400 cursor-pointer`}
                    >
                      {showConfirmPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="flex w-full items-center justify-center gap-2.5 rounded-xl bg-gradient-to-r from-cyan-500 via-blue-500 to-violet-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-500/20 transition duration-300 hover:-translate-y-0.5 hover:shadow-cyan-500/30 disabled:opacity-50 cursor-pointer"
                >
                  {loading ? <Loader2 size={18} className="animate-spin" /> : <>{t("authRegisterButton", lang)} <ArrowRight size={17} /></>}
                </button>
              </form>
            )}

            {/* ======================================================= */}
            {/* 3. FORGOT PASSWORD FORM */}
            {/* ======================================================= */}
            {mode === "forgot" && (
              <form onSubmit={handleForgotPassword} className="space-y-4">
                <div>
                  <label htmlFor="forgot-email" className="mb-1.5 block text-xs font-medium">
                    {t("authEmail", lang)}
                  </label>
                  <div className="relative">
                    <Mail className={`absolute left-4 top-1/2 -translate-y-1/2 ${theme.muted}`} size={17} />
                    <input
                      id="forgot-email"
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder={t("authEmailPlaceholder", lang)}
                      className={`w-full rounded-xl border py-3 pl-11 pr-4 text-sm outline-none transition focus:ring-2 focus:ring-cyan-400/20 ${theme.field}`}
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="flex w-full items-center justify-center gap-2.5 rounded-xl bg-gradient-to-r from-cyan-500 via-blue-500 to-violet-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-500/20 transition duration-300 hover:-translate-y-0.5 hover:shadow-cyan-500/30 disabled:opacity-50 cursor-pointer"
                >
                  {loading ? <Loader2 size={18} className="animate-spin" /> : <>{t("authForgotSubmit", lang)} <ArrowRight size={17} /></>}
                </button>

                <div className="flex items-center justify-between pt-2">
                  <button
                    type="button"
                    onClick={() => switchMode("login")}
                    className={`inline-flex items-center gap-1.5 text-xs ${theme.muted} hover:text-cyan-400 cursor-pointer`}
                  >
                    <ArrowLeft size={14} /> {t("authBackToLogin", lang)}
                  </button>
                  <button
                    type="button"
                    onClick={() => switchMode("reset")}
                    className="text-xs text-cyan-400 hover:underline cursor-pointer"
                  >
                    Have a token? {t("authTabReset", lang)}
                  </button>
                </div>
              </form>
            )}

            {/* ======================================================= */}
            {/* 4. RESET PASSWORD FORM */}
            {/* ======================================================= */}
            {mode === "reset" && (
              <form onSubmit={handleResetPassword} className="space-y-4">
                <div>
                  <label htmlFor="reset-token" className="mb-1.5 block text-xs font-medium">
                    {t("authResetToken", lang)}
                  </label>
                  <div className="relative">
                    <KeyRound className={`absolute left-4 top-1/2 -translate-y-1/2 ${theme.muted}`} size={17} />
                    <input
                      id="reset-token"
                      type="text"
                      required
                      value={resetToken}
                      onChange={(e) => setResetToken(e.target.value)}
                      placeholder={t("authResetTokenPlaceholder", lang)}
                      className={`w-full rounded-xl border py-3 pl-11 pr-4 text-sm font-mono outline-none transition focus:ring-2 focus:ring-cyan-400/20 ${theme.field}`}
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="reset-password" className="mb-1.5 block text-xs font-medium">
                    {t("authNewPassword", lang)}
                  </label>
                  <div className="relative">
                    <LockKeyhole className={`absolute left-4 top-1/2 -translate-y-1/2 ${theme.muted}`} size={17} />
                    <input
                      id="reset-password"
                      type={showPassword ? "text" : "password"}
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder={t("authNewPasswordPlaceholder", lang)}
                      className={`w-full rounded-xl border py-3 pl-11 pr-11 text-sm outline-none transition focus:ring-2 focus:ring-cyan-400/20 ${theme.field}`}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className={`absolute right-3.5 top-1/2 -translate-y-1/2 ${theme.muted} hover:text-cyan-400 cursor-pointer`}
                    >
                      {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                    </button>
                  </div>
                </div>

                <div>
                  <label htmlFor="reset-confirm" className="mb-1.5 block text-xs font-medium">
                    {t("authConfirmPassword", lang)}
                  </label>
                  <div className="relative">
                    <LockKeyhole className={`absolute left-4 top-1/2 -translate-y-1/2 ${theme.muted}`} size={17} />
                    <input
                      id="reset-confirm"
                      type={showConfirmPassword ? "text" : "password"}
                      required
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder={t("authConfirmPasswordPlaceholder", lang)}
                      className={`w-full rounded-xl border py-3 pl-11 pr-11 text-sm outline-none transition focus:ring-2 focus:ring-cyan-400/20 ${theme.field}`}
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className={`absolute right-3.5 top-1/2 -translate-y-1/2 ${theme.muted} hover:text-cyan-400 cursor-pointer`}
                    >
                      {showConfirmPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="flex w-full items-center justify-center gap-2.5 rounded-xl bg-gradient-to-r from-cyan-500 via-blue-500 to-violet-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-500/20 transition duration-300 hover:-translate-y-0.5 hover:shadow-cyan-500/30 disabled:opacity-50 cursor-pointer"
                >
                  {loading ? <Loader2 size={18} className="animate-spin" /> : <>{t("authResetSubmit", lang)} <ArrowRight size={17} /></>}
                </button>

                <div className="pt-2 text-center">
                  <button
                    type="button"
                    onClick={() => switchMode("login")}
                    className={`inline-flex items-center gap-1.5 text-xs ${theme.muted} hover:text-cyan-400 cursor-pointer`}
                  >
                    <ArrowLeft size={14} /> {t("authBackToLogin", lang)}
                  </button>
                </div>
              </form>
            )}

            {/* Security Badge */}
            <div className={`mt-6 flex items-center justify-center gap-2 text-xs ${theme.muted}`}>
              <ShieldCheck size={15} className="text-emerald-400" />
              <span>Bcrypt 12-round hashing & Bearer session security</span>
            </div>
          </motion.section>
        </div>

        <footer className={`mt-10 text-center text-xs ${theme.muted}`}>
          KnowledgeHub AI · Enterprise Confidential Document Intelligence · 2026
        </footer>
      </div>
    </div>
  );
}
