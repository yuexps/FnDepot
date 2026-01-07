# Antigravity

Antigravity Tools 是一个专为开发者和 AI 爱好者设计的全功能桌面应用。它将多账号管理、协议转换和智能请求调度完美结合，为您提供一个稳定、极速且成本低廉的 本地 AI 中转站。

## 使用 (Usage)

Antigravity 提供了一个强大的本地 API 网关，支持多种协议转换和智能路由。

### 主要功能

1.  **智能账号仪表盘**: 实时监控所有账号的健康状况和剩余配额，支持自动推荐最佳账号。
2.  **协议转换**:
    *   **OpenAI 格式**: 提供 `/v1/chat/completions` 端点，兼容各类 AI 应用。
    *   **Anthropic 格式**: 提供 `/v1/messages` 接口，支持 Claude CLI。
    *   **Gemini 格式**: 支持 Google 官方 SDK 直接调用。
3.  **智能路由**: 根据请求自动重试、轮换账号，并支持自定义模型映射。

### 🔑 添加账号 (OAuth 登录)

由于服务在远程，OAuth 回调无法自动处理，请使用以下方法：

#### 方法一：手动粘贴回调 URL（推荐）

1. 打开 `http://<服务器IP>:64550`
2. 点击"添加账号" → OAuth 标签页
3. 点击"开始 OAuth" 并复制 OAuth 链接
4. 在本地浏览器打开该链接，完成 Google 认证
5. 认证后浏览器会跳转到 `http://localhost:9004/callback?code=xxx`
6. **页面会显示"无法访问"，这是正常的**
7. 复制地址栏中的完整 URL
8. 回到服务器页面，在 OAuth 界面底部的输入框粘贴该 URL
9. 点击"确认"完成登录

#### 方法二：使用 Refresh Token

1. 通过其他方式获取 Google Refresh Token
2. 在"添加账号" → Token 标签页粘贴

### 接入示例

**基础地址 (Base URL)**: `http://127.0.0.1:8045`

#### Python 调用示例

```python
import openai

client = openai.OpenAI(
    api_key="sk-antigravity", # 任意值即可
    base_url="http://127.0.0.1:8045/v1"
)

response = client.chat.completions.create(
    model="gemini-3-flash",
    messages=[{"role": "user", "content": "你好，请自我介绍"}]
)

print(response.choices[0].message.content)
```

#### Kilo Code 接入

1.  **协议选择**: 建议优先使用 **Gemini 协议**。
2.  **Base URL**: 填写 `http://127.0.0.1:8045`。

## 🔒 安全建议

### 配置反向代理 (Nginx)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:64550;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # SSE 支持
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
    }
}
```

### 添加 HTTPS (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 防火墙配置

```bash
# 仅开放必要端口
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

## 📋 常见问题

### Q: 构建时报错 "openssl not found"
```bash
sudo apt install libssl-dev  # Debian/Ubuntu
sudo yum install openssl-devel  # CentOS
```

### Q: 启动时报错 "Address already in use"
```bash
# 检查端口占用
lsof -i :64550
# 或更换端口
./target/release/antigravity-server --port 9000 ...
```

### Q: OAuth 登录失败
确保：
1. 服务器能访问 Google API (`curl https://oauth2.googleapis.com`)
2. 正确复制了完整的回调 URL（包含 `?code=...`）

## 注意事项 (Precautions)

> [!IMPORTANT]
> **Kilo Code 配置提醒**
> 使用 Kilo Code 时，**请勿使用 OpenAI 模式**。
> Kilo Code 在 OpenAI 模式下会生成 `/v1/chat/completions/responses` 这种非标准路径，导致 Antigravity 返回 404 错误。请务必选择 **Gemini 模式** 并填入上述 Base URL。

> [!NOTE]
> **模型映射**
> 如果遇到特定模型无法连接或报错，由于 Kilo Code 或其他客户端的模型名称可能与 Antigravity 默认设置不一致，请在 Antigravity 的“模型映射”页面设置自定义映射，并查看日志文件进行调试。