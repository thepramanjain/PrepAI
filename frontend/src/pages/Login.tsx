import { useState, type FormEvent } from "react";
import { BrainCircuit, Mail, Lock, Sparkles, Eye, EyeOff } from "lucide-react";
import { Button } from "../components/ui/button";
import { useAuth } from "../context/AuthContext";
import type { Screen } from "../types";

interface LoginProps {
  onNavigate: (screen: Screen) => void;
}

export default function Login({ onNavigate }: LoginProps) {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!email.trim() || !password.trim()) {
      setError("Email and password are required.");
      return;
    }
    setLoading(true);
    try {
      await login(email.trim(), password);
      onNavigate("dashboard");
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Invalid email or password. Please try again.";
      setError(String(msg));
    } finally {
      setLoading(false);
    }
  }

  const inputCls =
    "w-full rounded-lg border border-border bg-input-background px-3 py-2.5 pl-10 text-sm text-foreground placeholder:text-muted-foreground transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background focus-visible:border-primary";

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      {/* Gradient orb */}
      <div
        aria-hidden
        className="pointer-events-none fixed left-1/2 top-0 -z-10 h-80 w-96 -translate-x-1/2 rounded-full opacity-15 blur-3xl"
        style={{ background: "radial-gradient(ellipse, #7c3aed 0%, #4f46e5 60%, transparent 100%)" }}
      />

      <div className="w-full max-w-sm">
        {/* Logo */}
        <button
          onClick={() => onNavigate("landing")}
          className="mx-auto mb-8 flex items-center gap-2.5"
          aria-label="PrepAI home"
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary shadow-md">
            <BrainCircuit size={18} className="text-primary-foreground" />
          </div>
          <span
            className="text-xl font-bold tracking-tight text-foreground"
            style={{ fontFamily: "var(--font-display)" }}
          >
            PrepAI
          </span>
        </button>

        {/* Card */}
        <div className="rounded-2xl border border-border bg-card p-8 shadow-xl shadow-black/[0.08]">
          <div className="mb-6 text-center">
            <h1
              className="text-2xl font-bold tracking-tight text-foreground"
              style={{ fontFamily: "var(--font-display)" }}
            >
              Welcome back
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Sign in to continue practicing
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            {/* Email */}
            <div className="relative">
              <Mail
                size={15}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
              />
              <input
                id="login-email"
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => { setEmail(e.target.value); setError(null); }}
                className={inputCls}
                disabled={loading}
              />
            </div>

            {/* Password */}
            <div className="relative">
              <Lock
                size={15}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
              />
              <input
                id="login-password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                placeholder="Your password"
                value={password}
                onChange={(e) => { setPassword(e.target.value); setError(null); }}
                className={`${inputCls} pr-10`}
                disabled={loading}
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground focus-visible:outline-none"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>

            {/* Error */}
            {error && (
              <p className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-xs text-destructive">
                {error}
              </p>
            )}

            {/* Submit */}
            <Button
              id="login-submit"
              type="submit"
              className="w-full"
              size="lg"
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                  Signing in…
                </>
              ) : (
                <>
                  <Sparkles size={14} /> Sign in
                </>
              )}
            </Button>
          </form>

          {/* Footer */}
          <p className="mt-5 text-center text-xs text-muted-foreground">
            Don't have an account?{" "}
            <button
              onClick={() => onNavigate("register")}
              className="font-semibold text-primary underline-offset-3 hover:underline"
            >
              Create one free
            </button>
          </p>
        </div>

        {/* Back to landing */}
        <p className="mt-5 text-center text-xs text-muted-foreground">
          <button
            onClick={() => onNavigate("landing")}
            className="hover:text-foreground transition-colors"
          >
            ← Back to home
          </button>
        </p>
      </div>
    </div>
  );
}
