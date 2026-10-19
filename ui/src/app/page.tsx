"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    // Check if authenticated, redirect to /kitchen if yes, /auth/sign-in if no
    const checkAuth = async () => {
      try {
        const response = await fetch("/api/v1/auth/session", {
          credentials: "include",
        });
        if (response.ok) {
          router.push("/kitchen");
        } else {
          router.push("/auth/sign-in");
        }
      } catch {
        router.push("/auth/sign-in");
      }
    };

    checkAuth();
  }, [router]);

  return (
    <main className="flex items-center justify-center min-h-screen">
      <p className="text-gray-500">Loading...</p>
    </main>
  );
}
