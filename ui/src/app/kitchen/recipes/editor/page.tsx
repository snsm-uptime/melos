'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

interface RecipeDraft {
  title?: string;
  instructions?: string;
  ingredients?: any[];
  yield_servings?: number;
  cook_time_minutes?: number;
  prep_time_minutes?: number;
  difficulty?: string;
}

export default function RecipeEditorPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [draft, setDraft] = useState<RecipeDraft | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [title, setTitle] = useState('');
  const [instructions, setInstructions] = useState('');
  const [ingredients, setIngredients] = useState<any[]>([]);
  const [yieldServings, setYieldServings] = useState(1);
  const [cookTime, setCookTime] = useState<number | undefined>();
  const [prepTime, setPrepTime] = useState<number | undefined>();
  const [difficulty, setDifficulty] = useState('medium');

  useEffect(() => {
    const draftParam = searchParams.get('draft');
    if (draftParam) {
      try {
        const parsedDraft = JSON.parse(draftParam);
        setDraft(parsedDraft);

        setTitle(parsedDraft.title || '');
        setInstructions(parsedDraft.instructions || '');
        setIngredients(parsedDraft.ingredients || []);
        setYieldServings(parsedDraft.yield_servings || 1);
        setCookTime(parsedDraft.cook_time_minutes);
        setPrepTime(parsedDraft.prep_time_minutes);
        setDifficulty(parsedDraft.difficulty || 'medium');
      } catch (err) {
        setError('Invalid recipe data');
      }
    }
  }, [searchParams]);

  const handleAddIngredient = () => {
    setIngredients([...ingredients, { name: '', quantity: 0, unit: 'unit', notes: '' }]);
  };

  const handleIngredientChange = (index: number, field: string, value: any) => {
    const updated = [...ingredients];
    updated[index] = { ...updated[index], [field]: value };
    setIngredients(updated);
  };

  const handleRemoveIngredient = (index: number) => {
    setIngredients(ingredients.filter((_, i) => i !== index));
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const kitchenId = new URL(window.location.href).searchParams.get('kitchenId');
      if (!kitchenId) {
        setError('Kitchen ID not found');
        return;
      }

      const response = await fetch(`/api/kitchens/${kitchenId}/recipes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          instructions,
          ingredients: ingredients.map((ing) => ({
            ingredient_name: ing.name,
            quantity: ing.quantity,
            unit: ing.unit,
            notes: ing.notes,
            is_linear: true,
          })),
          yield_servings: yieldServings,
          cook_time_minutes: cookTime,
          prep_time_minutes: prepTime,
          difficulty,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to save recipe');
      }

      const saved = await response.json();
      router.push(`/kitchen/recipes/${saved.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  if (!draft) {
    return <div className="p-4">Loading recipe editor...</div>;
  }

  return (
    <div className="max-w-3xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">Edit Recipe</h1>

      {error && (
        <div className="mb-4 p-4 bg-red-100 text-red-700 rounded">
          {error}
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        <div>
          <label className="block font-semibold mb-2">Recipe Title</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full p-2 border rounded"
            required
          />
        </div>

        <div className="grid grid-cols-4 gap-2">
          <div>
            <label className="block font-semibold mb-2">Yield (servings)</label>
            <input
              type="number"
              value={yieldServings}
              onChange={(e) => setYieldServings(parseInt(e.target.value))}
              className="w-full p-2 border rounded"
              min="1"
            />
          </div>
          <div>
            <label className="block font-semibold mb-2">Prep Time (min)</label>
            <input
              type="number"
              value={prepTime || ''}
              onChange={(e) => setPrepTime(e.target.value ? parseInt(e.target.value) : undefined)}
              className="w-full p-2 border rounded"
              min="0"
            />
          </div>
          <div>
            <label className="block font-semibold mb-2">Cook Time (min)</label>
            <input
              type="number"
              value={cookTime || ''}
              onChange={(e) => setCookTime(e.target.value ? parseInt(e.target.value) : undefined)}
              className="w-full p-2 border rounded"
              min="0"
            />
          </div>
          <div>
            <label className="block font-semibold mb-2">Difficulty</label>
            <select
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value)}
              className="w-full p-2 border rounded"
            >
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block font-semibold mb-2">Instructions</label>
          <textarea
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            className="w-full h-32 p-2 border rounded"
            required
          />
        </div>

        <div>
          <div className="flex justify-between items-center mb-3">
            <label className="block font-semibold">Ingredients</label>
            <button
              type="button"
              onClick={handleAddIngredient}
              className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700"
            >
              + Add
            </button>
          </div>

          <div className="space-y-3">
            {ingredients.map((ing, idx) => (
              <div key={idx} className="flex gap-2">
                <input
                  type="text"
                  placeholder="Ingredient name"
                  value={ing.name}
                  onChange={(e) => handleIngredientChange(idx, 'name', e.target.value)}
                  className="flex-1 p-2 border rounded"
                />
                <input
                  type="number"
                  placeholder="Qty"
                  value={ing.quantity}
                  onChange={(e) => handleIngredientChange(idx, 'quantity', parseFloat(e.target.value))}
                  className="w-20 p-2 border rounded"
                  step="0.1"
                />
                <select
                  value={ing.unit}
                  onChange={(e) => handleIngredientChange(idx, 'unit', e.target.value)}
                  className="w-24 p-2 border rounded"
                >
                  <option value="unit">unit</option>
                  <option value="cup">cup</option>
                  <option value="tbsp">tbsp</option>
                  <option value="tsp">tsp</option>
                  <option value="oz">oz</option>
                  <option value="lb">lb</option>
                  <option value="ml">ml</option>
                  <option value="l">l</option>
                  <option value="g">g</option>
                  <option value="kg">kg</option>
                </select>
                <input
                  type="text"
                  placeholder="Notes"
                  value={ing.notes}
                  onChange={(e) => handleIngredientChange(idx, 'notes', e.target.value)}
                  className="flex-1 p-2 border rounded"
                />
                <button
                  type="button"
                  onClick={() => handleRemoveIngredient(idx)}
                  className="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="flex gap-4">
          <button
            type="submit"
            disabled={loading}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
          >
            {loading ? 'Saving...' : 'Save Recipe'}
          </button>
          <button
            type="button"
            onClick={() => router.back()}
            className="flex-1 px-4 py-2 border rounded hover:bg-gray-100"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
