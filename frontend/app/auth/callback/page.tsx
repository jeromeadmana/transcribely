"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function AuthCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get("code");

    if (!code) {
      router.push("/login?error=oauth_failed");
      return;
    }

    // Exchange auth code for tokens via POST request
    const exchangeCode = async () => {
      try {
        const response = await fetch(`${API_URL}/api/auth/oauth/exchange`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ code }),
        });

        if (!response.ok) {
          const data = await response.json();
          setError(data.detail || "Authentication failed");
          setTimeout(() => router.push("/login?error=oauth_failed"), 2000);
          return;
        }

        const data = await response.json();
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);
        localStorage.setItem("user", JSON.stringify(data.user));
        router.push("/dashboard");
      } catch (err) {
        setError("Network error");
        setTimeout(() => router.push("/login?error=oauth_failed"), 2000);
      }
    };

    exchangeCode();
  }, [searchParams, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        {error ? (
          <>
            <div className="text-red-500 text-xl mb-2">Error</div>
            <p className="text-gray-600">{error}</p>
            <p className="text-gray-400 text-sm mt-2">Redirecting to login...</p>
          </>
        ) : (
          <>
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Signing you in...</p>
          </>
        )}
      </div>
    </div>
  );
}
