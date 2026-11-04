
import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, Mail } from 'lucide-react'

import { authAPI } from '../service/api'
import AuthLayout from '../layouts/AuthLayout'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setMessage('')
    setError('')

    try {
      const result = await authAPI.forgotPassword(email.trim())
      setMessage(result.message)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to process your request.',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout
      heading="Reset your password"
      description="Enter your registered email address to request password reset instructions."
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        {message && (
          <div
            role="status"
            className="rounded-xl border border-green-200 bg-green-50 p-4 text-sm text-green-700 dark:border-green-900 dark:bg-green-950/40 dark:text-green-300"
          >
            {message}
          </div>
        )}

        {error && (
          <div role="alert" className="rounded-xl bg-red-50 p-4 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">
            {error}
          </div>
        )}

        <div>
          <label htmlFor="email" className="mb-2 block text-sm font-medium">
            Email address
          </label>

          <div className="relative">
            <Mail
              size={18}
              className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
            />

            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              className="w-full rounded-xl border border-slate-200 bg-white py-3.5 pl-11 pr-4 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-700 dark:bg-slate-900"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-xl bg-blue-600 px-4 py-3.5 font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
        >
          {loading ? 'Sending request...' : 'Send reset instructions'}
        </button>

        <Link
          to="/login"
          className="flex items-center justify-center gap-2 text-sm text-slate-500 hover:text-blue-600"
        >
          <ArrowLeft size={16} />
          Back to sign in
        </Link>
      </form>
    </AuthLayout>
  )
}
