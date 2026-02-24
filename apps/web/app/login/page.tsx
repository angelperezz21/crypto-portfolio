"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { login, setToken } from "@/lib/api"

export default function LoginPage() {
  const router = useRouter()
  const [password, setPassword] = useState("")
  const [error, setError]       = useState<string | null>(null)
  const [loading, setLoading]   = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const token = await login(password)
      setToken(token)
      router.replace("/")
    } catch {
      setError("Contraseña incorrecta")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-base px-4">
      <div className="w-full max-w-sm">
        {/* Logo / título */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[#f97316]/10 mb-4">
            <span className="text-2xl">₿</span>
          </div>
          <h1 className="text-xl font-semibold text-primary">Portfolio Dashboard</h1>
          <p className="text-sm text-secondary mt-1">Introduce tu contraseña para acceder</p>
        </div>

        {/* Card */}
        <form
          onSubmit={handleSubmit}
          className="bg-surface border border-[var(--border)] rounded-xl p-6 space-y-4"
        >
          <div>
            <label className="block text-xs font-medium text-secondary mb-1.5">
              Contraseña
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoFocus
              required
              placeholder="••••••••"
              className="w-full px-3 py-2.5 text-sm rounded-lg
                         bg-elevated border border-[var(--border)]
                         text-primary placeholder:text-tertiary
                         focus:outline-none focus:ring-2 focus:ring-accent/50
                         transition-all"
            />
          </div>

          {error && (
            <p className="text-xs text-red-400 font-medium">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading || !password}
            className="w-full py-2.5 px-4 rounded-lg text-sm font-medium
                       bg-accent text-white
                       hover:bg-indigo-600 active:bg-indigo-700
                       disabled:opacity-50 disabled:cursor-not-allowed
                       transition-colors"
          >
            {loading ? "Accediendo…" : "Entrar"}
          </button>
        </form>
      </div>
    </div>
  )
}
