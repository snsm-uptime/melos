'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function AddRecipePage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'text' | 'url' | 'photo'>('text');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [textInput, setTextInput] = useState('');
  const [urlInput, setUrlInput] = useState('');
  const [photoFile, setPhotoFile] = useState<File | null>(null);

  const handleTextSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const kitchenId = new URL(window.location.href).searchParams.get('kitchenId');
      if (!kitchenId) {
        setError('Kitchen ID not found');
        return;
      }

      const response = await fetch(`/api/kitchens/${kitchenId}/recipes/draft`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: textInput }),
      });

      if (!response.ok) {
        throw new Error('Failed to extract recipe');
      }

      const draft = await response.json();

      if (!draft.is_recipe) {
        setError(draft.reason || 'That doesn\'t look like a recipe. Please try again.');
        return;
      }

      router.push(`/kitchen/recipes/editor?draft=${JSON.stringify(draft)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const handleUrlSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const kitchenId = new URL(window.location.href).searchParams.get('kitchenId');
      if (!kitchenId) {
        setError('Kitchen ID not found');
        return;
      }

      const response = await fetch(`/api/kitchens/${kitchenId}/recipes/draft`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: urlInput }),
      });

      if (!response.ok) {
        throw new Error('Failed to extract recipe from URL');
      }

      const draft = await response.json();

      if (!draft.is_recipe) {
        setError(draft.reason || 'Could not find a recipe at that URL. Please try another.');
        return;
      }

      router.push(`/kitchen/recipes/editor?draft=${JSON.stringify(draft)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const handlePhotoSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!photoFile) {
      setError('Please select an image');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const kitchenId = new URL(window.location.href).searchParams.get('kitchenId');
      if (!kitchenId) {
        setError('Kitchen ID not found');
        return;
      }

      const formData = new FormData();
      formData.append('file', photoFile);

      const response = await fetch(`/api/kitchens/${kitchenId}/recipes/draft/photo`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Failed to extract recipe from photo');
      }

      const draft = await response.json();

      if (!draft.is_recipe) {
        setError(draft.reason || 'Could not recognize a recipe in that photo. Please try another.');
        return;
      }

      router.push(`/kitchen/recipes/editor?draft=${JSON.stringify(draft)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">Add Recipe</h1>

      {error && (
        <div className="mb-4 p-4 bg-red-100 text-red-700 rounded">
          {error}
        </div>
      )}

      <div className="flex border-b mb-6">
        <button
          className={`px-4 py-2 ${activeTab === 'text' ? 'border-b-2 border-blue-600 font-semibold' : ''}`}
          onClick={() => setActiveTab('text')}
        >
          Paste Text
        </button>
        <button
          className={`px-4 py-2 ${activeTab === 'url' ? 'border-b-2 border-blue-600 font-semibold' : ''}`}
          onClick={() => setActiveTab('url')}
        >
          From URL
        </button>
        <button
          className={`px-4 py-2 ${activeTab === 'photo' ? 'border-b-2 border-blue-600 font-semibold' : ''}`}
          onClick={() => setActiveTab('photo')}
        >
          Upload Photo
        </button>
      </div>

      {activeTab === 'text' && (
        <form onSubmit={handleTextSubmit}>
          <textarea
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            placeholder="Paste your recipe text here..."
            className="w-full h-64 p-3 border rounded mb-4"
            required
          />
          <button
            type="submit"
            disabled={loading}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
          >
            {loading ? 'Extracting...' : 'Extract Recipe'}
          </button>
        </form>
      )}

      {activeTab === 'url' && (
        <form onSubmit={handleUrlSubmit}>
          <input
            type="url"
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            placeholder="https://example.com/recipe"
            className="w-full p-3 border rounded mb-4"
            required
          />
          <button
            type="submit"
            disabled={loading}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
          >
            {loading ? 'Fetching...' : 'Extract Recipe'}
          </button>
        </form>
      )}

      {activeTab === 'photo' && (
        <form onSubmit={handlePhotoSubmit}>
          <div className="border-2 border-dashed rounded p-6 text-center mb-4">
            <input
              type="file"
              accept="image/jpeg,image/png"
              onChange={(e) => setPhotoFile(e.target.files?.[0] || null)}
              className="hidden"
              id="photo-input"
            />
            <label htmlFor="photo-input" className="cursor-pointer">
              {photoFile ? (
                <p className="text-blue-600 font-semibold">{photoFile.name}</p>
              ) : (
                <div>
                  <p className="text-gray-600">Click to select or drag an image</p>
                  <p className="text-sm text-gray-500">JPEG or PNG only</p>
                </div>
              )}
            </label>
          </div>
          <button
            type="submit"
            disabled={loading || !photoFile}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
          >
            {loading ? 'Processing...' : 'Extract Recipe'}
          </button>
        </form>
      )}
    </div>
  );
}
