/**
 * KnowledgeHub AI - Centralized Localization Module (i18n)
 * Full translation dictionaries for English (en), Tamil (ta), and Hindi (hi).
 */

export const SUPPORTED_LANGUAGES = [
  { code: "en", label: "English", nativeName: "English", speechLang: "en-US" },
  { code: "ta", label: "Tamil", nativeName: "தமிழ்", speechLang: "ta-IN" },
  { code: "hi", label: "Hindi", nativeName: "हिन्दी", speechLang: "hi-IN" },
];

export const translations = {
  en: {
    // Brand & App
    appName: "KnowledgeHub AI",
    appSubtitle: "Your company knowledge, powered by AI",
    tagline: "Turn documents into intelligence.",
    taglineDesc: "Search, discover and get useful answers from your company documents in one intelligent workspace.",

    // Navigation
    navDashboard: "Dashboard",
    navKnowledgeBase: "Knowledge Base",
    navAIAssistant: "AI Assistant",
    navActivity: "Activity",
    navSettings: "Settings",
    navSignOut: "Sign Out",
    navLightMode: "Light mode",
    navDarkMode: "Dark mode",

    // Dashboard Stats
    statTotalDocs: "Total Documents",
    statIndexedChunks: "Indexed Chunks",
    statVectorCount: "Vector Embeddings",
    statFailedIngestion: "Failed Ingestion",
    statRAGEngine: "Cohere RAG Engine",
    statReady: "Operational",

    // Common Actions
    addDocument: "Add Document",
    uploading: "Uploading...",
    searchDocsPlaceholder: "Search documents by name or keyword...",
    viewDocument: "Preview",
    downloadDocument: "Download",
    reindex: "Re-index",
    delete: "Delete",
    refresh: "Refresh",
    cancel: "Cancel",
    submit: "Submit",
    save: "Save Changes",
    close: "Close",

    // Document Status
    statusIndexed: "Indexed",
    statusProcessing: "Processing",
    statusFailed: "Failed",
    statusUploaded: "Uploaded",
    pages: "pages",
    chunks: "chunks",

    // Auth - Common
    authWelcomeBack: "Welcome back!",
    authSignInSubtitle: "Sign in to access your confidential workspace.",
    authTabSignIn: "Sign In",
    authTabRegister: "Create Account",
    authTabForgot: "Forgot Password",
    authTabReset: "Reset Password",
    authEmail: "Email Address",
    authEmailPlaceholder: "you@company.com",
    authPassword: "Password",
    authPasswordPlaceholder: "Enter your password",
    authRememberMe: "Remember me",
    authForgotPasswordLink: "Forgot password?",
    authSignInButton: "Sign In",
    authRegisterButton: "Create Account",
    authFullName: "Full Name",
    authFullNamePlaceholder: "Jane Doe",
    authConfirmPassword: "Confirm Password",
    authConfirmPasswordPlaceholder: "Re-enter your password",
    authRoleNotice: "New accounts are granted Viewer access by default.",
    authForgotDesc: "Enter your email address to receive password recovery instructions.",
    authForgotSubmit: "Generate Reset Token",
    authResetToken: "Reset Token",
    authResetTokenPlaceholder: "Paste your reset token here",
    authNewPassword: "New Password",
    authNewPasswordPlaceholder: "Enter new password (min. 8 characters)",
    authResetSubmit: "Reset Password",
    authBackToLogin: "Back to Sign In",
    authDemoNote: "Local development mode: password reset token is provided directly on this screen for easy demonstration.",

    // Auth Validation & Messages
    errFillAll: "Please fill in all required fields.",
    errPasswordLength: "Password must be at least 8 characters.",
    errPasswordMatch: "Passwords do not match.",
    errInvalidEmail: "Please provide a valid corporate email address.",
    errLoginFailed: "Invalid email address or password.",
    msgRegSuccess: "Account created successfully! You are now signed in.",
    msgResetSuccess: "Password updated successfully. Please sign in with your new password.",

    // AI Assistant
    assistantTitle: "AI Document Assistant",
    assistantSubtitle: "Retrieval-Augmented Generation with exact citations",
    assistantWelcome: "Hello! I am your KnowledgeHub AI Document Assistant. Ask me anything about your uploaded company documents, policies, or manuals.",
    assistantPlaceholder: "Ask a question about your documents...",
    assistantSourceFilter: "Source Filter",
    assistantAllSources: "All Documents (Auto-detect)",
    assistantClear: "Clear Chat",
    assistantLanguage: "Response Language",
    assistantSuggestedHeading: "Suggested Queries",
    assistantSourcesHeading: "Sources Cited",
    assistantPage: "Page",
    assistantSending: "Searching & Generating...",
    assistantNoEvidence: "I cannot find the answer to this question in the provided company documents.",

    // Voice Input & Output
    voiceMicStart: "Click to speak (Voice input)",
    voiceMicListening: "Listening... Speak now",
    voiceMicStop: "Stop recording",
    voiceMicUnsupported: "Speech recognition is not supported in this browser.",
    voiceMicDenied: "Microphone permission was denied. Please allow microphone access.",
    voicePlay: "Read aloud",
    voiceStop: "Stop speaking",
    voiceAutoRead: "Auto-read responses",
    voiceAutoReadDesc: "Automatically read AI answers aloud when generated",
    voiceRate: "Speech Speed",
    voicePitch: "Speech Pitch",
    voiceTest: "Test Voice Playback",
    voiceTestPhrase: "KnowledgeHub AI voice synthesis is operating correctly.",
    voiceUnsupportedTTS: "Text-to-speech is not supported in this browser.",

    // Settings Page
    settingsTitle: "System & User Settings",
    settingsSubtitle: "Configure application language, voice preferences, and system parameters.",
    settingsSectionLanguage: "Language & Regional Settings",
    settingsLanguageDesc: "Select the display language for user interface and AI responses.",
    settingsSectionVoice: "Voice & Speech Synthesis",
    settingsVoiceDesc: "Configure speech recognition and text-to-speech parameters.",
    settingsSectionAI: "AI & RAG Engine Parameters",
    settingsSectionDiag: "System Diagnostics & Connectivity",
    settingsSectionProfile: "Active User Profile",
    settingsRole: "Current Role",
    settingsUserId: "User ID",
    settingsDbStatus: "SQLite Database",
    settingsVectorStatus: "ChromaDB Vector Store",
    settingsConnected: "Connected",

    // Activity Page
    activityTitle: "System Audit & Ingestion Log",
    activitySubtitle: "Real-time records of document processing and vectorization events.",
    activityEmpty: "No activity records found.",

    // Knowledge Base Page
    kbTitle: "Enterprise Knowledge Base",
    kbSubtitle: "Manage and inspect indexed company files and source citations.",
    kbDropzone: "Click to upload or drag and drop PDF / DOCX files (max 25MB).",
    kbEmpty: "No documents have been indexed yet.",
  },

  ta: {
    // Brand & App
    appName: "KnowledgeHub AI",
    appSubtitle: "செயற்கை நுண்ணறிவுடன் உங்கள் நிறுவன ஆவணங்கள்",
    tagline: "ஆவணங்களை அறிவாக மாற்றுங்கள்.",
    taglineDesc: "உங்கள் நிறுவனத்தின் ஆவணங்களிலிருந்து தகவல்களைத் தேடி, பயனுள்ள பதில்களை ஒரே இடத்தில் பெறுங்கள்.",

    // Navigation
    navDashboard: "முகப்பு பலகை",
    navKnowledgeBase: "ஆவண களஞ்சியம்",
    navAIAssistant: "AI உதவியாளர்",
    navActivity: "நடவடிக்கைகள்",
    navSettings: "அமைப்புகள்",
    navSignOut: "வெளியேறு",
    navLightMode: "பகல் பயன்முறை",
    navDarkMode: "இரவு பயன்முறை",

    // Dashboard Stats
    statTotalDocs: "மொத்த ஆவணங்கள்",
    statIndexedChunks: "பதிவேற்றப்பட்ட பகுதிகள்",
    statVectorCount: "வெக்டர் பதிவுகள்",
    statFailedIngestion: "தோல்வியடைந்த ஆவணங்கள்",
    statRAGEngine: "Cohere RAG இயந்திரம்",
    statReady: "செயல்பாட்டில் உள்ளது",

    // Common Actions
    addDocument: "ஆவணம் சேர்க்க",
    uploading: "பதிவேற்றுகிறது...",
    searchDocsPlaceholder: "ஆவணத்தின் பெயரைத் தட்டச்சு செய்து தேடுங்கள்...",
    viewDocument: "முன்னோட்டம்",
    downloadDocument: "பதிவிறக்கு",
    reindex: "மீண்டும் அட்டவணைப்படுத்து",
    delete: "நீக்கு",
    refresh: "புதுப்பி",
    cancel: "ரத்து செய்",
    submit: "சமர்ப்பி",
    save: "மாற்றங்களைச் சேமி",
    close: "மூடு",

    // Document Status
    statusIndexed: "இணைக்கப்பட்டது",
    statusProcessing: "செயலாக்கத்தில் உள்ளது",
    statusFailed: "தோல்வி",
    statusUploaded: "பதிவேற்றப்பட்டது",
    pages: "பக்கங்கள்",
    chunks: "பகுதிகள்",

    // Auth - Common
    authWelcomeBack: "மீண்டும் வருக!",
    authSignInSubtitle: "உங்கள் பாதுகாப்பான பணியிடத்திற்கு உள்நுழையவும்.",
    authTabSignIn: "உள்நுழைவு",
    authTabRegister: "கணக்கு தொடங்கு",
    authTabForgot: "கடவுச்சொல் மறந்ததா",
    authTabReset: "கடவுச்சொல் மாற்று",
    authEmail: "மின்னஞ்சல் முகவரி",
    authEmailPlaceholder: "you@company.com",
    authPassword: "கடவுச்சொல்",
    authPasswordPlaceholder: "உங்கள் கடவுச்சொல்லை உள்ளிடவும்",
    authRememberMe: "என்னை நினைவில் கொள்",
    authForgotPasswordLink: "கடவுச்சொல் மறந்துவிட்டதா?",
    authSignInButton: "உள்நுழைக",
    authRegisterButton: "புதிய கணக்கை உருவாக்கு",
    authFullName: "முழு பெயர்",
    authFullNamePlaceholder: "உங்கள் பெயர்",
    authConfirmPassword: "கடவுச்சொல்லை உறுதிப்படுத்து",
    authConfirmPasswordPlaceholder: "கடவுச்சொல்லை மீண்டும் உள்ளிடவும்",
    authRoleNotice: "புதிய கணக்குகளுக்கு பார்வையாளர் (Viewer) அனுமதி மட்டுமே வழங்கப்படும்.",
    authForgotDesc: "கடவுச்சொல்லை மீட்டமைக்க உங்கள் பதிவுசெய்த மின்னஞ்சல் முகவரியை உள்ளிடவும்.",
    authForgotSubmit: "மீட்டமைப்பு குறியீட்டை உருவாக்கு",
    authResetToken: "மீட்டமைப்பு குறியீடு (Token)",
    authResetTokenPlaceholder: "உங்கள் குறியீட்டை இங்கே ஒட்டவும்",
    authNewPassword: "புதிய கடவுச்சொல்",
    authNewPasswordPlaceholder: "புதிய கடவுச்சொல்லை உள்ளிடவும் (குறைந்தது 8 எழுத்துகள்)",
    authResetSubmit: "கடவுச்சொல்லை மாற்று",
    authBackToLogin: "உள்நுழைவிற்குத் திரும்பு",
    authDemoNote: "டெவலப்மென்ட் பயன்முறை: கடவுச்சொல் மீட்டமைப்பு குறியீடு இந்த திரையிலேயே காட்டப்பட்டுள்ளது.",

    // Auth Validation & Messages
    errFillAll: "அனைத்து புலங்களையும் நிரப்பவும்.",
    errPasswordLength: "கடவுச்சொல் குறைந்தது 8 எழுத்துகளைக் கொண்டிருக்க வேண்டும்.",
    errPasswordMatch: "கடவுச்சொற்கள் பொருந்தவில்லை.",
    errInvalidEmail: "சரியான மின்னஞ்சல் முகவரியை உள்ளிடவும்.",
    errLoginFailed: "தவறான மின்னஞ்சல் அல்லது கடவுச்சொல்.",
    msgRegSuccess: "கணக்கு வெற்றிகரமாக உருவாக்கப்பட்டது! நீங்கள் உள்நுழைந்துள்ளீர்கள்.",
    msgResetSuccess: "கடவுச்சொல் வெற்றிகரமாக மாற்றப்பட்டது. புதிய கடவுச்சொல்லுடன் உள்நுழையவும்.",

    // AI Assistant
    assistantTitle: "AI ஆவண உதவியாளர்",
    assistantSubtitle: "துல்லியமான சான்றுகளுடன் கூடிய பதில்கள்",
    assistantWelcome: "வணக்கம்! நான் உங்கள் KnowledgeHub AI ஆவண உதவியாளர். பதிவேற்றிய நிறுவன ஆவணங்கள் பற்றி என்னிடம் கேளுங்கள்.",
    assistantPlaceholder: "உங்கள் ஆவணங்கள் பற்றி ஒரு கேள்வியைக் கேளுங்கள்...",
    assistantSourceFilter: "ஆவண வடிகட்டி",
    assistantAllSources: "அனைத்து ஆவணங்களும் (தானியங்கு)",
    assistantClear: "அரட்டையை அழி",
    assistantLanguage: "பதில் மொழி",
    assistantSuggestedHeading: "பரிந்துரைக்கப்பட்ட கேள்விகள்",
    assistantSourcesHeading: "குறிப்பிடப்பட்ட ஆதாரங்கள்",
    assistantPage: "பக்கம்",
    assistantSending: "தேடுகிறது மற்றும் பதில் உருவாக்குகிறது...",
    assistantNoEvidence: "வழங்கப்பட்ட நிறுவன ஆவணங்களில் இந்தக் கேள்விக்கான பதிலை என்னால் கண்டுபிடிக்க முடியவில்லை.",

    // Voice Input & Output
    voiceMicStart: "பேச கிளிக் செய்யவும் (குரல் உள்ளீடு)",
    voiceMicListening: "கேட்கிறது... இப்போது பேசுங்கள்",
    voiceMicStop: "பதிவை நிறுத்து",
    voiceMicUnsupported: "உங்கள் உலாவியில் குரல் அறிதல் ஆதரிக்கப்படவில்லை.",
    voiceMicDenied: "மைக்ரோஃபோன் அனுமதி மறுக்கப்பட்டது. தயவுசெய்து அணுகலை அனுமதிக்கவும்.",
    voicePlay: "சத்தமாகப் படி",
    voiceStop: "நிறுத்து",
    voiceAutoRead: "பதில்களை தானாகப் படி",
    voiceAutoReadDesc: "AI பதில்கள் உருவானவுடன் தானாகவே சத்தமாகப் படிக்கும்",
    voiceRate: "பேச்சு வேகம்",
    voicePitch: "பேச்சு தொனி",
    voiceTest: "குரல் பரிசோதனை",
    voiceTestPhrase: "KnowledgeHub AI தமிழ் குரல் சரியாகச் செயல்படுகிறது.",
    voiceUnsupportedTTS: "உங்கள் உலாவியில் உரை-பேச்சு (TTS) ஆதரிக்கப்படவில்லை.",

    // Settings Page
    settingsTitle: "கணினி & பயனர் அமைப்புகள்",
    settingsSubtitle: "பயன்பாட்டு மொழி, குரல் விருப்பங்கள் மற்றும் கணினி அமைப்புகளை நிர்வகிக்கவும்.",
    settingsSectionLanguage: "மொழி அமைப்புகள்",
    settingsLanguageDesc: "இடைமுகம் மற்றும் AI பதில்களுக்கான மொழியைத் தேர்வுசெய்யவும்.",
    settingsSectionVoice: "குரல் மற்றும் பேச்சு அமைப்புகள்",
    settingsVoiceDesc: "குரல் உள்ளீடு மற்றும் பேச்சு அளவுருக்களை நிர்வகிக்கவும்.",
    settingsSectionAI: "AI மற்றும் RAG அளவுருக்கள்",
    settingsSectionDiag: "கணினி கண்டறிதல் மற்றும் இணைப்பு",
    settingsSectionProfile: "தற்போதைய பயனர் விபரம்",
    settingsRole: "தற்போதைய பங்கு (Role)",
    settingsUserId: "பயனர் எண்",
    settingsDbStatus: "SQLite தரவுத்தளம்",
    settingsVectorStatus: "ChromaDB வெக்டர் களஞ்சியம்",
    settingsConnected: "இணைக்கப்பட்டுள்ளது",

    // Activity Page
    activityTitle: "கணினி தணிக்கை மற்றும் செயல்பாட்டுப் பதிவு",
    activitySubtitle: "ஆவண செயலாக்கம் மற்றும் வெக்டரைசேஷன் நிகழ்வுகளின் நேரடிப் பதிவு.",
    activityEmpty: "நடவடிக்கைகள் ஏதும் இல்லை.",

    // Knowledge Base Page
    kbTitle: "நிறுவன அறிவு களஞ்சியம்",
    kbSubtitle: "நிறுவன ஆவணங்களையும் அவற்றின் மூல ஆதாரங்களையும் நிர்வகிக்கவும்.",
    kbDropzone: "PDF அல்லது DOCX கோப்புகளைப் பதிவேற்ற இங்கே கிளிக் செய்யவும் (அதிகபட்சம் 25MB).",
    kbEmpty: "ஆவணங்கள் எதுவும் இதுவரை இணைக்கப்படவில்லை.",
  },

  hi: {
    // Brand & App
    appName: "KnowledgeHub AI",
    appSubtitle: "एआई द्वारा संचालित आपकी कंपनी का ज्ञान आधार",
    tagline: "दस्तावेज़ों को ज्ञान में बदलें।",
    taglineDesc: "एक ही कार्यक्षेत्र में अपनी कंपनी के दस्तावेज़ों से तुरंत सटीक और विश्वसनीय उत्तर प्राप्त करें।",

    // Navigation
    navDashboard: "डैशबोर्ड",
    navKnowledgeBase: "ज्ञान आधार",
    navAIAssistant: "एआई सहायक",
    navActivity: "गतिविधियाँ",
    navSettings: "सेटिंग्स",
    navSignOut: "साइन आउट",
    navLightMode: "लाइट मोड",
    navDarkMode: "डार्क मोड",

    // Dashboard Stats
    statTotalDocs: "कुल दस्तावेज़",
    statIndexedChunks: "अनुक्रमित अंश",
    statVectorCount: "वेक्टर एम्बेडिंग",
    statFailedIngestion: "विफल दस्तावेज़",
    statRAGEngine: "Cohere RAG इंजन",
    statReady: "सक्रिय और तैयार",

    // Common Actions
    addDocument: "दस्तावेज़ जोड़ें",
    uploading: "अपलोड हो रहा है...",
    searchDocsPlaceholder: "दस्तावेज़ के नाम या कीवर्ड से खोजें...",
    viewDocument: "पूर्वावलोकन",
    downloadDocument: "डाउनलोड",
    reindex: "पुनः अनुक्रमित करें",
    delete: "हटाएं",
    refresh: "रिफ्रेश करें",
    cancel: "रद्द करें",
    submit: "जमा करें",
    save: "परिवर्तन सहेजें",
    close: "बंद करें",

    // Document Status
    statusIndexed: "अनुक्रमित",
    statusProcessing: "प्रक्रियाधीन",
    statusFailed: "विफल",
    statusUploaded: "अपलोड किया गया",
    pages: "पृष्ठ",
    chunks: "अंश",

    // Auth - Common
    authWelcomeBack: "वापसी पर स्वागत है!",
    authSignInSubtitle: "अपने सुरक्षित कार्यक्षेत्र में प्रवेश करने के लिए साइन इन करें।",
    authTabSignIn: "साइन इन",
    authTabRegister: "खाता बनाएं",
    authTabForgot: "पासवर्ड भूल गए",
    authTabReset: "पासवर्ड रीसेट",
    authEmail: "ईमेल पता",
    authEmailPlaceholder: "you@company.com",
    authPassword: "पासवर्ड",
    authPasswordPlaceholder: "अपना पासवर्ड दर्ज करें",
    authRememberMe: "मुझे याद रखें",
    authForgotPasswordLink: "पासवर्ड भूल गए?",
    authSignInButton: "साइन इन करें",
    authRegisterButton: "नया खाता बनाएं",
    authFullName: "पूरा नाम",
    authFullNamePlaceholder: "अपना नाम दर्ज करें",
    authConfirmPassword: "पासवर्ड की पुष्टि करें",
    authConfirmPasswordPlaceholder: "पासवर्ड पुनः दर्ज करें",
    authRoleNotice: "नए खातों को डिफ़ॉल्ट रूप से केवल दर्शक (Viewer) की भूमिका दी जाती है।",
    authForgotDesc: "पासवर्ड रीसेट करने के लिए अपना पंजीकृत ईमेल पता दर्ज करें।",
    authForgotSubmit: "रीसेट टोकन प्राप्त करें",
    authResetToken: "रीसेट टोकन",
    authResetTokenPlaceholder: "यहाँ अपना टोकन पेस्ट करें",
    authNewPassword: "नया पासवर्ड",
    authNewPasswordPlaceholder: "नया पासवर्ड दर्ज करें (न्यूनतम 8 वर्ण)",
    authResetSubmit: "पासवर्ड रीसेट करें",
    authBackToLogin: "साइन इन पर वापस जाएं",
    authDemoNote: "डेवलपमेंट मोड: पासवर्ड रीसेट टोकन परीक्षण के लिए सीधे इसी स्क्रीन पर प्रदान किया गया है।",

    // Auth Validation & Messages
    errFillAll: "कृपया सभी आवश्यक फ़ील्ड भरें।",
    errPasswordLength: "पासवर्ड कम से कम 8 वर्णों का होना चाहिए।",
    errPasswordMatch: "पासवर्ड मेल नहीं खाते।",
    errInvalidEmail: "कृपया एक मान्य कंपनी ईमेल पता दर्ज करें।",
    errLoginFailed: "अमान्य ईमेल पता या पासवर्ड।",
    msgRegSuccess: "खाता सफलतापूर्वक बनाया गया! आप साइन इन हैं।",
    msgResetSuccess: "पासवर्ड सफलतापूर्वक अपडेट किया गया। कृपया नए पासवर्ड से साइन इन करें।",

    // AI Assistant
    assistantTitle: "एआई दस्तावेज़ सहायक",
    assistantSubtitle: "सटीक उद्धरणों के साथ ज्ञान-आधारित उत्तर",
    assistantWelcome: "नमस्ते! मैं आपका KnowledgeHub AI दस्तावेज़ सहायक हूँ। अपनी कंपनी की नीतियों या दस्तावेज़ों के बारे में मुझसे कुछ भी पूछें।",
    assistantPlaceholder: "अपने दस्तावेज़ों के बारे में प्रश्न पूछें...",
    assistantSourceFilter: "स्रोत फ़िल्टर",
    assistantAllSources: "सभी दस्तावेज़ (स्वतः पहचान)",
    assistantClear: "चैट साफ़ करें",
    assistantLanguage: "उत्तर की भाषा",
    assistantSuggestedHeading: "सुझाए गए प्रश्न",
    assistantSourcesHeading: "संदर्भित स्रोत",
    assistantPage: "पृष्ठ",
    assistantSending: "खोज रहा है और उत्तर तैयार कर रहा है...",
    assistantNoEvidence: "प्रदान किए गए कंपनी दस्तावेज़ों में मुझे इस प्रश्न का उत्तर नहीं मिला।",

    // Voice Input & Output
    voiceMicStart: "बोलने के लिए क्लिक करें (आवाज इनपुट)",
    voiceMicListening: "सुन रहा हूँ... अब बोलें",
    voiceMicStop: "रिकॉर्डिंग रोकें",
    voiceMicUnsupported: "इस ब्राउज़र में वाक् पहचान (Speech Recognition) समर्थित नहीं है।",
    voiceMicDenied: "माइक्रोफ़ोन की अनुमति अस्वीकृत की गई। कृपया माइक्रोफ़ोन की अनुमति दें।",
    voicePlay: "बोलकर सुनाएं",
    voiceStop: "रोकें",
    voiceAutoRead: "उत्तर स्वतः पढ़ें",
    voiceAutoReadDesc: "एआई उत्तर उत्पन्न होने पर स्वतः बोलकर सुनाएं",
    voiceRate: "बोलने की गति",
    voicePitch: "आवाज़ का स्तर",
    voiceTest: "आवाज़ का परीक्षण",
    voiceTestPhrase: "KnowledgeHub AI हिंदी आवाज़ संश्लेषण सही ढंग से काम कर रहा है।",
    voiceUnsupportedTTS: "इस ब्राउज़र में टेक्स्ट-टू-स्पीच समर्थित नहीं है।",

    // Settings Page
    settingsTitle: "सिस्टम और उपयोगकर्ता सेटिंग्स",
    settingsSubtitle: "इंटरफ़ेस भाषा, आवाज़ प्राथमिकताएं और सिस्टम पैरामीटर कॉन्फ़िगर करें।",
    settingsSectionLanguage: "भाषा और क्षेत्रीय सेटिंग्स",
    settingsLanguageDesc: "यूजर इंटरफेस और एआई प्रतिक्रियाओं के लिए भाषा चुनें।",
    settingsSectionVoice: "आवाज़ और वाक् प्राथमिकताएं",
    settingsVoiceDesc: "माइक्रोफ़ोन इनपुट और टेक्स्ट-टू-स्पीच सेटिंग्स प्रबंधित करें।",
    settingsSectionAI: "एआई और RAG इंजन पैरामीटर",
    settingsSectionDiag: "सिस्टम डायग्नोस्टिक्स और कनेक्टिविटी",
    settingsSectionProfile: "सक्रिय उपयोगकर्ता प्रोफ़ाइल",
    settingsRole: "वर्तमान भूमिका",
    settingsUserId: "उपयोगकर्ता आईडी",
    settingsDbStatus: "SQLite डेटाबेस",
    settingsVectorStatus: "ChromaDB वेक्टर स्टोर",
    settingsConnected: "कनेक्टेड",

    // Activity Page
    activityTitle: "सिस्टम ऑडिट और गतिविधि लॉग",
    activitySubtitle: "दस्तावेज़ प्रसंस्करण और वेक्टराइजेशन घटनाओं का रीयल-टाइम रिकॉर्ड।",
    activityEmpty: "कोई गतिविधि रिकॉर्ड नहीं मिला।",

    // Knowledge Base Page
    kbTitle: "एंटरप्राइज़ ज्ञान आधार",
    kbSubtitle: "अनुक्रमित कंपनी फ़ाइलों और स्रोतों का प्रबंधन करें।",
    kbDropzone: "PDF या DOCX फ़ाइलें अपलोड करने के लिए यहाँ क्लिक करें (अधिकतम 25MB)।",
    kbEmpty: "अभी तक कोई दस्तावेज़ अनुक्रमित नहीं किया गया है।",
  },
};

/**
 * Returns a translation string with optional fallback
 */
export function t(key, lang = "en") {
  const selectedDict = translations[lang] || translations["en"];
  if (selectedDict && selectedDict[key] !== undefined) {
    return selectedDict[key];
  }
  return translations["en"]?.[key] || key;
}
