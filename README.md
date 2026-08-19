# Tmall AI Avatar Studio

一个围绕“头像定制”场景搭建的最小可运行原型。  
系统支持中文标签选参、首图生成、基于当前结果继续编辑，以及校园图书馆背景快速合成。

当前版本的重点不是追求最强模型效果，而是先把下面这条产品链路做完整：

`中文标签 -> Prompt 组织 -> 图片生成 -> 二次编辑 -> 背景处理 -> 结果下载`

## 1. Current Scope

当前仓库已经实现的能力：

- 中文视觉标签选择界面
- 标签到视觉 Prompt 的后端映射与分层组织
- 首图生成
- 基于当前结果继续编辑
- 校园图书馆背景快速合成
- 背景模式切换
  - `快速合成`：当前可用
  - `高级背景编辑`：预留入口

当前没有完全落地的能力：

- 真正的高质量高级编辑工作流
- 基于重模型的自然背景重绘
- 稳定的本地大模型推理

## 2. Repository Layout

```text
.
├─ app.py                         # 主后端服务
├─ static/                        # 前端页面、样式、脚本、背景素材
├─ config/                        # Prompt 映射与背景配置
├─ docs/                          # 过程文档与架构说明
├─ prompt_test/                   # Prompt 组合与模型调用实验脚本
├─ experiments/
│  └─ provider-tests/             # 外部模型 Provider 测试脚本与结果图
├─ colab/                         # Colab 远端服务示例
├─ assets/
│  └─ reference/                  # 参考输入素材
└─ requirements-diffusers.txt     # 本地 diffusers 依赖
```

## 3. Main Files

- [app.py](./app.py)
  - 当前项目的主后端
  - 包含首图生成、编辑、背景快速合成接口

- [static/index.html](./static/index.html)
  - 主页面结构

- [static/app.js](./static/app.js)
  - 前端交互逻辑

- [static/styles.css](./static/styles.css)
  - 页面样式

- [config/prompt-mapping.zh-en.json](./config/prompt-mapping.zh-en.json)
  - 中文标签与视觉短语映射

- [config/backgrounds.json](./config/backgrounds.json)
  - 校园背景素材配置

## 4. Product Flow

当前页面按下面的顺序使用：

1. 选择角色视觉标签
2. 输入补充中文描述
3. 生成首图
4. 继续编辑当前结果
5. 快速合成校园背景
6. 下载结果图片

## 5. Prompt Strategy

当前后端已经把 Prompt 分成两条路线：

### Generate Prompt

用于首图生成，主要按这些语义桶组织：

- `quality`
- `style`
- `subject`
- `outfit`
- `pose`
- `scene`
- `mood`
- `output`
- `custom`

### Edit Prompt

用于二次编辑，重点表达：

- 保留什么
- 想改什么
- 目标风格/氛围是什么
- 输出需要避免什么问题

这部分思路参考了更完整的编辑系统设计，但当前仓库只复用了 Prompt 与交互框架，没有把重型编辑引擎整套接进来。

## 6. Run Locally

### 6.1 Mock Mode

如果只是先看页面与交互逻辑：

```powershell
cd D:\XJTLU\Diffusion
python app.py
```

打开：

```text
http://127.0.0.1:8000
```

### 6.2 Diffusers Mode

如果要跑本地模型：

```powershell
cd D:\XJTLU\Diffusion
.\.venv-small-sd\Scripts\Activate.ps1
$env:DIFFUSION_BACKEND="diffusers"
$env:DIFFUSION_MODEL_ID="segmind/small-sd"
python app.py
```

说明：

- 当前这条路线可以运行，但效果有限
- 本地机器算力较弱，生成质量主要受模型和显存限制

### 6.3 Background Compose Dependencies

如果要使用“快速合成背景”，当前环境还需要：

```powershell
python -m pip install rembg onnxruntime
```

验证方式：

```powershell
python -c "import rembg; print('rembg ok')"
python -c "import onnxruntime; print('onnxruntime ok')"
```

## 7. Current Backends

### `mock`

- 默认可用
- 不真实生成图片
- 用于检查参数、页面和 Prompt 逻辑

### `diffusers`

- 使用本地 diffusers 模型
- 适合当前原型演示
- 质量受模型和本地机器限制

### `remote`

- 适合后续接 Colab 或远端 GPU 服务
- 当前仓库保留了远端服务接入结构

## 8. Background Modes

系统当前提供两种背景路线：

### 快速合成

当前已经实现：

- 抠出人物主体
- 贴到预设校园图书馆背景上

优点：

- 稳定
- 本地可运行
- 适合演示

缺点：

- 有时会有合成感

### 高级背景编辑

当前仅预留入口，尚未正式接入重模型工作流。

目标方向：

- 通过更强编辑模型直接重绘背景
- 保持人物主体稳定
- 让结果更自然

## 9. Experiments

仓库中的实验内容已经整理到专门目录：

- [prompt_test/](./prompt_test/)
  - Prompt 组合与模型实验

- [experiments/provider-tests/](./experiments/provider-tests/)
  - Krea、Tongyi 等 Provider 测试脚本与结果图

这些内容主要用于：

- 对比不同模型路线
- 记录 Prompt 调整效果
- 给后续模型选型提供参考

## 10. Current Limitations

当前最主要的限制不是代码，而是资源条件：

- 本地显存与算力有限
- 轻量模型可跑，但质量不够理想
- 高质量模型通常需要远端 GPU 或更复杂工作流
- Hugging Face Provider 路线受额度与权限约束

因此当前项目定位更适合：

- 作为可运行原型
- 作为课程/汇报演示系统
- 作为后续高级编辑服务的前端与调度入口

## 11. Roadmap

下一阶段比较值得继续做的事情：

1. 继续压缩和优化轻量模型 Prompt
2. 稳定跑通背景快速合成依赖
3. 整理演示话术与系统能力说明
4. 评估是否把高级编辑能力拆成独立服务
5. 后续在你自己的 GitHub 仓库中作为主线版本持续维护
