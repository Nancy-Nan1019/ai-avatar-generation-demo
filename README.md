# 天猫 AI 头像馆

一个围绕“头像定制”场景搭建的最小可运行原型。  
系统当前聚焦于把中文参数选项、Prompt 组织、图片生成、二次编辑和校园背景替换串成一条完整链路，先做出**可演示、可扩展、可继续优化**的原型系统。

## 项目定位

这个项目当前不是一个通用文生图工作台，而是一个面向头像场景的垂直 Demo。它主要解决以下问题：

- 把截图式参数表整理成前端可点击的中文标签
- 把中文业务描述映射成更规范的视觉 Prompt
- 让首图生成和已有图编辑走两套不同的 Prompt 组织逻辑
- 在算力有限的条件下，先完成“生成 -> 编辑 -> 背景 -> 下载”的闭环

当前版本的核心链路如下：

`中文标签选参 -> 后端 Prompt 组织 -> 首图生成 -> 继续编辑 -> 快速背景合成 -> 下载结果`

## 当前功能

### 1. 中文标签选参

前端支持按分类选择视觉标签，当前覆盖的主要维度包括：

- 基础画风
- IP 衍生风格
- 细节质感
- 发型、五官、面部细节
- 校园身份与二次元人设
- 服装与配饰
- 动作与姿态
- 场景与背景
- 情绪与氛围
- 头像适配与特殊需求

### 2. 首图生成

系统会根据用户选择的中文标签，在后端自动整理正向 Prompt、负向 Prompt 与推理参数，然后调用当前配置的图片后端进行生成。

当前本地默认可跑的轻量方案是：

- `segmind/small-sd`

这条路线的优势是本地能跑通，适合演示完整流程；不足是图片质量有限，尤其在复杂风格和高要求人物场景下效果不够理想。

### 3. 基于已有结果继续编辑

系统支持两种继续编辑方式：

- 直接基于当前生成结果继续修改
- 上传一张已有图片后继续修改

编辑区当前已经支持区分三种编辑方向：

- 人物形象微调
- 风格和气质调整
- 背景方向调整

后端不会再简单复用首图 Prompt，而是单独构建编辑 Prompt，重点表达：

- 需要保留什么
- 想要修改什么
- 目标风格与场景是什么
- 需要避免什么问题

### 4. 背景替换

当前背景区提供两条路线：

- `快速合成`
- `高级背景编辑（预留）`

#### 快速合成

当前已经实现，主要流程是：

1. 抠出人物主体
2. 选择学校与图书馆背景
3. 将人物合成到背景图中

优点：

- 稳定
- 本地可运行
- 适合产品演示

缺点：

- 有时会有一定合成感

#### 高级背景编辑

当前只保留了前端入口和交互模式，尚未接入真正的重模型背景重绘能力。

这部分后续目标是：

- 不只是抠图贴背景
- 而是让模型基于原图直接重绘更自然的背景

### 5. 结果下载

当前结果区支持：

- 预览当前生成或编辑结果
- 显示当前结果来源与上一步操作
- 直接下载当前图片

## 前端界面说明

页面当前按照单列流程式交互组织：

1. 选择角色视觉标签
2. 输入补充描述并配置首图背景
3. 查看首图结果
4. 基于结果继续编辑
5. 进行快速背景合成或切换到高级背景编辑预留模式

前端刻意隐藏了大部分模型实现细节，例如：

- 不直接暴露 Prompt 文本
- 不把页面做成模型调参面板
- 不向用户暴露 mock / diffusers / remote 等技术词

目的是让产品更像“头像定制系统”，而不是纯实验页面。

## Prompt 组织方式

### 1. 首图生成 Prompt

后端当前会按语义桶组织生成 Prompt，主要包括：

- `quality`
- `style`
- `subject`
- `outfit`
- `pose`
- `scene`
- `mood`
- `output`
- `custom`

这样做的目的是避免所有标签简单平铺拼接，让 Prompt 更有结构。

### 2. 编辑 Prompt

编辑场景下，Prompt 重点改为表达：

- 保留人物主体身份
- 保留脸部结构与核心外观
- 明确局部修改方向
- 补充风格与背景目标
- 添加质量与负向约束

这部分的思路参考了更完整的编辑系统框架，但当前仓库只复用了 Prompt 分层与交互逻辑，没有把重型编辑工作流整套引入。

## 代码框架与主要实现

### 前端

当前前端没有使用 React/Vue 构建工具，而是采用原生静态页面实现：

- [static/index.html](./static/index.html)
- [static/app.js](./static/app.js)
- [static/styles.css](./static/styles.css)

主要负责：

- 标签渲染
- 页面交互
- 结果状态更新
- 编辑区与背景区切换逻辑

### 后端

主服务文件为：

- [app.py](./app.py)

当前后端基于 Python 标准库 HTTP 服务实现，主要包括：

- `/api/config`
- `/api/backgrounds`
- `/api/generate`
- `/api/edit`
- `/api/compose-background`

### 配置层

- [config/prompt-mapping.zh-en.json](./config/prompt-mapping.zh-en.json)
  - 中文标签到视觉短语的映射

- [config/backgrounds.json](./config/backgrounds.json)
  - 校园图书馆背景配置

### 辅助目录

- [docs/](./docs/)
  - 架构过程文档

- [prompt_test/](./prompt_test/)
  - Prompt 逻辑与模型调用实验

- [experiments/provider-tests/](./experiments/provider-tests/)
  - Krea、Tongyi 等外部 Provider 测试脚本与效果图

- [colab/](./colab/)
  - Colab 远端服务示例

## 目录结构

```text
.
├─ app.py
├─ static/
│  ├─ index.html
│  ├─ app.js
│  ├─ styles.css
│  └─ backgrounds/
├─ config/
│  ├─ prompt-mapping.zh-en.json
│  └─ backgrounds.json
├─ docs/
├─ prompt_test/
├─ experiments/
│  └─ provider-tests/
├─ colab/
├─ assets/
└─ requirements-diffusers.txt
```

## 本地运行

### 1. 仅查看前端和流程

如果只是先看页面和交互流程：

```powershell
cd D:\XJTLU\Diffusion
python app.py
```

打开：

```text
http://127.0.0.1:8000
```

### 2. 本地 small-sd 生成

如果要运行当前本地轻量模型：

```powershell
cd D:\XJTLU\Diffusion
.\.venv-small-sd\Scripts\Activate.ps1
$env:DIFFUSION_BACKEND="diffusers"
$env:DIFFUSION_MODEL_ID="segmind/small-sd"
python app.py
```

说明：

- 这条路线目前可以运行
- 但效果较弱，属于“流程可跑通，质量一般”的状态

### 3. 快速背景合成依赖

如果要使用背景快速合成，还需要：

```powershell
python -m pip install rembg onnxruntime
```

验证方式：

```powershell
python -c "import rembg; print('rembg ok')"
python -c "import onnxruntime; print('onnxruntime ok')"
```

## 当前测试过的模型

本项目目前测试过的模型主要分为三类：

### 1. 本地轻量模型

#### `segmind/small-sd`

- 用途：本地首图生成、本地继续编辑的轻量路线
- 优点：能在当前机器上跑通
- 缺点：效果不稳定，复杂人物和高质量头像表现较弱

本地 small-sd 中文 Prompt 测试结果：

![small-sd test](./experiments/provider-tests/small_sd_chinese_test.png)

结论：

- 适合作为本地演示链路
- 不适合作为最终高质量效果主力模型

### 2. 外部高质量文本生图模型

#### `krea/Krea-2-Turbo`

- 测试方式：Hugging Face Inference Providers
- 特点：角色感较强，风格表达更精致
- 适合作为高质量头像方向候选

第一组 Krea 结果：

![Krea Test 1](./experiments/provider-tests/krea_test.png)

第二组 Krea 结果：

![Krea Test 2](./experiments/provider-tests/krea_test2.png)

古风仙侠测试结果：

![Krea Xianxia](./experiments/provider-tests/krea_xianxia_test.png)

结论：

- 效果比本地轻量模型明显更好
- 但受 Hugging Face Provider 权限与额度限制，不适合长期免费演示

#### `Tongyi-MAI/Z-Image-Turbo`

- 测试方式：Hugging Face Inference Providers
- 特点：角色主体更稳定，头像构图较清晰

第一组 Tongyi 结果：

![Tongyi Test 1](./experiments/provider-tests/zimage_test3.png)

第二组 Tongyi 结果：

![Tongyi Test 2](./experiments/provider-tests/zimage_test2.png)

古风仙侠测试结果：

![Tongyi Xianxia](./experiments/provider-tests/zimage_xianxia_test.png)

结论：

- 远端效果整体优于 small-sd
- 同样受免费额度限制

### 3. 图像编辑模型

#### `black-forest-labs/FLUX.2-dev`

- 用途：image-to-image 编辑测试
- 测试脚本：`prompt_test/flux2_edit_test.py`
- 作用：验证“基于已有图继续修改”这条路线

示例编辑结果：

![FLUX2 Edit](./prompt_test/outputs/xianxia_avatar_krea_xianxia_avatar_flux2_edit.png)

说明：

- 这条路线更接近真正的高级编辑能力
- 但仍然依赖外部模型与额度
- 本地无法稳定承担该级别的编辑推理

## 现阶段的结论

目前项目已经验证出一个很清楚的现实情况：

- 本地轻量模型可以把系统流程跑通
- 但生成质量与编辑质量都不够理想
- 远端高质量模型效果更好
- 但受限于额度、权限或算力资源

所以当前最合理的工程策略是：

- 本地保留前端与 Prompt 组织系统
- 本地保留 small-sd 作为轻量可运行路线
- 把高质量模型作为远端候选
- 把高级编辑与高级背景编辑继续作为后续扩展方向

## 已知限制

当前项目的主要限制包括：

- 本地显存与算力不足
- 本地轻量模型效果一般
- 背景快速合成需要额外依赖
- 高级背景编辑尚未真正接入
- 外部 Provider 测试受额度影响明显

## 后续方向

下一阶段比较值得继续做的事情：

1. 继续压缩并优化 small-sd 友好的 Prompt 写法
2. 稳定跑通快速背景合成依赖
3. 整理系统能力说明与演示话术
4. 评估是否把高级编辑能力拆成独立服务
5. 将仓库迁移到自己的 GitHub 仓库并持续维护
