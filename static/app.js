const state = {
  config: null,
  selections: {},
};

const elements = {
  categories: document.getElementById("categories"),
  positivePrompt: document.getElementById("positivePrompt"),
  negativePrompt: document.getElementById("negativePrompt"),
  resultImage: document.getElementById("resultImage"),
  resultNote: document.getElementById("resultNote"),
  backendBadge: document.getElementById("backendBadge"),
  heroBackendMode: document.getElementById("heroBackendMode"),
  statusText: document.getElementById("statusText"),
  customPromptZh: document.getElementById("customPromptZh"),
  widthInput: document.getElementById("widthInput"),
  heightInput: document.getElementById("heightInput"),
  stepsInput: document.getElementById("stepsInput"),
  cfgInput: document.getElementById("cfgInput"),
  generateBtn: document.getElementById("generateBtn"),
  resetBtn: document.getElementById("resetBtn"),
  categoryCount: document.getElementById("categoryCount"),
  selectedCount: document.getElementById("selectedCount"),
  selectedSummaryCount: document.getElementById("selectedSummaryCount"),
};

async function loadConfig() {
  const response = await fetch("/api/config");
  state.config = await response.json();
  applyDefaults();
  renderCategories();
  updateSelectionMetrics();
  await generatePreview();
}

function applyDefaults() {
  const defaults = state.config.generationDefaults.inference;
  elements.widthInput.value = defaults.width;
  elements.heightInput.value = defaults.height;
  elements.stepsInput.value = defaults.numInferenceSteps;
  elements.cfgInput.value = defaults.guidanceScale;
  elements.categoryCount.textContent = state.config.categories.length;
}

function renderCategories() {
  elements.categories.innerHTML = "";

  state.config.categories.forEach((category) => {
    const section = document.createElement("section");
    section.className = "category";

    const titleRow = document.createElement("div");
    titleRow.className = "category-title-row";

    const titleWrap = document.createElement("div");

    const title = document.createElement("h3");
    title.textContent = category.labelZh;

    const titleMeta = document.createElement("p");
    titleMeta.className = "category-meta";
    titleMeta.textContent = `${category.options.length} 个可选项`;

    titleWrap.append(title, titleMeta);

    const mode = document.createElement("span");
    mode.className = "selection-mode";
    mode.textContent = category.selectionMode === "single" ? "单选" : "多选";

    titleRow.append(titleWrap, mode);
    section.appendChild(titleRow);

    const optionsWrap = document.createElement("div");
    optionsWrap.className = "options-wrap";

    category.options.forEach((option) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "chip";
      button.textContent = option.labelZh;
      button.title = option.promptEn;
      button.dataset.categoryId = category.id;
      button.dataset.labelZh = option.labelZh;
      button.addEventListener("click", () => toggleOption(category, option.labelZh));
      optionsWrap.appendChild(button);
    });

    section.appendChild(optionsWrap);
    elements.categories.appendChild(section);
  });
}

function toggleOption(category, labelZh) {
  const current = state.selections[category.id] || [];
  let next;

  if (category.selectionMode === "single") {
    next = current.includes(labelZh) ? [] : [labelZh];
  } else {
    next = current.includes(labelZh)
      ? current.filter((item) => item !== labelZh)
      : [...current, labelZh];
  }

  state.selections[category.id] = next;
  syncButtonState(category.id);
  updateSelectionMetrics();
}

function syncButtonState(categoryId) {
  document.querySelectorAll(`[data-category-id="${categoryId}"]`).forEach((button) => {
    const selected = (state.selections[categoryId] || []).includes(button.dataset.labelZh);
    button.classList.toggle("selected", selected);
  });
}

function updateSelectionMetrics() {
  const total = Object.values(state.selections).reduce((sum, items) => sum + items.length, 0);
  elements.selectedCount.textContent = total;
  elements.selectedSummaryCount.textContent = total;
}

function buildPayload() {
  return {
    selections: state.selections,
    customPromptZh: elements.customPromptZh.value.trim(),
    width: Number(elements.widthInput.value),
    height: Number(elements.heightInput.value),
    numInferenceSteps: Number(elements.stepsInput.value),
    guidanceScale: Number(elements.cfgInput.value),
  };
}

async function generatePreview() {
  elements.generateBtn.disabled = true;
  elements.statusText.textContent = "正在生成预览...";

  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(buildPayload()),
    });
    const data = await response.json();

    elements.positivePrompt.textContent = data.prompt.positivePrompt;
    elements.negativePrompt.textContent = data.prompt.negativePrompt;
    elements.resultImage.src = data.result.imageUrl;
    elements.resultNote.textContent = data.result.note;
    elements.backendBadge.textContent = data.result.backend;
    elements.heroBackendMode.textContent = data.result.backend;
    elements.statusText.textContent = "预览已更新";
  } catch (error) {
    elements.statusText.textContent = "生成失败";
    elements.resultNote.textContent = `请求失败：${error.message}`;
  } finally {
    elements.generateBtn.disabled = false;
  }
}

function resetSelections() {
  state.selections = {};
  document.querySelectorAll(".chip").forEach((button) => button.classList.remove("selected"));
  elements.customPromptZh.value = "";
  updateSelectionMetrics();
  generatePreview();
}

elements.generateBtn.addEventListener("click", generatePreview);
elements.resetBtn.addEventListener("click", resetSelections);

loadConfig();
