/**
 * src/app/App.tsx
 *
 * Root application shell.
 * - Wraps the app in AuthProvider (JWT context)
 * - Manages screen routing via simple state machine
 * - Guards authenticated screens → redirects to /login if no token
 * - Redirects authenticated users away from landing/login/register
 */

import { useEffect, useState, useCallback } from "react";
import Navbar from "../components/Navbar";
import Sidebar from "../components/Sidebar";
import Landing from "../screens/Landing";
import Dashboard from "../pages/Dashboard";
import CreateInterview from "../pages/CreateInterview";
import InterviewResult from "../pages/InterviewResult";
import AnalyticsPage from "../pages/Analytics";
import Login from "../pages/Login";
import Register from "../pages/Register";
import TextInterview from "../screens/TextInterview";
import VoiceInterview from "../screens/VoiceInterview";
import { AuthProvider, useAuth } from "../context/AuthContext";
import { AUTHENTICATED_SCREENS, type Screen } from "../types";

// ── Session state passed between screens ─────────────────────────────

interface SessionState {
  interviewId?: string;
}

// ── Router: maps screen → component ─────────────────────────────────

function renderScreen(
  screen: Screen,
  onNavigate: (s: Screen, state?: SessionState) => void,
  sessionState: SessionState,
  dark: boolean,
) {
  switch (screen) {
    case "landing":          return <Landing onNavigate={onNavigate} />;
    case "login":            return <Login onNavigate={onNavigate} />;
    case "register":         return <Register onNavigate={onNavigate} />;
    case "dashboard":        return <Dashboard onNavigate={onNavigate} dark={dark} />;
    case "create-interview": return <CreateInterview onNavigate={onNavigate} />;
    case "text-interview":   return <TextInterview onNavigate={onNavigate} interviewId={sessionState.interviewId} />;
    case "voice-interview":  return <VoiceInterview onNavigate={onNavigate} interviewId={sessionState.interviewId} />;
    case "results":          return <InterviewResult onNavigate={onNavigate} dark={dark} interviewId={sessionState.interviewId} />;
    case "analytics":        return <AnalyticsPage onNavigate={onNavigate} dark={dark} />;
  }
}

// ── Inner app shell (has access to AuthContext) ──────────────────────

function AppInner() {
  const { isAuthenticated, isLoading, logout } = useAuth();
  const [screen, setScreen] = useState<Screen>("landing");
  const [sessionState, setSessionState] = useState<SessionState>({});
  const dark = true;

  // Force dark mode on <html>
  useEffect(() => {
    document.documentElement.classList.add("dark");
  }, []);

  // Authenticated user tries to view public screens → dashboard
  useEffect(() => {
    if (!isLoading && isAuthenticated && ["landing", "login", "register"].includes(screen)) {
      setScreen("dashboard");
    }
  }, [isAuthenticated, isLoading, screen]);

  // Unauthenticated user tries to view protected screen → login
  useEffect(() => {
    if (!isLoading && !isAuthenticated && AUTHENTICATED_SCREENS.includes(screen)) {
      setScreen("login");
    }
  }, [isAuthenticated, isLoading, screen]);

  // Navigate with optional session state payload
  const navigate = useCallback((s: Screen, state?: SessionState) => {
    if (state) setSessionState(state);
    setScreen(s);
  }, []);

  // Navbar navigate: sign out if user goes to landing while authenticated
  const handleNavbarNavigate = useCallback((s: Screen) => {
    if (s === "landing" && isAuthenticated) {
      logout();
    }
    navigate(s);
  }, [isAuthenticated, logout, navigate]);

  const showSidebar = AUTHENTICATED_SCREENS.includes(screen);

  // Global loading spinner (waiting for token → profile fetch)
  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <span className="inline-block h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          <p className="text-xs text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
            Loading PrepAI…
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      className="flex h-screen flex-col overflow-hidden bg-background text-foreground"
      style={{ fontFamily: "var(--font-body)" }}
    >
      <Navbar currentScreen={screen} onNavigate={handleNavbarNavigate} />

      <div className="flex flex-1 overflow-hidden">
        {showSidebar && (
          <Sidebar currentScreen={screen} onNavigate={navigate} />
        )}

        <main
          className="flex-1 overflow-y-auto"
          style={{ scrollbarWidth: "none", msOverflowStyle: "none" } as React.CSSProperties}
        >
          <style>{`main::-webkit-scrollbar { display: none; }`}</style>
          {renderScreen(screen, navigate, sessionState, dark)}
        </main>
      </div>
    </div>
  );
}

// ── Root component: wraps everything in AuthProvider ─────────────────

export default function App() {
  return (
    <AuthProvider>
      <AppInner />
    </AuthProvider>
  );
}
