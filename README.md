# 天猫 AI 头像馆

一个面向演示场景的中文标签式 AI 头像生成与编辑原型系统。  
前端负责让用户用中文按钮选择角色标签、补充中文描述、选择校园图书馆背景；后端负责把这些信息整理成结构化 Prompt，并分别走首图生成、二次编辑、背景合成三条处理链路。

这个项目当前更偏向“流程验证 + 模型选型 + 交互打样”，而不是已经完成商业化部署的成品。仓库里同时保留了本地轻量模型、Hugging Face Provider、Colab 远端接口和独立实验脚本，用于对比不同路线的可行性。

## 1. 项目定位

当前系统主要想解决的是下面这条链路：

1. 用户在前端用中文选择人物风格、人设、外貌、服装、动作、场景等标签
2. 后端读取 `config/prompt-mapping.zh-en.json`
3. 将中文标签映射成更适合扩散模型的英文视觉短语
4. 组装生成 Prompt / 编辑 Prompt / 背景处理参数
5. 调用本地模型、Hugging Face Provider 或远端 Colab 服务
6. 在页面中展示结果，并支持继续修改、背景替换和浏览器下载

## 2. 当前系统能力总览

### 已实现

- 中文标签选参与分组渲染
- 中文补充描述输入
- 首图生成
- 基于当前结果继续编辑
- 上传已有图片后再编辑
- 编辑模式切换：
  - 人物形象微调
  - 风格与气质调整
  - 背景方向调整
- 生成时直接附加校园图书馆背景
- 独立背景替换
- 结果预览
- 浏览器内下载当前图片

### 预留 / 实验中

- 高级背景编辑入口
- 中文补充描述的自动翻译能力（后端保留了接口与环境变量，但默认不启用）
- 多模型切换与模型选型对比

## 3. 页面交互流程

当前前端页面由 `static/index.html` + `static/app.js` + `static/styles.css` 实现，主要分为五块：

### Step 1：角色视觉标签

- 从 `/api/config` 拉取标签配置
- 以中文按钮方式渲染
- 覆盖基础画风、IP 衍生、细节质感、发型、五官、面部细节、人设、服饰、姿态、动作、场景、情绪、头像适配等分类

### Step 2：补充描述与首图背景

- 用户可输入中文补充描述
- 可勾选“首图生成时直接带校园图书馆背景”
- 可选择学校、场景、人物位置、人物大小

### Step 3：结果图继续修改

- 可直接基于当前结果继续改
- 也可上传已有图片后再改
- 编辑模式分为人物、风格、背景三个方向

### 独立背景替换

- 可直接使用当前结果图
- 或上传一张已有角色图
- 选择学校背景后进行快速合成
- 页面中还保留了“高级背景编辑”入口，目前属于预留模式

### 结果预览与下载

- 所有首图、编辑图、背景合成图都会进入同一个结果区
- 页面右上角提供下载按钮，直接走浏览器下载，不额外依赖 VS Code 本地保存

## 4. Prompt 工程逻辑

项目不是简单把所有中文拼成一句英文，而是做了一个分层的 Prompt 组织过程。

### 4.1 中文标签到英文视觉短语

配置文件：`config/prompt-mapping.zh-en.json`

例如：

- `古风仙侠` -> `xianxia style, ancient chinese fantasy`
- `校园清新` -> `school-life illustration, bright campus style`
- `泪痣` -> `beauty mark under eye`
- `汉服` -> `hanfu outfit`
- `图书馆` -> `library interior`

这里映射的不是机械直译，而是更偏向图像模型可理解的视觉短语。

### 4.2 生成 Prompt 结构

后端在 `app.py` 中会先做 `collect_prompt_context(...)`，再进入 `build_generate_prompt(...)`。

当前主要按这些 bucket 组织：

- `quality`
- `style`
- `subject`
- `outfit`
- `pose`
- `scene`
- `mood`
- `output`
- `custom`

这样做的目的是：

- 把“画风”与“主体设定”分开
- 把“场景”和“情绪氛围”分开
- 把“社交头像裁切约束”单独收口到输出层

### 4.3 编辑 Prompt 与生成 Prompt 分离

后端不是把“编辑要求”直接粗暴拼在原始 Prompt 后面，而是单独提供了两条逻辑：

- `build_edit_prompt(payload, prompt_result)`
- `build_local_edit_prompt(payload, prompt_result)`

两者共同目标是：

- 尽量保留人物身份、脸型、发型、主体轮廓
- 根据编辑模式决定是改人物、改风格，还是改背景方向
- 保留头像展示所需的清晰面部和稳定构图

### 4.4 Negative Prompt

生成与编辑都会带上默认负面约束，避免常见错误，例如：

- 模糊
- 五官异常
- 手部错误
- 低质量纹理
- 裁切不完整

## 5. 背景替换逻辑

当前仓库里的“校园图书馆背景”并不是让扩散模型重新画一张完整新场景，而是一个轻量的本地合成流程。

### 快速合成流程

`人物图 -> 前景分割 -> 去除原背景 -> 读取选中的校园图书馆照片 -> 调整人物位置/大小 -> 合成输出`

对应后端接口：

- `POST /api/compose-background`

依赖：

- `rembg`
- `onnxruntime`

这条路线的特点是：

- 优点：轻量、稳定、容易本地跑通、适合演示
- 缺点：观感上更像“抠图合成”，不如真正的模型重绘自然

### 高级背景编辑

页面里已经保留了“高级背景编辑”入口，但目前还没有落成一条稳定的模型化背景重绘链路。  
也就是说，现阶段真正可用的是“快速合成”，高级编辑属于后续迭代方向。

## 6. 后端接口与代码结构

这个项目后端不是 Flask，也不是 FastAPI 主服务，而是一个 Python 标准库 HTTP Server。

主入口：

- `app.py`

### 当前接口

- `GET /`
  - 返回 `static/index.html`

- `GET /static/...`
  - 返回静态资源

- `GET /api/config`
  - 返回中文标签与 Prompt 映射配置

- `GET /api/backgrounds`
  - 返回学校背景素材配置

- `POST /api/generate`
  - 首图生成
  - 也支持在同一次请求里附加校园背景

- `POST /api/edit`
  - 对当前结果图或上传图做二次编辑

- `POST /api/compose-background`
  - 做独立背景合成

### 当前模型分发逻辑

在 `app.py` 中，首图生成大致有三条路：

- `DIFFUSION_BACKEND=mock`
  - 只返回占位预览图

- `DIFFUSION_BACKEND=diffusers`
  - 走本地模型

- `DIFFUSION_BACKEND=huggingface`
  - 走 Hugging Face Provider

另外还保留了：

- `DIFFUSION_BACKEND=remote`
  - 对接 `colab/colab_server.py`

## 7. 当前目录结构

以下结构基于当前仓库真实内容整理：

```text
.
├─ app.py
├─ requirements-diffusers.txt
├─ config/
│  ├─ backgrounds.json
│  └─ prompt-mapping.zh-en.json
├─ static/
│  ├─ index.html
│  ├─ app.js
│  ├─ styles.css
│  └─ backgrounds/
├─ prompt_test/
│  ├─ shared.py
│  ├─ run_krea_case.py
│  ├─ run_tongyi_case.py
│  ├─ run_ssd1b_case.py
│  ├─ flux2_edit_test.py
│  ├─ show_prompt_only.py
│  └─ outputs/
├─ experiments/
│  └─ provider-tests/
├─ colab/
│  └─ colab_server.py
├─ docs/
│  └─ step1-current-architecture.md
└─ assets/
   └─ reference/
```

## 8. 模型路线与定位说明

这部分很重要：仓库里出现过的模型，不代表都已经稳定接入主站默认流程。

### 8.1 当前本地主流程默认模型

- `segmind/small-sd`

它在 `app.py` 中是默认本地模型 ID：

- `DIFFUSION_MODEL_ID=segmind/small-sd`

它的意义主要是：

- 能在本地轻量环境下尽量跑通整套流程
- 用来验证“前端中文选参 -> Prompt 组装 -> 图片输出 -> 再编辑/换背景”的闭环

但它的实际问题也非常明确：

- 画质一般
- 角色一致性弱
- 对复杂中文语义和古风类题材支持不稳定
- 长 Prompt 和复杂细节承载能力有限

所以 README 里会明确把它定义为：

**本地轻量验证模型，不代表最终效果上限。**

### 8.2 Hugging Face Provider 实验模型

仓库里保留了多条外部 Provider 测试脚本，主要用于对比远端模型效果：

- `krea/Krea-2-Turbo`
- `Tongyi-MAI/Z-Image-Turbo`
- `black-forest-labs/FLUX.2-dev`（图像编辑）

这些模型主要出现在：

- `experiments/provider-tests/`
- `prompt_test/`

它们的作用是：

- 比较不同模型对同一套 Prompt 的响应
- 为前端后续真正接大模型提供依据
- 证明系统流程是成立的，效果受限主要来自算力和模型资源

### 8.3 本地实验过但尚未沉淀为稳定主线的模型

- `segmind/SSD-1B`
- `Tencent-Hunyuan/HunyuanDiT-v1.2-Diffusers`

这两条路线在仓库里有代码依据：

- `prompt_test/run_ssd1b_case.py`
- `app.py` 中对 `StableDiffusionXLPipeline` 与 `HunyuanDiTPipeline` 的分发支持

但当前仓库里没有足够稳定、可直接展示为主结果图的成套输出，因此它们会在下面的表格中被标记为“实验中/验证中”，而不是当前前端默认生产路线。

## 9. 模型对比结论

| 模型 / 路线 | 当前位置 | 是否已接入主站 | 主要作用 | 当前结论 |
|---|---|---:|---|---|
| `segmind/small-sd` | `app.py` 默认本地模型 | 是 | 本地轻量闭环验证 | 能跑通，但效果一般 |
| `krea/Krea-2-Turbo` | `experiments/` + `prompt_test/` | 否 | 远端高质量首图测试 | 效果较好，但受 HF 额度限制 |
| `Tongyi-MAI/Z-Image-Turbo` | `experiments/` + `prompt_test/` | 否 | 远端高质量首图测试 | 效果可观，也受额度限制 |
| `black-forest-labs/FLUX.2-dev` | `prompt_test/flux2_edit_test.py`、`app.py` | 部分 | 远端 image-to-image 编辑实验 | 编辑方向可行 |
| `segmind/SSD-1B` | `prompt_test/run_ssd1b_case.py` | 否 | 本地/Colab 的 SDXL 级实验 | 已接入脚本，仍在验证 |
| `Tencent-Hunyuan/HunyuanDiT-v1.2-Diffusers` | `app.py` | 否 | 中文 Prompt 路线评估 | 有代码支持，但本地资源压力大 |
| `runwayml/stable-diffusion-v1-5` | `colab/colab_server.py` | 否 | Colab 远端 API 验证 | 适合演示远端服务链路 |

## 10. 实验效果图对比

下面只展示仓库中真实存在的图片文件。

### 10.1 Provider 直测：Krea

#### Krea 基础测试

![Krea Test](./experiments/provider-tests/krea_test.png)

#### Krea 修改 Prompt 后测试

![Krea Test 2](./experiments/provider-tests/krea_test2.png)

#### Krea 古风仙侠测试

![Krea Xianxia Test](./experiments/provider-tests/krea_xianxia_test.png)

### 10.2 Provider 直测：Tongyi / Z-Image

#### Tongyi 基础测试

![Tongyi Test](./experiments/provider-tests/zimage_test.png)

#### Tongyi 第二轮测试

![Tongyi Test 2](./experiments/provider-tests/zimage_test2.png)

#### Tongyi 调整 Prompt 后测试

![Tongyi Test 3](./experiments/provider-tests/zimage_test3.png)

#### Tongyi 古风仙侠测试

![Tongyi Xianxia Test](./experiments/provider-tests/zimage_xianxia_test.png)

### 10.3 基于当前 Prompt 管线的标准案例对比

#### 案例 A：古风仙侠头像

Krea：

![Xianxia Krea](./prompt_test/outputs/xianxia_avatar_krea.png)

Tongyi：

![Xianxia Tongyi](./prompt_test/outputs/xianxia_avatar_tongyi.png)

#### 案例 B：校园男生头像

Krea：

![Campus Boy Krea](./prompt_test/outputs/campus_boy_avatar_krea.png)

Tongyi：

![Campus Boy Tongyi](./prompt_test/outputs/campus_boy_avatar_tongyi.png)

## 11. 图像编辑实验

当前编辑功能的核心目标不是“重新从零画一张”，而是：

- 保留已有人物主体
- 按用户要求继续微调
- 测试 image-to-image 在头像场景里的可行性

### 当前主站编辑入口

前端支持两种编辑源：

- 基于当前结果继续编辑
- 上传已有图片再编辑

编辑模式支持：

- 人物形象微调
- 风格与气质调整
- 背景方向调整

### 仓库中的 FLUX.2-dev 编辑实验

实验脚本：

- `prompt_test/flux2_edit_test.py`

这个脚本使用：

- `black-forest-labs/FLUX.2-dev`

用于验证“已有图 -> 根据指令继续修改”的路线。

#### 编辑前

![Edit Before](./prompt_test/outputs/xianxia_avatar_krea.png)

#### 编辑后

![Edit After](./prompt_test/outputs/xianxia_avatar_krea_xianxia_avatar_flux2_edit.png)

#### 背景修改后的延伸结果

![Watertown Result](./prompt_test/outputs/xianxia_avatar_krea_watertown.png)

![Watertown Flux Edit](./prompt_test/outputs/xianxia_avatar_krea_watertown_xianxia_avatar_flux2_edit.png)

说明：

- 这一组结果用于说明编辑链路可行
- 不代表已经沉淀成可稳定本地部署的最终模型方案

## 12. 本地运行方式

### 12.1 最小可运行版本

如果你只是想先把页面和流程跑起来：

```bash
python app.py
```

默认情况下会进入 `mock` 模式：

- 页面可正常打开
- 中文标签可正常选择
- Prompt 组装正常工作
- 结果区返回占位图，便于先验证交互流程

### 12.2 本地 diffusers 路线

安装基础依赖：

```bash
pip install -r requirements-diffusers.txt
```

然后设置：

```bash
DIFFUSION_BACKEND=diffusers
DIFFUSION_MODEL_ID=segmind/small-sd
python app.py
```

如果你想改本地图像编辑模型，还可以额外设置：

```bash
EDIT_DIFFUSERS_MODEL_ID=segmind/small-sd
EDIT_STRENGTH=0.6
```

### 12.3 Hugging Face Provider 路线

```bash
HF_TOKEN=your_token
DIFFUSION_BACKEND=huggingface
HF_PROVIDER=fal-ai
HF_TEXT_TO_IMAGE_MODEL=krea/Krea-2-Turbo
EDIT_IMAGE_MODEL=black-forest-labs/FLUX.2-dev
python app.py
```

注意：

- 这条路线依赖 Hugging Face Provider 额度
- 仓库开发过程中实际遇到过 `402 Payment Required` 等额度问题
- 因此它更适合做实验对比，不适合作为无成本稳定主线

### 12.4 远端 Colab 路线

仓库里保留了一个简单远端服务：

- `colab/colab_server.py`

可在 Colab 中启动后，通过：

```bash
DIFFUSION_BACKEND=remote
DIFFUSION_REMOTE_URL=your_remote_url
python app.py
```

将主站前端接到远端生成服务。

## 13. 背景合成依赖

如果要使用“快速合成背景”能力，还需要补安装：

```bash
pip install rembg onnxruntime
```

否则 `/api/compose-background` 会返回依赖缺失错误。

## 14. 实验脚本说明

### `experiments/provider-tests/`

主要用途：

- 记录 Provider 级别的直接调用方法
- 保存独立效果图
- 做模型初筛

### `prompt_test/`

主要用途：

- 基于主站当前 Prompt 管线生成标准化测试案例
- 比较 Krea / Tongyi 在同一套标签与同一套 Prompt 下的输出差异
- 记录 FLUX.2-dev 编辑实验
- 记录 SSD-1B 这类本地/Colab 候选路线

## 15. 工程判断：为什么当前默认还是 small-sd

结论并不是 `small-sd` 最好，而是：

- 它最容易本地跑通
- 最适合验证完整业务闭环
- 能证明前端、Prompt 管线、编辑入口、背景入口都已经连起来了

当前真正的工程判断是：

1. **闭环已经打通**
   - 中文标签选择
   - Prompt 组装
   - 首图生成
   - 二次编辑
   - 快速背景替换
   - 结果下载

2. **效果上限受模型与算力限制**
   - 本地轻量模型效果一般
   - Hugging Face Provider 效果更好，但免费额度有限
   - 更高质量的中文模型和更强编辑模型仍需要继续选型

3. **项目现阶段更适合向老师展示为“已完成流程原型 + 正在做模型迭代”**

## 16. 当前状态总表

### ✅ 已实现

- 中文标签按钮式前端
- 后端 Prompt 映射与分桶组装
- 首图生成接口
- 二次编辑接口
- 独立背景替换接口
- 校园图书馆背景素材配置
- 浏览器内图片下载
- Krea / Tongyi / FLUX 的独立实验脚本

### 🧪 实验中

- `segmind/small-sd` 本地默认生成路线
- `segmind/SSD-1B` 测试脚本路线
- `Tencent-Hunyuan/HunyuanDiT-v1.2-Diffusers` 本地中文模型路线
- Hugging Face Provider 远端生成
- FLUX.2-dev 远端 image-to-image 编辑

### 🚧 预留 / 计划中

- 高级背景编辑
- 更自然的模型化背景重绘
- 更适合中文语义的本地模型
- 更稳定的翻译增强与 Prompt 压缩策略
- 更高质量的本地 image-to-image 路线

## 17. 相关文件

- 主后端：[app.py](./app.py)
- 前端页面：[static/index.html](./static/index.html)
- 前端逻辑：[static/app.js](./static/app.js)
- 样式文件：[static/styles.css](./static/styles.css)
- 标签映射：[config/prompt-mapping.zh-en.json](./config/prompt-mapping.zh-en.json)
- 背景配置：[config/backgrounds.json](./config/backgrounds.json)
- Prompt 实验：[prompt_test/](./prompt_test/)
- Provider 实验：[experiments/provider-tests/](./experiments/provider-tests/)
- Colab 服务：[colab/colab_server.py](./colab/colab_server.py)
- 架构说明：[docs/step1-current-architecture.md](./docs/step1-current-architecture.md)

---

如果把这个项目放在当前阶段来定义，更准确的说法是：

**它已经不是“只有想法”的阶段，而是一套已经能跑通生成、编辑、换背景、下载流程的头像原型系统；只是最终效果仍然高度依赖模型质量与算力条件。**
