# Step 1 - Current Architecture Baseline

This document records the current frontend/backend structure before we refactor the prompt pipeline. The goal is to make the next prompt-builder changes incremental and low risk.

## 1. Current frontend structure

The current page is defined in `static/index.html` and split into five visible areas:

1. Hero summary
   - project title
   - category count
   - selected option count
   - background material count

2. Step 1 - tag selection
   - Chinese category buttons rendered from `/api/config`
   - reset button
   - selection summary

3. Step 2 - custom description and first-pass background
   - `customPromptZh` textarea
   - `applyBackgroundOnGenerate` checkbox
   - school/background/placement/scale selectors for first-pass generation
   - generate button

4. Existing image edit panel
   - optional upload input
   - `editInstructionZh` textarea
   - edit current result button
   - upload then edit button

5. Standalone background composition panel
   - source mode: current result or upload
   - school/background/placement/scale selectors
   - compose background button

6. Result preview panel
   - result image
   - result note
   - download image button

## 2. Current frontend runtime flow

The current browser logic is in `static/app.js`.

### On page load

- fetch `/api/config`
- fetch `/api/backgrounds`
- render category chips
- render school/background selectors
- set empty result state

### Current user actions

1. Generate first image
   - button: `generateBtn`
   - request: `POST /api/generate`

2. Edit current result
   - button: `editCurrentBtn`
   - request: `POST /api/edit`
   - source image comes from `state.currentImageUrl`

3. Edit uploaded image
   - button: `editUploadBtn`
   - request: `POST /api/edit`
   - source image comes from uploaded file

4. Compose school library background
   - button: `composeBackgroundBtn`
   - request: `POST /api/compose-background`

5. Download current image
   - button: `downloadImageBtn`
   - downloads the current browser-visible image URL directly

## 3. Current backend API surface

The backend is a single HTTP server in `app.py`.

### GET endpoints

- `GET /`
  - serves `static/index.html`

- `GET /static/...`
  - serves static files

- `GET /api/config`
  - returns the prompt mapping config from `config/prompt-mapping.zh-en.json`

- `GET /api/backgrounds`
  - returns school library background metadata from `config/backgrounds.json`

### POST endpoints

- `POST /api/generate`
  - input: JSON payload
  - builds prompt with `build_prompt(...)`
  - generates image with `try_generate_with_diffusers(...)`
  - may optionally compose a school background in the same request

- `POST /api/edit`
  - input: multipart form-data or JSON
  - resolves source image from upload or current result
  - builds prompt with `build_prompt(...)`
  - routes to:
    - `generate_edit_via_diffusers(...)`, or
    - `generate_edit_via_huggingface(...)`

- `POST /api/compose-background`
  - input: multipart form-data or JSON
  - resolves source image from upload or current result
  - uses local cutout/composition flow to place the character on a selected school background

## 4. Current prompt pipeline

The main prompt entry today is:

- `build_prompt(payload)`

This function currently does the following:

1. reads selected Chinese labels from `payload["selections"]`
2. maps them to English prompt phrases from `config/prompt-mapping.zh-en.json`
3. groups them using `CATEGORY_GROUP_MAP`
4. builds:
   - `positivePrompt`
   - `positivePromptZh`
   - `negativePrompt`
   - `promptGroups`
   - `promptGroupsZh`
5. attaches generation defaults

### Current prompt groups

The current group order is:

- `quality`
- `style`
- `persona`
- `appearance`
- `outfit`
- `pose`
- `scene`
- `mood`
- `composition`
- `custom`

### Important current limitation

`build_prompt(...)` is shared by:

- first-pass generation
- image edit
- background-first generation

That means the project still treats "generate a new image" and "edit an existing image" as mostly the same prompt source, which is the main thing we will improve in later steps.

## 5. Current edit prompt pipeline

There are currently two edit prompt builders:

- `build_edit_prompt(payload, prompt_result)`
- `build_local_edit_prompt(payload, prompt_result)`

### Current edit logic

1. reuse the normal generated prompt as the target direction
2. append the Chinese edit instruction
3. append negative prompt constraints
4. send the final text into:
   - local img2img, or
   - Hugging Face image-to-image

### Current limitation

This is still a flat "append more instructions" strategy. It does not yet explicitly separate:

- subject to preserve
- attributes to modify
- scene/background to modify
- avatar framing constraints

This is the exact part we want to improve by borrowing the `image-edit2` prompt-builder idea.

## 6. Current background pipeline

The current background replacement flow is not a model-driven background edit. It is a lightweight local composition flow:

1. extract/cut the character
2. choose a school library background
3. place the character on the selected background
4. output a composited image

This means:

- it is lighter and easier to run locally
- it is more stable for demos
- but it may look less natural than a true model-based background rewrite

## 7. What stays unchanged in Step 2

When we move to Step 2, these parts should remain unchanged:

- the visible Chinese button layout
- the current category ids and option labels used by the frontend
- the existing endpoint names
  - `/api/generate`
  - `/api/edit`
  - `/api/compose-background`
- the current download button
- the current school background asset flow

## 8. What will change in Step 2

The next step should only change backend interpretation, not the visible page structure.

We will refactor the prompt layer so that:

1. selected tags are reorganized into clearer semantic buckets
2. generate prompt and edit prompt stop sharing the same assembly logic
3. edit flow becomes more explicit about:
   - what to preserve
   - what to modify
   - what visual direction to target

## 9. Files that matter for the next step

- `app.py`
  - main backend routes
  - current prompt builders
  - generation and editing dispatch

- `config/prompt-mapping.zh-en.json`
  - Chinese label to prompt phrase mapping

- `static/index.html`
  - current panel structure

- `static/app.js`
  - current frontend request flow

## 10. Step 1 conclusion

The current project already has three usable lanes:

1. Chinese tag -> first-pass avatar generation
2. current/uploaded image -> second-pass image editing
3. current/uploaded image -> school library background composition

So Step 2 does not need a UI rewrite. It only needs a better backend prompt architecture.
