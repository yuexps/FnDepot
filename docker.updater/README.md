# Docker Updater

Docker Updater 是专为飞牛系统 (FNOS) 打造的 Docker 容器升级管理器（亦支持作为原生 Linux 服务运行）。提供直观的 Web 界面，实现容器版本检测、一键升级、健康探活与故障自愈等功能。

## 核心功能

* **版本检测**：支持手动或定时自动扫描容器并比对最新镜像版本。
* **安全升级**：极速 Spec 克隆重建，一键拉取最新镜像并更新容器。
* **探活自愈**：新容器启动后自动执行健康探活，若异常则自动回滚还原服务。
* **镜像与仓库**：支持私有镜像库凭证配置、加速源设置及一键清理虚悬镜像。
* **消息通知**：支持 SMTP 邮件与多平台 Webhook（微信、钉钉、飞书、自定义）的事件推送。

## 启动模式

### 1. 飞牛模式（带参数 `--fnos`）
* **启动命令**：`./docker-updater --fnos`
* **网络监听**：监听 `TRIM_APPDEST` 目录下的 Unix Domain Socket (`web.sock`) 供网关代理。
* **数据目录**：配置文件与日志存放在环境变量 `TRIM_PKGVAR` 指定的目录下。

### 2. 原生模式（无参数，默认）
* **启动命令**：`./docker-updater`
* **网络监听**：默认监听 TCP 端口 `2293`（支持通过 `PORT` 环境变量自定义）。
* **数据目录**：数据库 `data.db` 与日志 `info.log` 强制保存在程序可执行文件同级目录下。

---

## 编译与构建

1. **前端构建**：
   ```bash
   cd frontend && npm install && npm run build
   ```
2. **后端编译（原生独立运行）**：
   ```bash
   go build -o docker-updater main.go
   ```
3. **应用打包（.fpk 安装包）**：
   * **Windows**：直接运行 `build.cmd`
   * **Linux**：运行 `chmod +x build.sh && ./build.sh`
