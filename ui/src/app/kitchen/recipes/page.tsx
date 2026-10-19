'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

interface Recipe {
  id: string;
  title: string;
  yield_servings: number;
  cook_time_minutes?: number;
  prep_time_minutes?: number;
  difficulty: string;
}

export default function RecipesPage() {
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchRecipes = async () => {
      try {
        const kitchenId = new URL(window.location.href).searchParams.get('kitchenId');
        if (!kitchenId) {
          setError('Kitchen ID not found');
          return;
        }

        const response = await fetch(`/api/kitchens/${kitchenId}/recipes`);
        if (!response.ok) {
          throw new Error('Failed to fetch recipes');
        }
        const data = await response.json();
        setRecipes(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchRecipes();
  }, []);

  if (loading) {
    return <div className="p-4">Loading recipes...</div>;
  }

  if (error) {
    return <div className="p-4 text-red-600">Error: {error}</div>;
  }

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Recipes</h1>
        <Link
          href="/kitchen/recipes/add"
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Add Recipe
        </Link>
      </div>

      {recipes.length === 0 ? (
        <p className="text-gray-500">No recipes yet. Start by adding one!</p>
      ) : (
        <div className="grid gap-4">
          {recipes.map((recipe) => (
            <div key={recipe.id} className="border rounded p-4 hover:shadow-lg">
              <Link href={`/kitchen/recipes/${recipe.id}`}>
                <h2 className="text-lg font-semibold hover:text-blue-600">
                  {recipe.title}
                </h2>
              </Link>
              <div className="text-sm text-gray-600 mt-2">
                <p>Yield: {recipe.yield_servings} servings</p>
                {recipe.cook_time_minutes && (
                  <p>Cook time: {recipe.cook_time_minutes} minutes</p>
                )}
                {recipe.prep_time_minutes && (
                  <p>Prep time: {recipe.prep_time_minutes} minutes</p>
                )}
                <p>Difficulty: {recipe.difficulty}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
