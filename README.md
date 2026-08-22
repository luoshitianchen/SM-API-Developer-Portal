# SM API Developer Portal

API开发者门户：应用注册、订阅、配额和文档。

```powershell
git clone https://github.com/luoshitianchen/SM-API-Developer-Portal.git
cd SM-API-Developer-Portal
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8440
```

接口：`/health`、`/readyz`、`/api/overview`、`/api/items`、`/api/ops/metrics`、`/api/crypto/status`。

内置 TrustedHost、安全响应头、CSP、国密状态接口和容器加固。
