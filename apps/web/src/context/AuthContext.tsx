
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'

import {
  authAPI,
  setAccessToken,
  type User,
} from '../service/api'

interface AuthContextValue {
  user: User | null
  loading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(
  undefined,
)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const login = useCallback(
    async (email: string, password: string) => {
      const result = await authAPI.login(email, password)
      setUser(result.user)
    },
    [],
  )

  const logout = useCallback(async () => {
    try {
      await authAPI.logout()
    } finally {
      setAccessToken(null)
      setUser(null)
    }
  }, [])

  useEffect(() => {
    let active = true

    async function restoreSession() {
      try {
        const token = await authAPI.refresh()

        if (!token) return

        const currentUser = await authAPI.me()

        if (active) {
          setUser(currentUser)
        }
      } catch {
        setAccessToken(null)

        if (active) {
          setUser(null)
        }
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    void restoreSession()

    return () => {
      active = false
    }
  }, [])

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAuthenticated: Boolean(user),
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

// This hook must remain available from this module; it shares the context with AuthProvider.
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const context = useContext(AuthContext)

  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider')
  }

  return context
}
