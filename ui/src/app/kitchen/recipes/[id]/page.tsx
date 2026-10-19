'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';

interface Recipe {
  id: string;
  title: string;
  instructions: string;
  yield_servings: number;
  cook_time_minutes?: number;
  prep_time_minutes?: number;
  difficulty: string;
  created_by_user_id: string;
  created_at: string;
}

export default function RecipeDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [recipe, setRecipe] = useState<Recipe | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const recipeId = params.id as string;

  useEffect(() => {
    const fetchRecipe = async () => {
      try {
        const kitchenId = new URL(window.location.href).searchParams.get('kitchenId');
        if (!kitchenId) {
          setError('Kitchen ID not found');
          return;
        }

        const response = await fetch(`/api/kitchens/${kitchenId}/recipes/${recipeId}`);
        if (!response.ok) {
          throw new Error('Failed to fetch recipe');
        }
        const data = await response.json();
        setRecipe(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchRecipe();
  }, [recipeId]);

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this recipe?')) {
      return;
    }

    try {
      const kitchenId = new URL(window.location.href).searchParams.get('kitchenId');
      if (!kitchenId) {
        setError('Kitchen ID not found');
        return;
      }

      const response = await fetch(`/api/kitchens/${kitchenId}/recipes/${recipeId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete recipe');
      }

      router.push('/kitchen/recipes');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  };

  if (loading) {
    return <div className="p-4">Loading recipe...</div>;
  }

  if (error) {
    return <div className="p-4 text-red-600">Error: {error}</div>;
  }

  if (!recipe) {
    return <div className="p-4">Recipe not found</div>;
  }

  return (
    <div className="p-4">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="text-3xl font-bold">{recipe.title}</h1>
          <p className="text-gray-600 mt-2">
            Yield: {recipe.yield_servings} servings | Difficulty: {recipe.difficulty}
          </p>
          {recipe.cook_time_minutes && (
            <p className="text-gray-600">
              Total time: {(recipe.prep_time_minutes || 0) + (recipe.cook_time_minutes || 0)} minutes
            </p>
          )}
        </div>
        <button
          onClick={handleDelete}
          className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Delete Recipe
        </button>
      </div>

      <section className="mb-6">
        <h2 className="text-xl font-semibold mb-2">Instructions</h2>
        <p className="whitespace-pre-wrap">{recipe.instructions}</p>
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-2">Created</h2>
        <p className="text-gray-600">{new Date(recipe.created_at).toLocaleString()}</p>
      </section>
    </div>
  );
}
