"use client";

import { useState, useEffect } from "react";
import { useAuthStore } from "@/lib/store";
import styles from "./page.module.css";

export default function HomePage() {
  const { user, isLoading, loadFromStorage } = useAuthStore();

  useEffect(() => {
    loadFromStorage();
  }, [loadFromStorage]);

  if (isLoading) {
    return (
      <div className={styles.loadingScreen}>
        <div className={styles.logoContainer}>
          <div className={styles.logoGlow} />
          <h1 className={styles.logoText}>ZAPRICA</h1>
          <p className={styles.logoSubtext}>Initializing secure environment...</p>
          <div className="spinner" style={{ margin: "24px auto" }} />
        </div>
      </div>
    );
  }

  if (!user) {
    return <AuthPage />;
  }

  // Redirect to dashboard when authenticated
  if (typeof window !== "undefined") {
    window.location.href = "/dashboard";
  }

  return null;
}

function AuthPage() {
  const [mode, setMode] = useState<"login" | "register">("login");

  return (
    <div className={styles.authContainer}>
      <div className={styles.authHero}>
        <div className={styles.heroContent}>
          <div className={styles.heroBadge}>
            <span className={styles.heroBadgeDot} />
            ENTERPRISE AI OSINT
          </div>
          <h1 className={styles.heroTitle}>
            <span className={styles.heroGradient}>ZAPRICA</span>
          </h1>
          <p className={styles.heroDesc}>
            Autonomous AI investigation platform for cybersecurity threat
            intelligence. Deploy reasoning agents to conduct multi-step OSINT
            investigations with full evidence provenance.
          </p>
          <div className={styles.heroFeatures}>
            <FeatureItem icon="🔍" text="Autonomous OSINT Investigations" />
            <FeatureItem icon="🛡️" text="DualView Security (Anti-Injection)" />
            <FeatureItem icon="🕸️" text="Knowledge Graph Visualization" />
            <FeatureItem icon="📜" text="Cryptographic Evidence Provenance" />
          </div>
        </div>
      </div>

      <div className={styles.authFormSide}>
        <div className={styles.authCard}>
          <div className={styles.authTabs}>
            <button
              className={`${styles.authTab} ${mode === "login" ? styles.authTabActive : ""}`}
              onClick={() => setMode("login")}
            >
              Sign In
            </button>
            <button
              className={`${styles.authTab} ${mode === "register" ? styles.authTabActive : ""}`}
              onClick={() => setMode("register")}
            >
              Register
            </button>
          </div>

          {mode === "login" ? <LoginForm /> : <RegisterForm />}
        </div>
      </div>
    </div>
  );
}

function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const { login, error, isLoading } = useAuthStore();
  const [localError, setLocalError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError("");
    try {
      await login(email, password);
      window.location.href = "/dashboard";
    } catch (err: unknown) {
      setLocalError(err instanceof Error ? err.message : "Login failed");
    }
  };

  return (
    <form onSubmit={handleSubmit} className={styles.authForm}>
      <div className={styles.formGroup}>
        <label className="label" htmlFor="login-email">Email</label>
        <input
          id="login-email"
          className="input"
          type="email"
          placeholder="analyst@company.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
        />
      </div>
      <div className={styles.formGroup}>
        <label className="label" htmlFor="login-password">Password</label>
        <input
          id="login-password"
          className="input"
          type="password"
          placeholder="••••••••"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="current-password"
        />
      </div>

      {(localError || error) && (
        <div className={styles.errorMsg}>{localError || error}</div>
      )}

      <button
        type="submit"
        className="btn btn-primary btn-lg"
        disabled={isLoading}
        style={{ width: "100%", marginTop: "8px" }}
      >
        {isLoading ? <span className="spinner" /> : "Sign In to ZAPRICA"}
      </button>
    </form>
  );
}

function RegisterForm() {
  const [formData, setFormData] = useState({
    org_name: "",
    org_slug: "",
    email: "",
    password: "",
    full_name: "",
  });
  const { register, error, isLoading } = useAuthStore();
  const [localError, setLocalError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError("");
    try {
      await register(formData);
      window.location.href = "/dashboard";
    } catch (err: unknown) {
      setLocalError(err instanceof Error ? err.message : "Registration failed");
    }
  };

  const updateField = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (field === "org_name") {
      setFormData((prev) => ({
        ...prev,
        org_slug: value.toLowerCase().replace(/[^a-z0-9-]/g, "-").replace(/-+/g, "-"),
      }));
    }
  };

  return (
    <form onSubmit={handleSubmit} className={styles.authForm}>
      <div className={styles.formGroup}>
        <label className="label" htmlFor="reg-org">Organization Name</label>
        <input
          id="reg-org"
          className="input"
          placeholder="Acme Security"
          value={formData.org_name}
          onChange={(e) => updateField("org_name", e.target.value)}
          required
        />
      </div>
      <div className={styles.formGroup}>
        <label className="label" htmlFor="reg-name">Full Name</label>
        <input
          id="reg-name"
          className="input"
          placeholder="Jane Analyst"
          value={formData.full_name}
          onChange={(e) => updateField("full_name", e.target.value)}
          required
        />
      </div>
      <div className={styles.formGroup}>
        <label className="label" htmlFor="reg-email">Email</label>
        <input
          id="reg-email"
          className="input"
          type="email"
          placeholder="jane@acme.com"
          value={formData.email}
          onChange={(e) => updateField("email", e.target.value)}
          required
        />
      </div>
      <div className={styles.formGroup}>
        <label className="label" htmlFor="reg-password">Password</label>
        <input
          id="reg-password"
          className="input"
          type="password"
          placeholder="Min 8 characters"
          value={formData.password}
          onChange={(e) => updateField("password", e.target.value)}
          required
          minLength={8}
        />
      </div>

      {(localError || error) && (
        <div className={styles.errorMsg}>{localError || error}</div>
      )}

      <button
        type="submit"
        className="btn btn-primary btn-lg"
        disabled={isLoading}
        style={{ width: "100%", marginTop: "8px" }}
      >
        {isLoading ? <span className="spinner" /> : "Create Account"}
      </button>
    </form>
  );
}

function FeatureItem({ icon, text }: { icon: string; text: string }) {
  return (
    <div className={styles.featureItem}>
      <span className={styles.featureIcon}>{icon}</span>
      <span>{text}</span>
    </div>
  );
}
