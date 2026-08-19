const state = {
  config: null,
  backgrounds: null,
  selections: {},
  currentImageUrl: "",
  currentResultSource: "",
  currentResultAction: "",
  backgroundMode: "compose",
};

const EDIT_MODE_COPY = {
  character: {
    placeholder: "\u6bd4\u5982\uff1a\u4fdd\u7559\u8fd9\u4e2a\u4eba\u7684\u8138\u548c\u53d1\u578b\uff0c\u628a\u8863\u670d\u6539\u6210\u6c49\u670d\uff0c\u6574\u4f53\u6c14\u8d28\u66f4\u6e05\u51b7\u4e00\u70b9",
    actionLabel: "\u6b63\u5728\u4f18\u5316\u4eba\u7269\u5f62\u8c61...",
  },
  style: {
    placeholder: "\u6bd4\u5982\uff1a\u4fdd\u7559\u4eba\u7269\u4e0d\u53d8\uff0c\u6574\u4f53\u8272\u8c03\u66f4\u67d4\u548c\uff0c\u753b\u98ce\u66f4\u504f\u6821\u56ed\u6e05\u65b0",
    actionLabel: "\u6b63\u5728\u8c03\u6574\u98ce\u683c\u548c\u6c14\u8d28...",
  },
  background: {
    placeholder: "\u6bd4\u5982\uff1a\u4fdd\u7559\u4eba\u7269\u4e0d\u53d8\uff0c\u80cc\u666f\u66f4\u50cf\u56fe\u4e66\u9986\u6216\u53e4\u98ce\u5ead\u9662\uff0c\u6574\u4f53\u66f4\u81ea\u7136",
    actionLabel: "\u6b63\u5728\u8c03\u6574\u80cc\u666f\u65b9\u5411...",
  },
};

const elements = {
  categories: document.getElementById("categories"),
  resultImage: document.getElementById("resultImage"),
  resultNote: document.getElementById("resultNote"),
  resultSourceLabel: document.getElementById("resultSourceLabel"),
  resultActionLabel: document.getElementById("resultActionLabel"),
  downloadImageBtn: document.getElementById("downloadImageBtn"),
  statusText: document.getElementById("statusText"),
  customPromptZh: document.getElementById("customPromptZh"),
  applyBackgroundOnGenerate: document.getElementById("applyBackgroundOnGenerate"),
  generateSchoolSelect: document.getElementById("generateSchoolSelect"),
  generateBackgroundSelect: document.getElementById("generateBackgroundSelect"),
  generatePlacementSelect: document.getElementById("generatePlacementSelect"),
  generateScalePresetSelect: document.getElementById("generateScalePresetSelect"),
  generateBackgroundPreview: document.getElementById("generateBackgroundPreview"),
  generateBackgroundDescription: document.getElementById("generateBackgroundDescription"),
  editModeSelect: document.getElementById("editModeSelect"),
  editImageInput: document.getElementById("editImageInput"),
  editSourceHint: document.getElementById("editSourceHint"),
  editInstructionZh: document.getElementById("editInstructionZh"),
  composeImageInput: document.getElementById("composeImageInput"),
  composeUploadWrap: document.getElementById("composeUploadWrap"),
  composeSourceMode: document.getElementById("composeSourceMode"),
  schoolSelect: document.getElementById("schoolSelect"),
  backgroundSelect: document.getElementById("backgroundSelect"),
  placementSelect: document.getElementById("placementSelect"),
  scalePresetSelect: document.getElementById("scalePresetSelect"),
  backgroundPreview: document.getElementById("backgroundPreview"),
  backgroundDescription: document.getElementById("backgroundDescription"),
  generateBtn: document.getElementById("generateBtn"),
  editCurrentBtn: document.getElementById("editCurrentBtn"),
  editUploadBtn: document.getElementById("editUploadBtn"),
  composeBackgroundBtn: document.getElementById("composeBackgroundBtn"),
  backgroundModeComposeBtn: document.getElementById("backgroundModeComposeBtn"),
  backgroundModeAdvancedBtn: document.getElementById("backgroundModeAdvancedBtn"),
  backgroundModeHint: document.getElementById("backgroundModeHint"),
  resetBtn: document.getElementById("resetBtn"),
  categoryCount: document.getElementById("categoryCount"),
  selectedCount: document.getElementById("selectedCount"),
  selectedSummaryCount: document.getElementById("selectedSummaryCount"),
  backgroundCount: document.getElementById("backgroundCount"),
};

async function loadInitialData() {
  elements.resultImage.hidden = true;
  elements.resultNote.textContent = "";

  const [configResponse, backgroundResponse] = await Promise.all([
    fetch("/api/config"),
    fetch("/api/backgrounds"),
  ]);

  state.config = await configResponse.json();
  state.backgrounds = await backgroundResponse.json();

  applyDefaults();
  renderCategories();
  renderBackgroundSelectors();
  updateSelectionMetrics();
  setEmptyResult();
  updateEditModeUI();
}

function applyDefaults() {
  elements.categoryCount.textContent = state.config.categories.length;
  const backgroundCount = state.backgrounds.schools.reduce(
    (sum, school) => sum + school.backgrounds.length,
    0,
  );
  elements.backgroundCount.textContent = backgroundCount;
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
    titleMeta.textContent = `${category.options.length} \u4e2a\u53ef\u9009\u9879`;

    titleWrap.append(title, titleMeta);

    const mode = document.createElement("span");
    mode.className = "selection-mode";
    mode.textContent = category.selectionMode === "single" ? "\u5355\u9009" : "\u591a\u9009";

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

function fillSchoolSelect(selectElement) {
  selectElement.innerHTML = "";
  state.backgrounds.schools.forEach((school) => {
    const option = document.createElement("option");
    option.value = school.id;
    option.textContent = school.labelZh;
    selectElement.appendChild(option);
  });
}

function renderBackgroundSelectors() {
  fillSchoolSelect(elements.generateSchoolSelect);
  fillSchoolSelect(elements.schoolSelect);
  syncBackgroundOptions("generate");
  syncBackgroundOptions("compose");
}

function getSchoolById(schoolId) {
  return state.backgrounds.schools.find((school) => school.id === schoolId) || state.backgrounds.schools[0];
}

function getPickerElements(kind) {
  if (kind === "generate") {
    return {
      schoolSelect: elements.generateSchoolSelect,
      backgroundSelect: elements.generateBackgroundSelect,
      preview: elements.generateBackgroundPreview,
      description: elements.generateBackgroundDescription,
    };
  }

  return {
    schoolSelect: elements.schoolSelect,
    backgroundSelect: elements.backgroundSelect,
    preview: elements.backgroundPreview,
    description: elements.backgroundDescription,
  };
}

function getSelectedBackground(kind) {
  const picker = getPickerElements(kind);
  const school = getSchoolById(picker.schoolSelect.value);
  return school.backgrounds.find((item) => item.id === picker.backgroundSelect.value) || school.backgrounds[0];
}

function syncBackgroundOptions(kind) {
  const picker = getPickerElements(kind);
  const school = getSchoolById(picker.schoolSelect.value);
  picker.backgroundSelect.innerHTML = "";

  school.backgrounds.forEach((background) => {
    const option = document.createElement("option");
    option.value = background.id;
    option.textContent = background.labelZh;
    picker.backgroundSelect.appendChild(option);
  });

  updateBackgroundPreview(kind);
}

function updateBackgroundPreview(kind) {
  const picker = getPickerElements(kind);
  const background = getSelectedBackground(kind);
  if (!background) {
    picker.preview.removeAttribute("src");
    picker.description.textContent = "";
    return;
  }

  picker.preview.src = background.imageUrl;
  picker.description.textContent = background.descriptionZh || "";
}

function toggleComposeSourceMode() {
  const useUpload = elements.composeSourceMode.value === "upload";
  elements.composeUploadWrap.hidden = !useUpload;
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

function updateDownloadButton() {
  const hasImage = Boolean(state.currentImageUrl);
  elements.downloadImageBtn.disabled = !hasImage;
}

function getResultSourceLabel(result = {}) {
  const backend = result.backend || "";
  if (backend === "diffusers") {
    return "\u672c\u5730\u9996\u56fe\u751f\u6210";
  }
  if (backend === "huggingface") {
    return "Hugging Face \u9996\u56fe\u751f\u6210";
  }
  if (backend === "diffusers-edit" || backend === "huggingface-edit") {
    return "\u4e8c\u6b21\u7f16\u8f91\u7ed3\u679c";
  }
  if (backend === "compose") {
    return "\u6821\u56ed\u80cc\u666f\u5408\u6210";
  }
  if (backend === "remote") {
    return "\u8fdc\u7a0b\u751f\u6210\u7ed3\u679c";
  }
  if (backend === "mock") {
    return "\u9884\u89c8\u5360\u4f4d\u56fe";
  }
  return "\u5c1a\u672a\u751f\u6210";
}

function updateResultMeta() {
  elements.resultSourceLabel.textContent = state.currentResultSource || "\u5c1a\u672a\u751f\u6210";
  elements.resultActionLabel.textContent = state.currentResultAction || "\u7b49\u5f85\u751f\u6210";
}

function updateBackgroundModeUI() {
  const isCompose = state.backgroundMode === "compose";
  elements.backgroundModeComposeBtn.classList.toggle("active", isCompose);
  elements.backgroundModeAdvancedBtn.classList.toggle("active", !isCompose);
  elements.composeBackgroundBtn.textContent = isCompose
    ? "\u751f\u6210\u6821\u56ed\u80cc\u666f\u56fe"
    : "\u9ad8\u7ea7\u80cc\u666f\u7f16\u8f91\uff08\u9884\u7559\uff09";
  elements.backgroundModeHint.textContent = isCompose
    ? "\u5f53\u524d\u4f7f\u7528\u5feb\u901f\u5408\u6210\uff1a\u540e\u7aef\u4f1a\u57fa\u4e8e\u5f53\u524d\u4eba\u7269\u56fe\u505a\u6290\u56fe/\u7c98\u8d34\u5f0f\u80cc\u666f\u5408\u6210\uff0c\u4f18\u70b9\u662f\u7a33\u5b9a\u3001\u80fd\u8dd1\u3001\u9002\u5408\u6f14\u793a\u3002"
    : "\u9ad8\u7ea7\u80cc\u666f\u7f16\u8f91\u662f\u540e\u7eed\u9884\u7559\u6a21\u5f0f\uff1a\u76ee\u6807\u662f\u7528\u6a21\u578b\u76f4\u63a5\u91cd\u7ed8\u80cc\u666f\uff0c\u6548\u679c\u4f1a\u66f4\u81ea\u7136\uff0c\u4f46\u5bf9\u6a21\u578b\u548c\u7b97\u529b\u8981\u6c42\u66f4\u9ad8\u3002";
}

function getSelectedEditMode() {
  return elements.editModeSelect.value || "character";
}

function updateEditModeUI() {
  const mode = getSelectedEditMode();
  const copy = EDIT_MODE_COPY[mode] || EDIT_MODE_COPY.character;
  elements.editInstructionZh.placeholder = copy.placeholder;

  if (state.currentImageUrl) {
    elements.editSourceHint.textContent = "\u5f53\u524d\u5df2\u6709\u751f\u6210\u7ed3\u679c\uff0c\u53ef\u4ee5\u76f4\u63a5\u70b9\u51fb\u201c\u7ee7\u7eed\u4fee\u6539\u5f53\u524d\u7ed3\u679c\u201d\uff0c\u57fa\u4e8e\u540c\u4e00\u5f20\u56fe\u505a\u5c40\u90e8\u4fee\u6539\u3002";
    return;
  }

  elements.editSourceHint.textContent = "\u8fd8\u6ca1\u6709\u5f53\u524d\u7ed3\u679c\u56fe\u3002\u4f60\u53ef\u4ee5\u5148\u751f\u6210\u4e00\u5f20\u57fa\u7840\u56fe\uff0c\u6216\u8005\u76f4\u63a5\u4e0a\u4f20\u4e00\u5f20\u73b0\u6709\u56fe\u7247\u518d\u4fee\u6539\u3002";
}

function downloadCurrentImage() {
  if (!state.currentImageUrl) {
    return;
  }

  const link = document.createElement("a");
  link.href = state.currentImageUrl;
  const isJpeg = state.currentImageUrl.startsWith("data:image/jpeg") || state.currentImageUrl.endsWith(".jpg") || state.currentImageUrl.endsWith(".jpeg");
  link.download = `avatar-${new Date().toISOString().slice(0, 10)}.${isJpeg ? "jpg" : "png"}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
}

function buildPayload() {
  const defaults = state.config.generationDefaults.inference;
  const selectedGenerateBackground = getSelectedBackground("generate");
  return {
    selections: state.selections,
    customPromptZh: elements.customPromptZh.value.trim(),
    width: Number(defaults.width),
    height: Number(defaults.height),
    numInferenceSteps: Number(defaults.numInferenceSteps),
    guidanceScale: Number(defaults.guidanceScale),
    applyBackgroundOnGenerate: elements.applyBackgroundOnGenerate.checked,
    backgroundId: elements.generateBackgroundSelect.value || selectedGenerateBackground?.id || "",
    placement: elements.generatePlacementSelect.value,
    scalePreset: elements.generateScalePresetSelect.value,
  };
}

function buildEditFormData(options = {}) {
  const formData = new FormData();
  formData.append("selections", JSON.stringify(state.selections));
  formData.append("customPromptZh", elements.customPromptZh.value.trim());
  formData.append("editInstructionZh", elements.editInstructionZh.value.trim());
  formData.append("editMode", getSelectedEditMode());

  const defaults = state.config.generationDefaults.inference;
  formData.append("width", String(defaults.width));
  formData.append("height", String(defaults.height));
  formData.append("numInferenceSteps", String(defaults.numInferenceSteps));
  formData.append("guidanceScale", String(defaults.guidanceScale));

  if (options.useCurrentResult) {
    formData.append("useCurrentResult", "true");
    if (state.currentImageUrl) {
      formData.append("currentImageUrl", state.currentImageUrl);
    }
  }

  if (options.includeUpload && elements.editImageInput.files.length > 0) {
    formData.append("image", elements.editImageInput.files[0]);
  }

  return formData;
}

function buildComposeFormData() {
  const formData = new FormData();
  const selectedComposeBackground = getSelectedBackground("compose");
  formData.append("backgroundId", elements.backgroundSelect.value || selectedComposeBackground?.id || "");
  formData.append("placement", elements.placementSelect.value);
  formData.append("scalePreset", elements.scalePresetSelect.value);

  if (elements.composeSourceMode.value === "current") {
    formData.append("useCurrentResult", "true");
    if (state.currentImageUrl) {
      formData.append("currentImageUrl", state.currentImageUrl);
    }
  }

  if (elements.composeSourceMode.value === "upload" && elements.composeImageInput.files.length > 0) {
    formData.append("image", elements.composeImageInput.files[0]);
  }

  return formData;
}

function setEmptyResult() {
  elements.resultImage.hidden = true;
  elements.resultImage.removeAttribute("src");
  elements.resultNote.textContent = "还未生成图片，请先选择参数后点击“生成头像方案”。";
  elements.statusText.textContent = "等待生成";
  state.currentImageUrl = "";
  state.currentResultSource = "";
  state.currentResultAction = "";
  updateDownloadButton();
  updateResultMeta();
  updateEditModeUI();
}

function applyResult(data, statusMessage) {
  elements.resultImage.hidden = false;
  elements.resultImage.src = data.result.imageUrl;
  state.currentImageUrl = data.result.imageUrl;
  state.currentResultSource = getResultSourceLabel(data.result);
  state.currentResultAction = statusMessage;
  updateDownloadButton();
  updateResultMeta();
  updateEditModeUI();
  elements.resultNote.textContent = data.result.note || "";
  elements.statusText.textContent = statusMessage;
}

async function generatePreview() {
  elements.statusText.textContent = "\u6b63\u5728\u751f\u6210\u9884\u89c8...";
  elements.resultImage.hidden = true;
  elements.resultImage.removeAttribute("src");
  elements.resultNote.textContent = "\u6b63\u5728\u751f\u6210\u5934\u50cf\u65b9\u6848...";

  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(buildPayload()),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || data.result?.note || "\u751f\u6210\u5931\u8d25");
    }
    applyResult(data, elements.applyBackgroundOnGenerate.checked ? "\u5df2\u751f\u6210\u5e26\u6821\u56ed\u80cc\u666f\u7684\u6210\u56fe" : "\u9884\u89c8\u5df2\u66f4\u65b0");
  } catch (error) {
    elements.resultImage.hidden = true;
    elements.resultImage.removeAttribute("src");
    state.currentImageUrl = "";
    state.currentResultAction = "\u751f\u6210\u5931\u8d25";
    updateDownloadButton();
    updateResultMeta();
    elements.resultNote.textContent = error.message;
    elements.statusText.textContent = `\u751f\u6210\u5931\u8d25\uff1a${error.message}`;
  }
}

async function editImage(options = {}) {
  const mode = getSelectedEditMode();
  const copy = EDIT_MODE_COPY[mode] || EDIT_MODE_COPY.character;
  elements.statusText.textContent = copy.actionLabel;
  elements.resultImage.hidden = true;
  elements.resultImage.removeAttribute("src");
  elements.resultNote.textContent = "\u6b63\u5728\u4fee\u6539\u56fe\u7247...";

  if (options.includeUpload && elements.editImageInput.files.length === 0) {
    elements.statusText.textContent = "\u8bf7\u5148\u9009\u62e9\u4e00\u5f20\u56fe\u7247";
    elements.resultNote.textContent = "\u8bf7\u5148\u9009\u62e9\u4e00\u5f20\u56fe\u7247\u518d\u8fdb\u884c\u4fee\u6539\u3002";
    return;
  }

  if (options.useCurrentResult && !state.currentImageUrl) {
    elements.statusText.textContent = "\u5f53\u524d\u8fd8\u6ca1\u6709\u53ef\u7ee7\u7eed\u4fee\u6539\u7684\u7ed3\u679c\u56fe";
    elements.resultNote.textContent = "\u5f53\u524d\u8fd8\u6ca1\u6709\u53ef\u4f9b\u4fee\u6539\u7684\u7ed3\u679c\u56fe\u3002";
    return;
  }

  try {
    const response = await fetch("/api/edit", {
      method: "POST",
      body: buildEditFormData(options),
    });
    const data = await response.json();

    if (!response.ok || !data.ok) {
      throw new Error(data.error || data.result?.note || "\u7f16\u8f91\u5931\u8d25");
    }

    applyResult(data, "\u4fee\u6539\u7ed3\u679c\u5df2\u66f4\u65b0");
  } catch (error) {
    state.currentImageUrl = "";
    state.currentResultAction = "\u4fee\u6539\u5931\u8d25";
    updateDownloadButton();
    updateResultMeta();
    updateEditModeUI();
    elements.statusText.textContent = `\u4fee\u6539\u5931\u8d25\uff1a${error.message}`;
    elements.resultNote.textContent = error.message;
  }
}

async function composeBackground() {
  if (state.backgroundMode === "advanced") {
    elements.statusText.textContent = "\u9ad8\u7ea7\u80cc\u666f\u7f16\u8f91\u6682\u672a\u542f\u7528";
    elements.resultNote.textContent = "\u5df2\u5207\u6362\u5230\u201c\u9ad8\u7ea7\u80cc\u666f\u7f16\u8f91\u201d\u9884\u7559\u6a21\u5f0f\uff0c\u5f53\u524d\u7248\u672c\u8fd8\u672a\u63a5\u5165\u6a21\u578b\u9a71\u52a8\u7684\u80cc\u666f\u91cd\u7ed8\u80fd\u529b\u3002\u73b0\u5728\u53ef\u4ee5\u5148\u4f7f\u7528\u201c\u5feb\u901f\u5408\u6210\u201d\u5b8c\u6210\u6821\u56ed\u80cc\u666f\u6f14\u793a\u3002";
    state.currentResultAction = "\u9ad8\u7ea7\u80cc\u666f\u7f16\u8f91\u9884\u7559\u4e2d";
    updateResultMeta();
    return;
  }

  elements.statusText.textContent = "\u6b63\u5728\u751f\u6210\u80cc\u666f\u5408\u6210\u56fe...";
  elements.resultImage.hidden = true;
  elements.resultImage.removeAttribute("src");
  elements.resultNote.textContent = "\u6b63\u5728\u751f\u6210\u6821\u56ed\u80cc\u666f\u56fe...";

  if (elements.composeSourceMode.value === "current" && !state.currentImageUrl) {
    elements.statusText.textContent = "\u5f53\u524d\u6ca1\u6709\u53ef\u7528\u7684\u4eba\u7269\u7ed3\u679c\u56fe";
    elements.resultNote.textContent = "\u5f53\u524d\u6ca1\u6709\u53ef\u7528\u7684\u4eba\u7269\u7ed3\u679c\u56fe\uff0c\u8bf7\u5148\u751f\u6210\u6216\u4e0a\u4f20\u4e00\u5f20\u4eba\u7269\u56fe\u3002";
    return;
  }

  if (elements.composeSourceMode.value === "upload" && elements.composeImageInput.files.length === 0) {
    elements.statusText.textContent = "\u8bf7\u5148\u4e0a\u4f20\u4e00\u5f20\u4eba\u7269\u56fe";
    elements.resultNote.textContent = "\u8bf7\u5148\u4e0a\u4f20\u4e00\u5f20\u4eba\u7269\u56fe\u518d\u751f\u6210\u6821\u56ed\u80cc\u666f\u56fe\u3002";
    return;
  }

  try {
    const response = await fetch("/api/compose-background", {
      method: "POST",
      body: buildComposeFormData(),
    });
    const data = await response.json();

    if (!response.ok || !data.ok) {
      throw new Error(data.error || data.result?.note || "\u80cc\u666f\u5408\u6210\u5931\u8d25");
    }

    applyResult(data, "\u80cc\u666f\u5408\u6210\u7ed3\u679c\u5df2\u66f4\u65b0");
  } catch (error) {
    state.currentImageUrl = "";
    state.currentResultAction = "\u80cc\u666f\u5408\u6210\u5931\u8d25";
    updateDownloadButton();
    updateResultMeta();
    updateEditModeUI();
    elements.statusText.textContent = `\u80cc\u666f\u5408\u6210\u5931\u8d25\uff1a${error.message}`;
    elements.resultNote.textContent = error.message;
  }
}

function resetSelections() {
  state.selections = {};
  document.querySelectorAll(".chip").forEach((button) => button.classList.remove("selected"));
  elements.customPromptZh.value = "";
  elements.editModeSelect.value = "character";
  elements.editInstructionZh.value = "";
  elements.editImageInput.value = "";
  elements.composeImageInput.value = "";
  state.backgroundMode = "compose";
  elements.applyBackgroundOnGenerate.checked = false;
  elements.composeSourceMode.value = "current";
  elements.generatePlacementSelect.value = "center";
  elements.generateScalePresetSelect.value = "medium";
  elements.placementSelect.value = "center";
  elements.scalePresetSelect.value = "medium";
  toggleComposeSourceMode();
  updateBackgroundModeUI();
  updateSelectionMetrics();
  setEmptyResult();
}

function setBackgroundMode(mode) {
  state.backgroundMode = mode;
  updateBackgroundModeUI();
}

elements.generateBtn.addEventListener("click", generatePreview);
elements.editCurrentBtn.addEventListener("click", () => editImage({ useCurrentResult: true }));
elements.editUploadBtn.addEventListener("click", () => editImage({ includeUpload: true }));
elements.composeBackgroundBtn.addEventListener("click", composeBackground);
elements.downloadImageBtn.addEventListener("click", downloadCurrentImage);
elements.resetBtn.addEventListener("click", resetSelections);
elements.editModeSelect.addEventListener("change", updateEditModeUI);
elements.backgroundModeComposeBtn.addEventListener("click", () => setBackgroundMode("compose"));
elements.backgroundModeAdvancedBtn.addEventListener("click", () => setBackgroundMode("advanced"));
elements.composeSourceMode.addEventListener("change", toggleComposeSourceMode);
elements.generateSchoolSelect.addEventListener("change", () => syncBackgroundOptions("generate"));
elements.generateBackgroundSelect.addEventListener("change", () => updateBackgroundPreview("generate"));
elements.schoolSelect.addEventListener("change", () => syncBackgroundOptions("compose"));
elements.backgroundSelect.addEventListener("change", () => updateBackgroundPreview("compose"));

loadInitialData();
updateBackgroundModeUI();
