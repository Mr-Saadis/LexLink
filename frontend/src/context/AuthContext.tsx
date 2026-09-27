import React, { createContext, useContext, useState, useEffect } from "react";

export interface User {
  id: string;
  email: string;
  name?: string;
  role?: "layman" | "lawyer" | "admin" | string;
  verification_status?: string;
}

export interface SignupData {
  email: string;
  password: string;
  name: string;
  role: "layman" | "lawyer";
  license_no?: string;
  cnic?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  isAuthModalOpen: boolean;
  setIsAuthModalOpen: (open: boolean) => void;
  login: (email: string, password: string) => Promise<User | null>;
  signup: (data: SignupData) => Promise<User | null>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_BASE = "http://localhost:8000";

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState<boolean>(false);

  useEffect(() => {
    const savedToken =
      localStorage.getItem("token") ||
      localStorage.getItem("access_token");

    const savedUser = localStorage.getItem("user");

    if (savedToken && savedUser) {
      try {
        setToken(savedToken);
        setUser(JSON.parse(savedUser));
      } catch (error) {
        console.error("Failed to parse saved user:", error);

        localStorage.removeItem("token");
        localStorage.removeItem("access_token");
        localStorage.removeItem("user");
      }
    }

    setIsLoading(false);
  }, []);

  const login = async (
    email: string,
    password: string
  ): Promise<User | null> => {
    setError(null);
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Authentication failed. Please check your credentials."
        );
      }

      const accessToken = data.access_token;
      const userData: User = data.user;

      setToken(accessToken);
      setUser(userData);

      localStorage.setItem("token", accessToken);
      localStorage.setItem("access_token", accessToken);
      localStorage.setItem("user", JSON.stringify(userData));

      setIsAuthModalOpen(false);

      return userData;
    } catch (err: any) {
      setError(err.message || "Failed to sign in");
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  const signup = async (
    signupData: SignupData
  ): Promise<User | null> => {
    setError(null);
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/auth/signup`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: signupData.email,
          password: signupData.password,
          name: signupData.name,
          role: signupData.role,

          // Optional fields
          ...(signupData.license_no?.trim()
            ? { license_no: signupData.license_no.trim() }
            : {}),

          ...(signupData.cnic?.trim()
            ? { cnic: signupData.cnic.trim() }
            : {}),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Registration failed. Please try again."
        );
      }

      const accessToken = data.access_token;
      const userData: User = data.user;

      if (accessToken) {
        setToken(accessToken);

        localStorage.setItem("token", accessToken);
        localStorage.setItem("access_token", accessToken);
      }

      setUser(userData);
      localStorage.setItem("user", JSON.stringify(userData));

      setIsAuthModalOpen(false);

      return userData;
    } catch (err: any) {
      setError(err.message || "Registration failed");
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);

    localStorage.removeItem("token");
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user && !!token,
        isLoading,
        error,
        isAuthModalOpen,
        setIsAuthModalOpen,
        login,
        signup,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }

  return context;
};