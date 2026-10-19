/**
 * Kitchen overview page
 */
"use client";

import React from "react";
import { AppShell } from "@/components/layout/AppShell";

export default function KitchenPage() {
  return (
    <AppShell>
      <div className="space-y-8">
        <h1 className="text-4xl font-bold">My Kitchen</h1>

        <div className="grid grid-cols-3 gap-6">
          {/* Stats cards */}
          <div className="bg-white rounded-lg shadow p-6">
            <p className="text-gray-600 text-sm font-medium">Recipes</p>
            <p className="text-3xl font-bold">0</p>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <p className="text-gray-600 text-sm font-medium">Ingredients</p>
            <p className="text-3xl font-bold">0</p>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <p className="text-gray-600 text-sm font-medium">Members</p>
            <p className="text-3xl font-bold">1</p>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold mb-4">Quick Actions</h2>
          <div className="space-y-2">
            <a href="/kitchen/recipes/add" className="block text-blue-600 hover:underline">
              + Add Recipe
            </a>
            <a href="/kitchen/shopping-list" className="block text-blue-600 hover:underline">
              Generate Shopping List
            </a>
            <a href="/kitchen/ask" className="block text-blue-600 hover:underline">
              Ask a Question
            </a>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
