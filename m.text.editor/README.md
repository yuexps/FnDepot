# NotePod++

**NotePod++** 是一款轻量、极速的文本编辑器，它基于强大的 **Monaco Editor** 核心（VS Code 同款）。

## 特性

- **类 VS Code 视觉风格**：深色现代 UI
- **文件管理深度集成**：在飞牛文件管理器内提供“右键编辑”菜单及工具栏“新建文件”按钮。
- **手动路径打开**：支持在主页输入绝对路径打开文件。
- **快速创建文件**：支持在主页或文件管理工具栏快速创建并编辑新文件。
- **编码自动检测**：自动检测 UTF-8, GBK, Big5, UTF-16 等常见编码，无需手动切换。
- **全方位语法高亮**：
  - **主流开发**：JS/TS, HTML/CSS/SCSS, Go, Python, Rust, Java, C++, PHP, SQL...
  - **Web 框架**：Vue, Svelte, Astro, JSX/TSX...
  - **脚本运维**：Shell (sh/bash/zsh), PowerShell, AWK, Makefile, Dockerfile...
  - **配置数据**：YAML, JSON, TOML, XML, INI, .env, .editorconfig...
  - **安全凭据**：PEM, KEY, CRT, PUB, SSH 证书...

## 浏览器拓展使用

为了在 FNOS 文件管理器中获得最佳的深度集成体验，建议安装配套的浏览器拓展：

1. **安装步骤**：
   - 打开 Chrome/Edge 浏览器，进入 `chrome://extensions/`。
   - 开启右上角的“**开发者模式**”。
   - 点击“**加载已解压的扩展程序**”，选择项目中的 `chrome_extension` 文件夹。
2. **配置说明**：
   - 点击浏览器工具栏的 NotePod++ 图标。
   - 在“自定义网址 / 域名列表”中输入您的 FNOS 访问地址（例如 `192.168.1.100` 或自定义域名）。
   - 拓展会自动感应并在文件管理器中注入“右键编辑”及“新建文件”功能。

## 感谢

- Monaco Editor：https://github.com/microsoft/monaco-editor
- shuangji66 大佬的应用名称
- 米恋泥 大佬的文件管理集成方案
