# PodNote

**PodNote** 是一款基于飞牛OS（FNOS）适配的轻量极速文本编辑器，搭载 Monaco Editor 内核。

## 核心特性

* **现代编辑器工作区**：类 VS Code 活动栏与侧边栏，支持多标签页编辑、全局正则查找与替换、只读监听追踪。
* **集成交互式终端**：基于 WebSocket 与 xterm.js，后端桥接 PTY 提供 Linux Bash 终端交互。
* **深度适配飞牛OS**：支持在 FNOS 文件管理器中右键编辑、工具栏一键新建文件，支持常用编码智能识别。
* **语言与语法支持**：主流开发语言语法高亮、前端框架及运维脚本支持，自带 JSON/HTML/CSS 语法校验。

## 目录结构

* [src/](./src/)：Go 后端服务源码。
* [build/](./build/)：飞牛OS 打包分发资源（包含前端网页、配置及打包工具）。
* [chrome_extension/](./chrome_extension/)：配套 FNOS 文件管理器集成的 Chrome/Edge 扩展源码。
* [test/](./test/)：本地开发仿真调试环境。

## 浏览器扩展使用

安装配套扩展以实现 FNOS 文件管理器右键无缝联动。

### 安装步骤
1. **在线安装**：访问 [Microsoft Edge Addons](https://microsoftedge.microsoft.com/addons/detail/ecgbblpdmcifphblcegckelcdhpghjge)。
2. **本地安装**：
   * 打开 `chrome://extensions/`，开启 **开发者模式**。
   * 点击 **加载已解压的扩展程序**，选择项目内 `chrome_extension` 文件夹。

### 配置方式
1. 点击工具栏 PodNote 图标，在配置中填入 FNOS 访问地址（IP 或域名）。
2. 在飞牛文件管理器中右键点击文件即可选择“使用 PodNote 编辑”。

## 致谢

* Monaco Editor: https://github.com/microsoft/monaco-editor
* xterm.js: https://github.com/xtermjs/xterm.js
* marked: https://github.com/markedjs/marked
* 命名与集成方案：shuangji66, 米恋泥
