
import { useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ArrowLeft, LockKeyhole } from 'lucide-react'

import { authAPI } from '../service/api'
import AuthLayout from '../layouts/AuthLayout'

export default function ResetPassword() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setMessage('')

    if (password.length < 12 || password.length > 128) {
      setError('Password must contain 12–128 characters.')
      return
    }

    if (password.trim() !== password) {
      setError('Password cannot start or end with whitespace.')
      return
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setLoading(true)

    try {
      const result = await authAPI.resetPassword(token, password)
      setMessage(result.message)
      setPassword('')
      setConfirmPassword('')
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to reset your password.',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout
      heading="Choose a new password"
      description="Create a strong password to secure your account."
    >
      {!token ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300">
          No password reset token was provided. Please request a new reset link.
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-5">
          {message && (
            <div role="status" className="rounded-xl border border-green-200 bg-green-50 p-4 text-sm text-green-700 dark:border-green-900 dark:bg-green-950/40 dark:text-green-300">
              {message}
            </div>
          )}

          {error && (
            <div role="alert" className="rounded-xl bg-red-50 p-4 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="password" className="mb-2 block text-sm font-medium">
              New password
            </label>
            <div className="relative">
              <LockKeyhole size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                id="password"
                type="password"
                autoComplete="new-password"
                required
                minLength={12}
                maxLength={128}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-white py-3.5 pl-11 pr-4 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-700 dark:bg-slate-900"
              />
            </div>
            <p className="mt-2 text-xs text-slate-500">
              Use 12–128 characters.
            </p>
          </div>

          <div>
            <label htmlFor="confirm-password" className="mb-2 block text-sm font-medium">
              Confirm new password
            </label>
            <input
              id="confirm-password"
              type="password"
              autoComplete="new-password"
              required
              maxLength={128}
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3.5 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-700 dark:bg-slate-900"
            />
          </div>

          <button
            type="submit"
            disabled={loading || Boolean(message)}
            className="w-full rounded-xl bg-blue-600 px-4 py-3.5 font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {loading ? 'Updating password...' : 'Update password'}
          </button>
        </form>
      )}

      <Link
        to="/login"
        className="mt-6 flex items-center justify-center gap-2 text-sm text-slate-500 hover:text-blue-600"
      >
        <ArrowLeft size={16} />
        Back to sign in
      </Link>
    </AuthLayout>
  )
}
