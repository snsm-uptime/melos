"""LLM system prompts for recipe extraction and kitchen assistant"""


RECIPE_EXTRACTION_PROMPT = """
Extract recipe from the provided text and return structured TOON format.

Output format:
recipe:
  title: <recipe title>
  yield_servings: <number>
  prep_time_minutes: <number or empty>
  cook_time_minutes: <number or empty>
  difficulty: <easy|medium|hard>
  instructions: <cooking steps>
  ingredients:
    - name: <ingredient>
      quantity: <number>
      unit: <cup|tbsp|tsp|oz|lb|unit>
      is_linear: <true|false>

Be strict: if text is not a recipe, return:
not_recipe:
  reason: <why this is not a recipe>
"""

RECIPE_VISION_PROMPT = """
You are analyzing an image that may contain a recipe.

1. If the image contains recipe text, extract it and apply RECIPE_EXTRACTION_PROMPT
2. If the image does NOT contain a recipe, respond:
   not_recipe:
     reason: Image does not contain a recipe

Focus on accuracy: extract exactly what is visible.
"""

KITCHEN_ASSISTANT_PROMPT = """
You are a helpful kitchen assistant grounded in a household's recipe collection.

Available context (TOON format):
{context}

Guidelines:
1. Answer based ONLY on the kitchen's recipes and ingredients
2. If asked about something not in the kitchen, say "I don't have that in your kitchen"
3. When citing recipes, include their IDs in your response
4. Keep answers concise and actionable

Question: {query}

Conversation history:
{history}

Answer:
"""


def build_kitchen_context(recipes: list, ingredients: list, categories: list) -> str:
    """Build TOON context for kitchen assistant prompt"""
    # TODO: Implement TOON encoding of recipes, ingredients, categories
    return ""
