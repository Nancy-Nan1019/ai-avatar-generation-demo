# 天猫 AI 头像馆

一个面向头像定制场景的最小可运行原型。前端提供中文参数选择界面，后端把这些选项整理成适合文生图模型理解的英文视觉短语，并输出生成结果预览。当前版本的重点不是做通用文生图工作台，而是围绕“头像定制”这一类明确场景，把参数组织、Prompt 整理和图片后端切换做成一条完整链路。

## 项目目标

这个项目当前主要解决四件事：

- 把截图式参数表整理成可点击的中文标签界面
- 把中文业务词映射成更规范的英文视觉短语，而不是生硬直译
- 给不同图片模型准备统一的输入组织方式
- 在算力有限的条件下，先完成可演示、可对比、可继续扩展的头像生成原型

## 当前实现

- 前端：`static/index.html` + `static/app.js` + `static/styles.css`
- 后端：`app.py`
- 参数映射：`config/prompt-mapping.zh-en.json`
- Colab 远端服务示例：`colab/colab_server.py`
- Provider 测试脚本：`krea_test.py`、`zimage_test.py`、`zimage_test2.py`

项目目前使用 Python 标准库 HTTP 服务，不依赖前端构建工具，也还不是 React + Express 架构。README 中的说明都基于当前仓库里的真实实现，不额外虚构还没落地的能力。

## 页面说明

首页已经调整成单列流程式交互，用户从上到下完成三步：

1. 选择角色视觉标签
2. 按需补充额外中文描述
3. 查看头像结果预览

当前页面刻意隐藏了很多技术细节，例如：

- 不直接给用户展示 Prompt 文本
- 不在页面中暴露 mock / remote / diffusers 等模式词
- 不暴露采样步数、CFG、宽高等底层参数

这样做的目的，是让页面更像“头像定制产品”，而不是“模型调参面板”。

## Prompt 组织方式

### 正向 Prompt

当前正向 Prompt 的来源由三部分组成：

1. 固定质量前缀
2. 中文选项映射出的英文视觉短语
3. 用户补充输入的中文描述

配置文件中的 `promptEn` 已经不是逐字翻译，而是更适合图片模型理解的视觉描述。例如：

- `日系萌系` -> `anime portrait style, cute youthful aesthetic`
- `校园清新` -> `fresh school-life illustration, bright youthful atmosphere`
- `微信头像` -> `avatar-friendly composition, centered face for wechat profile`
- `圆形裁剪兼容` -> `circle-crop friendly framing, face centered in composition`

### 负向 Prompt

当前负向 Prompt 采用两层结构：

- 基础通用负向词
- 按场景自动追加的负向 profiles

目前内置的 profiles 包括：

- `portrait`：头像构图类
- `duo`：双人头像类
- `full_body`：全身像类
- `action`：动作 / 战斗类
- `clean_background`：纯色或留白背景类

这让系统在不同头像场景下，不必完全依赖用户自己写 negative prompt，而是可以自动补一层常见约束。

## 运行方式

### 本地启动

```bash
python app.py
```

打开：

```text
http://127.0.0.1:8000
```

## 后端模式

### `mock`

默认模式，不需要下载模型。页面会返回一张包含 Prompt 摘要的预览图，用于检查参数映射和组合逻辑是否正确。

### `diffusers`

在本机直接调用 `diffusers` 和本地模型。

先安装依赖：

```bash
pip install -r requirements-diffusers.txt
```

再设置环境变量：

```powershell
$env:DIFFUSION_BACKEND="diffusers"
$env:DIFFUSION_MODEL_ID="runwayml/stable-diffusion-v1-5"
python app.py
```

说明：

- 没有 GPU 时会退到 CPU，速度会非常慢
- 当前机器本地只有很弱的显卡和 CPU 版 torch，不适合跑重模型
- `runwayml/stable-diffusion-v1-5` 只是默认值，不代表最终推荐模型

### `remote`

把真实模型放在 Colab 或别的远端 GPU 上运行，本项目只负责 Prompt 整理和请求转发。

```powershell
$env:DIFFUSION_BACKEND="remote"
$env:DIFFUSION_REMOTE_URL="https://你的远端服务地址"
python app.py
```

远端服务需要兼容：

- `POST /generate`
- JSON 请求体中包含 `prompt`、`negative_prompt`、`width`、`height`、`num_inference_steps`、`guidance_scale`

项目里附带了一个 Colab 服务示例：

- `colab/colab_server.py`

## 已测试模型与结果

这一部分记录了当前仓库里已经真实测试过的图片模型、调用方式、效果结果和资源限制。

### 1. `krea/Krea-2-Turbo`

- 测试方式：Hugging Face Inference Providers
- Provider：`fal-ai`
- 测试脚本：[krea_test.py](./krea_test.py)
- 主要特点：角色感和风格化表达都比较强，整体观感偏精致
- 本地运行结论：当前机器本地显卡和 CUDA 环境不足，不适合本地直接推理

测试 Prompt 使用的是一条偏校园风男性角色头像的描述。当前 README 保留两张 Krea 测试图，分别对应原始版本和后续调整 Prompt 后的新版本。

第一张结果如下：

![Krea Test](./krea_test.png)

第二张结果如下：

![Krea Test 2](./krea_test2.png)

测试观察：

- 从结果上看，这条路线的出图风格比较接近我们想要的“精致头像感”
- `krea_test2.png` 对应调整后的 Prompt，说明这条模型路线对提示词变化比较敏感，值得继续做 Prompt 优化
- 但通过 Hugging Face Provider 调用时，权限和额度约束比较明显
- 更适合作为远端高质量模型候选，而不是本地主力方案

第三张选择古风仙侠为主题，结果如下：

![krea_xianxia_test.py](./krea_xianxia_test.py)

![Krea Xianxia Test](./krea_xianxia_test.png)

### 2. `Tongyi-MAI/Z-Image-Turbo`

- 测试方式：Hugging Face Inference Providers
- Provider：`fal-ai`
- 测试脚本：[zimage_test.py](./zimage_test.py)
- 主要特点：支持较清晰的头像构图，角色主体稳定度相对不错
- 本地运行结论：模型本体比 Krea 更现实一些，但对当前机器仍然不适合本地跑

第一张测试图原本使用了较早的一版 Prompt，后来重新整理了更合理的头像描述，因此展示图替换成了新的 `zimage_test3.png`，结果如下：

![Z-Image Test 1](./zimage_test3.png)

测试观察：

- 更新后的 Prompt 在头像构图和主体聚焦上更稳定，更适合做展示图
- 在远端 provider 上可以跑通
- 但免费额度非常有限，第二次继续调用就已经触发 `402 Payment Required`

古风仙侠主题的结果如下：

![tongyi_xianxia_test.py](./tongyi_xianxia_test.py)

![Tongyi Xianxia Test](./zimage_xianxia_test.png)

### 3. `Tongyi-MAI/Z-Image-Turbo` 第二组 Prompt

- 测试方式：Hugging Face Inference Providers
- Provider：`fal-ai`
- 测试脚本：[zimage_test2.py](./zimage_test2.py)
- Prompt 更偏动作氛围、战斗风格和幻想配色

第二组结果图如下：

![Z-Image Test 2](./zimage_test2.png)

测试观察：

- 更适合做风格强、情绪更明显的角色图
- 在风格词较集中的情况下，画面表现力不错
- 但同样受限于 Hugging Face Provider 的月度免费额度

## 测试阶段的现实问题

目前项目已经验证出一个很清楚的现实约束：

- 本地机器显存太小，不适合跑更大的高质量模型
- Colab 免费额度不稳定，也很难长期支撑重模型测试
- Hugging Face Provider 路线可以快速验证效果，但免费额度很快会耗尽
- 更轻量的本地方案虽然可行，但效果又不满足目标

这意味着当前最现实的工程策略不是“完全本地大模型生成”，而是：

- 前端和 Prompt 系统留在本地
- 真实图片生成交给远端高质量模型
- 需要演示时，可以结合少量实时生成和预生成结果图一起展示

## API

### `GET /api/config`

返回中文选项配置和默认生成参数。

### `POST /api/generate`

根据前端选择：

- 组装正向 Prompt
- 自动组合负向 Prompt
- 调用当前模式对应的图片后端

请求体示例：

```json
{
  "selections": {
    "style_base": ["日系萌系"],
    "appearance_hair": ["双马尾", "粉毛"],
    "persona_school_role": ["JK制服女生"],
    "pose_basic": ["半身像"],
    "scene_school": ["教室窗边"],
    "mood_emotion": ["温柔治愈"]
  },
  "customPromptZh": "适合微信头像，整体温柔明亮",
  "width": 512,
  "height": 512,
  "numInferenceSteps": 20,
  "guidanceScale": 6
}
```

## 下一步建议

如果继续往下迭代，当前最推荐的方向是：

1. 把正向 Prompt 从简单拼接升级成模板化组装
2. 给前端增加“分类折叠 / 一级导航”，减少长页面压力
3. 把远端图片后端继续抽象成可切换模式
4. 在 README 和页面中继续补充真实模型测试记录，而不是只写理论说明
