# UI Contract: Melos Recipe & Kitchen System

**Phase**: 1 (Design)  
**Date**: 2026-10-18  
**Status**: Draft

---

## Overview

This contract defines the page structure and component responsibilities for the Melos UI. The UI is built with Next.js 16 (App Router), React 19, and Tailwind 4. See project structure in `plan.md` for file locations.

## Page Hierarchy

```
/                          # Home (redirects to /kitchen or /sign-up)
├── (auth)/
│   ├── sign-up            # User registration
│   ├── sign-in            # User login
│   └── forgot-password    # Password reset
├── kitchen/
│   ├── [id]/              # Kitchen shell (AppShell with sidebar)
│   │   ├── page           # Kitchen overview/dashboard
│   │   ├── recipes/
│   │   │   ├── page       # Recipe list
│   │   │   ├── [id]/      # Recipe detail (view/edit)
│   │   │   └── add        # Add recipe (capture: text/URL/photo)
│   │   ├── ingredients/
│   │   │   ├── page       # Ingredient catalog
│   │   │   └── [id]/      # Ingredient detail
│   │   ├── members/
│   │   │   ├── page       # Members list
│   │   │   └── invite     # Send invite
│   │   ├── shopping-list/
│   │   │   ├── page       # Generate & view shopping lists
│   │   │   └── [id]/      # Shopping list detail
│   │   ├── ask/           # Chat with Kitchen Assistant
│   │   └── settings/      # Kitchen settings
└── account                # User account (profile, password)
```

## Core Pages

### Home Page

**Path**: `/`  
**Component**: `app/page.tsx`

**Responsibility**:
- If authenticated, redirect to default kitchen (first in list)
- If not authenticated, show marketing landing or redirect to `/sign-up`

**Key Elements**:
- Melos logo, tagline
- Call-to-action buttons (Sign Up, Sign In)

---

### Kitchen Overview

**Path**: `/kitchen/[id]/`  
**Component**: `app/kitchen/[id]/page.tsx`

**Responsibility**:
- Display kitchen dashboard with key stats and quick actions
- Show recent recipes, shopping lists, members

**Key Elements**:
- Kitchen name (editable for owner only)
- Recipe count, ingredient count, member count
- Recent recipes (last 5) with thumbnails
- Quick actions: "Add Recipe", "Generate Shopping List", "Ask"
- Members list (expandable)

**Responsive**:
- Desktop: 2-3 columns
- Mobile: 1 column

---

### Recipe List

**Path**: `/kitchen/[id]/recipes`  
**Component**: `app/kitchen/[id]/recipes/page.tsx`

**Responsibility**:
- List all recipes in kitchen
- Allow filtering/sorting (by name, date, difficulty)
- Provide add/edit/delete actions

**Key Elements**:
- Search/filter bar (by title, ingredient)
- Recipe cards: title, yield, cook time, difficulty, creator
- Actions menu: edit, delete, view details, add to cart
- Pagination (if > 20)
- "Add Recipe" button

**Table Alternative** (desktop):
- Columns: Title, Yield, Cook Time, Difficulty, Created By, Actions

---

### Add Recipe (Capture)

**Path**: `/kitchen/[id]/recipes/add`  
**Component**: `app/kitchen/[id]/recipes/add/page.tsx`

**Responsibility**:
- Capture recipe from 3 sources: text, URL, photo
- Show extraction progress/result (draft)
- Allow user to review/edit before saving

**Key Elements**:
1. **Source Selection**:
   - Tabs: "Paste Text", "Enter URL", "Upload Photo"

2. **Paste Text Tab**:
   - Large textarea for recipe text
   - "Extract" button
   - Progress spinner (2-5 seconds)

3. **Enter URL Tab**:
   - Input field for URL
   - "Extract" button
   - SSRF warning: "We'll fetch and parse this URL safely"

4. **Upload Photo Tab**:
   - File upload (image only)
   - "Extract" button
   - Progress spinner

5. **Draft Review (after extraction)**:
   - Title (editable)
   - Instructions (editable, markdown support)
   - Ingredients table (editable):
     - Columns: Name, Quantity, Unit, Notes, New?
     - Add/remove rows
     - Mark items as non-linear (for manual review during scaling)
   - Metadata: yield servings, cook time, prep time, difficulty
   - "Save" and "Cancel" buttons

6. **Error State**:
   - If extraction fails (not a recipe), show reason
   - Allow user to try again or manually create recipe

---

### Recipe Detail

**Path**: `/kitchen/[id]/recipes/[recipe_id]`  
**Component**: `app/kitchen/[id]/recipes/[id]/page.tsx`

**Responsibility**:
- Display full recipe details
- Allow viewing/editing
- Show usage in shopping lists

**Key Elements**:
- Title, yield, cook/prep times, difficulty
- Source (URL or upload date)
- Ingredients table (read-only or edit mode)
- Instructions (formatted)
- "Edit", "Delete", "Add to Shopping List" actions
- Kitchen members can view; members can edit (future refinement)

---

### Shopping List Generator

**Path**: `/kitchen/[id]/shopping-list`  
**Component**: `app/kitchen/[id]/shopping-list/page.tsx`

**Responsibility**:
- Select recipes, enter headcount, generate consolidated list
- Display and export (PDF, markdown, copy)

**Key Elements**:
1. **Selection Panel**:
   - Recipe multi-select (checkboxes or pills)
   - Search recipes by name
   - Headcount input (spinner or text)
   - "Generate List" button

2. **Generated List**:
   - Grouped by category (Produce, Dairy, Pantry, ...)
   - Columns: Ingredient, Quantity, Unit, In Recipes
   - Checkbox to mark items as purchased (local, not saved)
   - Non-linear items flagged: "Salt (to taste) — review"
   - Edit mode: allow adjusting quantities

3. **Export Options**:
   - "Export as PDF" button → download
   - "Export as Markdown" → copy to clipboard
   - "Print" button
   - "Share Link" (out of scope for v1)

4. **Saved Lists** (if persisted):
   - Show history of generated lists
   - Allow viewing past lists

---

### Kitchen Assistant (Ask)

**Path**: `/kitchen/[id]/ask`  
**Component**: `app/kitchen/[id]/ask/page.tsx`

**Responsibility**:
- Chat interface for asking questions about the kitchen
- Display conversation history and citations

**Key Elements**:
1. **Conversation View**:
   - Message history (user messages left, assistant right)
   - User messages: plain text
   - Assistant messages: formatted text + recipe citations

2. **Input Area**:
   - Text input ("What can we make...?")
   - @mention recipes (autocomplete)
   - "Send" button
   - Progress indicator while awaiting response

3. **Citation Display**:
   - When assistant mentions a recipe, show inline link
   - Hoverable preview of recipe
   - Click to view full recipe

4. **Conversation List** (sidebar or tabs):
   - List of recent conversations
   - Start new conversation button

---

### Ingredient Catalog

**Path**: `/kitchen/[id]/ingredients`  
**Component**: `app/kitchen/[id]/ingredients/page.tsx`

**Responsibility**:
- View and manage kitchen's ingredient catalog
- Create new ingredients, edit canonical names, manage aliases

**Key Elements**:
- Search/filter by name or category
- Table: Canonical Name, Category, Aliases, Recipe Count, Actions
- "Add Ingredient" button
- Edit mode: change canonical name, add aliases, change category
- Delete button (with warning if used in recipes)

---

### Members & Invites

**Path**: `/kitchen/[id]/members`  
**Component**: `app/kitchen/[id]/members/page.tsx`

**Responsibility**:
- View kitchen members, send invites, manage roles

**Key Elements**:
- Members list: Name, Role, Joined Date, Actions (remove for owner)
- "Send Invite" button → modal
- Invite modal: email input, role select (Visitor/Member), "Send" button
- Pending invites list: email, sent date, resend/revoke buttons

---

### Kitchen Settings

**Path**: `/kitchen/[id]/settings`  
**Component**: `app/kitchen/[id]/settings/page.tsx`

**Responsibility**:
- Configure kitchen (name, language, timezone, etc.)
- Owner-only access

**Key Elements**:
- Kitchen name (editable)
- Content language: English / Spanish
- Timezone (future: for scheduling)
- Delete kitchen button (with confirmation)

---

### User Account

**Path**: `/account`  
**Component**: `app/account/page.tsx`

**Responsibility**:
- View/edit user profile
- Change password
- Manage sessions

**Key Elements**:
- Profile: alias, email, photo (upload)
- Theme: Light / Dark / System
- Password change (links to reset flow)
- Sign out button

---

## Shared Components

### AppShell

**Component**: `components/layout/AppShell.tsx`

**Responsibility**:
- Layout wrapper for all authenticated pages
- Sidebar with kitchen navigation
- Header with user menu, notifications

**Structure**:
```
┌──────────────────────────────────────┐
│ Header (Melos logo, user menu)      │
├─────────────────┬────────────────────┤
│                 │                    │
│ Sidebar         │ Page Content       │
│ - Kitchen name  │                    │
│ - Nav: Overview │                    │
│   Recipes       │                    │
│   Ingredients   │                    │
│   Shopping List │                    │
│   Ask           │                    │
│   Members       │                    │
│   Settings      │                    │
│                 │                    │
└─────────────────┴────────────────────┘
```

### RecipeCard

**Component**: `components/recipe/RecipeCard.tsx`

**Props**:
```typescript
{
  recipe: Recipe
  onClick?: () => void
  showActions?: boolean
  onEdit?: () => void
  onDelete?: () => void
}
```

**Renders**:
- Title, yield, cook time, difficulty
- Creator name (small)
- 1-2 image placeholders or ingredient icons

### RecipeForm

**Component**: `components/recipe/RecipeForm.tsx`

**Props**:
```typescript
{
  initialData?: Recipe
  onSubmit: (recipe) => Promise<void>
  isDraft?: boolean
}
```

**Renders**:
- Title, yield, cook/prep times, difficulty
- Instructions textarea
- Ingredients table (add/remove rows)
- Save/Cancel buttons

### ShoppingListView

**Component**: `components/shopping/ShoppingListView.tsx`

**Props**:
```typescript
{
  list: ShoppingList
  editable?: boolean
  onExport?: (format) => void
}
```

**Renders**:
- Items grouped by category
- Quantity, unit, recipes using
- Checkboxes for purchased (local state)
- Export buttons

### ConversationView

**Component**: `components/ask/ConversationView.tsx`

**Props**:
```typescript
{
  conversation: Conversation
  messages: Message[]
  isLoading?: boolean
  onSendMessage: (text, mentionedRecipes) => Promise<void>
}
```

**Renders**:
- Message history (scrollable)
- Input area with @mention autocomplete
- Loading indicator during response

---

## Responsive Breakpoints

- Mobile: < 640px (1 column)
- Tablet: 640px–1024px (2 columns)
- Desktop: > 1024px (3 columns, full sidebar)

---

## Accessibility

- All forms have labels and ARIA roles
- Links use semantic HTML
- Color contrast meets WCAG AA standards
- Keyboard navigation throughout
- Focus indicators visible

---

## Reused Components (from finance-dashboard)

- `AppShell`: Kitchen sidebar + main layout
- `ActionDialog`: Confirmation dialogs (delete recipe, etc.)
- `IconButton`: Compact buttons
- `CopyButton`: Copy-to-clipboard
- `Chip`, `ChipPicker`: Tag/category selection
- `Disclosure`: Expandable sections

---

## Error Handling UI

**Toast Notifications**:
- Success: "Recipe saved!"
- Error: "Failed to add recipe. Please try again."
- Info: "Generating shopping list..."

**Validation Errors** (inline on forms):
- Red text below fields
- Highlight field with red border

**Error Pages**:
- 404: "Kitchen not found"
- 403: "You don't have access to this kitchen"
- 500: "Something went wrong. Please try again."

---

## Loading States

- Recipe extraction: spinner + "Analyzing recipe..." (2–5 seconds)
- Shopping list generation: spinner + "Consolidating ingredients..." (<10 seconds)
- Chat response: spinner + "Thinking..." (<5 seconds)
- Page navigation: skeleton screens for recipe list, ingredients, etc.

---

## Performance Considerations

- Lazy load recipe images (thumbnails)
- Virtualize long lists (100+ recipes)
- Debounce search input (300ms)
- Cache API responses (SWR or TanStack Query)
- Prefetch common pages (recipes, shopping list)
