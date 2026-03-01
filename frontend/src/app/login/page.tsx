"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { authApi } from "@/lib/api";

type Mode = "login" | "register" | "totp";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [tempToken, setTempToken] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (mode === "register") {
        await authApi.register(email, password);
        toast.success("Аккаунт создан! Теперь войдите.");
        setMode("login");
      } else if (mode === "login") {
        const res = await authApi.login(email, password);
        const data = res.data;
        if (data.totp_required) {
          setTempToken(data.access_token);
          setMode("totp");
          toast("Введите код из приложения-аутентификатора");
        } else {
          localStorage.setItem("access_token", data.access_token);
          router.push("/dashboard");
        }
      } else if (mode === "totp") {
        const res = await authApi.verifyTotp(tempToken, otp);
        localStorage.setItem("access_token", res.data.access_token);
        router.push("/dashboard");
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Ошибка. Попробуйте снова.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-50 to-white flex items-center justify-center p-4">
      <div className="card max-w-sm w-full space-y-6">
        <div className="text-center">
          <div className="text-3xl">🏥</div>
          <h1 className="text-xl font-bold mt-1">AI Health Archive</h1>
          <p className="text-sm text-gray-500">
            {mode === "login" && "Войдите в свой аккаунт"}
            {mode === "register" && "Создать аккаунт"}
            {mode === "totp" && "Двухфакторная аутентификация"}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {mode !== "totp" && (
            <>
              <div>
                <label className="text-sm font-medium text-gray-700">Email</label>
                <input
                  type="email"
                  className="input mt-1"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="you@example.com"
                  autoComplete="email"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">Пароль</label>
                <input
                  type="password"
                  className="input mt-1"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={8}
                  placeholder="••••••••"
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                />
              </div>
            </>
          )}

          {mode === "totp" && (
            <div>
              <label className="text-sm font-medium text-gray-700">OTP-код</label>
              <input
                type="text"
                className="input mt-1 text-center text-2xl tracking-widest"
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                maxLength={6}
                placeholder="000000"
                autoFocus
              />
            </div>
          )}

          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? "..." : mode === "login" ? "Войти" : mode === "register" ? "Зарегистрироваться" : "Подтвердить"}
          </button>
        </form>

        {mode !== "totp" && (
          <p className="text-center text-sm text-gray-500">
            {mode === "login" ? "Нет аккаунта?" : "Уже есть аккаунт?"}{" "}
            <button
              className="text-brand-600 font-medium hover:underline"
              onClick={() => setMode(mode === "login" ? "register" : "login")}
            >
              {mode === "login" ? "Зарегистрироваться" : "Войти"}
            </button>
          </p>
        )}
      </div>
    </div>
  );
}
