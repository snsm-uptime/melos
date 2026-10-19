/**
 * Main application shell layout with navigation
 */
"use client";

import React from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";

interface AppShellProps {
  children: React.ReactNode;
  kitchenId?: string;
}

export function AppShell({ children, kitchenId }: AppShellProps) {
  const { session } = useAuth();

  if (!session) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <Link href="/kitchen" className="text-2xl font-bold text-blue-600">
            🏠 Melos
          </Link>
          <nav className="flex gap-6 items-center">
            {kitchenId && (
              <>
                <Link href={`/kitchen`} className="text-gray-700 hover:text-blue-600">
                  Overview
                </Link>
                <Link href={`/kitchen/recipes`} className="text-gray-700 hover:text-blue-600">
                  Recipes
                </Link>
                <Link href={`/kitchen/ingredients`} className="text-gray-700 hover:text-blue-600">
                  Ingredients
                </Link>
                <Link href={`/kitchen/shopping-list`} className="text-gray-700 hover:text-blue-600">
                  Shopping List
                </Link>
                <Link href={`/kitchen/ask`} className="text-gray-700 hover:text-blue-600">
                  Ask
                </Link>
              </>
            )}
            <div className="text-sm text-gray-600">
              {session.user.email}
            </div>
          </nav>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-gray-100 border-t border-gray-200 mt-12 py-8 px-4 text-center text-sm text-gray-600">
        <p>&copy; 2026 Melos - Recipe & Kitchen System</p>
      </footer>
    </div>
  );
}
