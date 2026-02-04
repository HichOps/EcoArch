"""Styles globaux et animations CSS pour l'application - Design Apple-like."""

# ===== ANIMATIONS CSS GLOBALES =====
GLOBAL_ANIMATIONS = """
/* Animations de base */
@keyframes pulse-success {
    0%, 100% { box-shadow: 0 0 0 0 rgba(52, 199, 89, 0.4); }
    50% { box-shadow: 0 0 0 12px rgba(52, 199, 89, 0); }
}

@keyframes pulse-error {
    0%, 100% { box-shadow: 0 0 0 0 rgba(255, 59, 48, 0.4); }
    50% { box-shadow: 0 0 0 12px rgba(255, 59, 48, 0); }
}

@keyframes fade-in-up {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}

@keyframes float {
    0%, 100% { transform: translateY(0px); }
    50% { transform: translateY(-6px); }
}

@keyframes glow {
    0%, 100% { box-shadow: 0 0 20px rgba(0, 122, 255, 0.2); }
    50% { box-shadow: 0 0 30px rgba(0, 122, 255, 0.4); }
}

/* Import police système Apple */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Variables CSS personnalisées */
:root {
    --apple-blue: #007AFF;
    --apple-green: #34C759;
    --apple-red: #FF3B30;
    --apple-orange: #FF9500;
    --apple-yellow: #FFCC00;
    --apple-purple: #AF52DE;
    --apple-pink: #FF2D55;
    --apple-teal: #5AC8FA;
    --apple-indigo: #5856D6;
    
    --glass-bg: rgba(255, 255, 255, 0.72);
    --glass-border: rgba(255, 255, 255, 0.18);
    --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.04);
    --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.08);
    --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.12);
    --shadow-xl: 0 16px 48px rgba(0, 0, 0, 0.16);
    
    --transition-fast: 0.15s ease;
    --transition-normal: 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    --transition-slow: 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --radius-xl: 24px;
    --radius-full: 9999px;
}

/* Mode sombre */
.dark {
    --glass-bg: rgba(30, 30, 30, 0.72);
    --glass-border: rgba(255, 255, 255, 0.08);
}

/* Styles de base */
* {
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, sans-serif;
}

/* Scrollbar personnalisée style Apple */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: transparent;
}

::-webkit-scrollbar-thumb {
    background: rgba(0, 0, 0, 0.2);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: rgba(0, 0, 0, 0.3);
}

.dark ::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.2);
}

.dark ::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.3);
}

/* Glass morphism utilities */
.glass-card {
    background: var(--glass-bg);
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid var(--glass-border);
    border-radius: var(--radius-xl);
}

.glass-subtle {
    background: rgba(255, 255, 255, 0.5);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
}

.dark .glass-subtle {
    background: rgba(255, 255, 255, 0.05);
}

/* Hover effects */
.hover-lift {
    transition: transform var(--transition-normal), box-shadow var(--transition-normal);
}

.hover-lift:hover {
    transform: translateY(-4px);
    box-shadow: var(--shadow-lg);
}

.hover-scale {
    transition: transform var(--transition-fast);
}

.hover-scale:hover {
    transform: scale(1.02);
}

.hover-glow:hover {
    box-shadow: 0 0 24px rgba(0, 122, 255, 0.25);
}

/* Button styles Apple-like */
.btn-apple {
    font-weight: 600;
    letter-spacing: -0.01em;
    transition: all var(--transition-fast);
}

.btn-apple:active {
    transform: scale(0.98);
}

/* Badge glow effect */
.badge-glow-green {
    animation: pulse-success 2s infinite;
}

.badge-glow-red {
    animation: pulse-error 2s infinite;
}

/* Fade in animation for cards */
.animate-in {
    animation: fade-in-up 0.5s ease-out;
}

/* Terminal styles */
.terminal-glow {
    box-shadow: 0 0 40px rgba(52, 199, 89, 0.15), inset 0 0 60px rgba(0, 0, 0, 0.3);
}

/* Tab styles */
.rt-TabsTrigger {
    font-weight: 500 !important;
    letter-spacing: -0.01em !important;
}

/* Select styles */
.rt-SelectTrigger {
    font-weight: 500 !important;
}

/* Input focus glow */
.rt-TextFieldInput:focus {
    box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.2) !important;
}

/* Card subtle gradient */
.gradient-subtle {
    background: linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(255,255,255,0.7) 100%);
}

.dark .gradient-subtle {
    background: linear-gradient(135deg, rgba(45,45,45,0.9) 0%, rgba(35,35,35,0.7) 100%);
}
"""

# ===== PALETTE DE COULEURS APPLE =====
APPLE_BLUE = "#007AFF"
APPLE_GREEN = "#34C759"
APPLE_RED = "#FF3B30"
APPLE_ORANGE = "#FF9500"
APPLE_YELLOW = "#FFCC00"
APPLE_PURPLE = "#AF52DE"
APPLE_PINK = "#FF2D55"
APPLE_TEAL = "#5AC8FA"
APPLE_INDIGO = "#5856D6"

# Couleurs pour les graphiques
CHART_COLORS = {
    "Compute": APPLE_BLUE,
    "SQL": APPLE_PURPLE,
    "Storage": APPLE_ORANGE,
    "Network": APPLE_TEAL,
    "Autre": APPLE_PINK,
}

# Terminal colors
TERMINAL_GREEN = "#32D74B"
TERMINAL_BG = "#1D1D1F"