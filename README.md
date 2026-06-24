# Diffusion Prompt Builder MVP

这个项目先实现了一个最小可运行版本：

- 前端显示中文按钮
- 后端根据中文选项拼接英文 prompt
- 暴露 `/api/generate` 接口
- 在没有安装 Stable Diffusion 模型时，默认使用 `mock` 模式返回预览图
- 后续安装好模型依赖后，可以切到 `diffusers` 模式真实生成图片
- 也可以切到 `remote` 模式，把真正的模型推理放到 Colab GPU 上

## 运行方式

```bash
python app.py
```

启动后打开：

```text
http://127.0.0.1:8000
```
