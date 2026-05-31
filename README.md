# Claude-as-API

Bọc **[Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview)** thành một HTTP API (kiểu OpenAI) chạy local, để bạn gọi Claude từ code/script/ứng dụng khác.

> ⚠️ **Dùng cho mục đích cá nhân.** Khi dùng bằng tài khoản đăng nhập (Claude Pro/Max), KHÔNG được dùng làm backend phục vụ người khác hay bán lại — vi phạm [Terms of Service](https://www.anthropic.com/legal/commercial-terms) của Anthropic. Muốn làm sản phẩm → dùng **API key** trả theo token.

---

## Tính năng

- ✅ Endpoint HTTP `POST /chat` — gọi Claude như một API
- ✅ Dùng được **2 kiểu auth**: tài khoản Claude đang đăng nhập, hoặc `ANTHROPIC_API_KEY`
- ✅ Có **tool** sẵn của Claude Code: `Read`, `Grep`, `Glob`, `Bash` (đọc file, tìm kiếm, chạy lệnh)
- ✅ Hỗ trợ **streaming** (trả token dần)
- ✅ **Khóa token** (`API_TOKEN`) để bảo vệ khi mở ra mạng
- ✅ Validate input + xử lý lỗi an toàn (không lộ chi tiết ra client)
- ✅ Tài liệu API tự sinh tại `/docs`

---

## Yêu cầu

- **Python 3.10+** (đã test 3.12)
- **Claude Code** đã cài và **đã đăng nhập** (gói Pro/Max) — hoặc một `ANTHROPIC_API_KEY`
- Windows / macOS / Linux

---

## Cài đặt

```bash
git clone https://github.com/<user>/claude-api-test.git
cd claude-api-test

python -m venv .venv
# Windows:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

---

## Xác thực (Auth)

| Cách | Thiết lập | Dùng cho |
|------|-----------|----------|
| Tài khoản đăng nhập (mặc định) | Đã `claude` login sẵn → không cần làm gì | Cá nhân |
| API key | `export ANTHROPIC_API_KEY=sk-ant-...` (Windows: `setx`) | Sản phẩm, always-on |

---

## Chạy server

### Cách nhanh (Windows) — dùng `run.ps1`
```powershell
.\run.ps1            # Chế độ LOCAL: chỉ máy này gọi được (localhost)
.\run.ps1 -Expose    # Chế độ MỞ: bind 0.0.0.0, tự bật token + tắt Bash
```

### Chạy thủ công
```bash
# Local
uvicorn api:app --port 8000

# Mở cho LAN / tunnel (kèm bảo mật)
# Windows PowerShell:
$env:API_TOKEN="<chuoi-bi-mat>"; $env:CLAUDE_TOOLS="Read,Grep,Glob"
uvicorn api:app --host 0.0.0.0 --port 8000
```

---

## Cấu hình (biến môi trường)

| Biến | Mặc định | Ý nghĩa |
|------|----------|---------|
| `API_TOKEN` | *(trống)* | Nếu set → mọi request phải kèm `Authorization: Bearer <token>` |
| `CLAUDE_TOOLS` | `Read,Grep,Glob,Bash` | Danh sách tool Claude được dùng |
| `CLAUDE_MAX_PROMPT` | `20000` | Độ dài tối đa của prompt |
| `ANTHROPIC_API_KEY` | *(trống)* | Nếu set → dùng API key thay vì tài khoản login |

---

## API

### `GET /health`
Kiểm tra server sống.
```json
{ "status": "ok" }
```

### `POST /chat`
**Body:**
| Trường | Kiểu | Bắt buộc | Mô tả |
|--------|------|:--:|-------|
| `prompt` | string | ✅ | Câu hỏi / yêu cầu |
| `tools` | string[] | ❌ | Ghi đè tool. `[]` = không dùng tool. Bỏ trống = mặc định |
| `stream` | bool | ❌ | `true` = trả token dần (SSE) |

**Response:**
```json
{ "result": "..." }
```

---

## Ví dụ

**Hỏi thường:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Thủ đô Việt Nam là gì?", "tools": []}'
```

**Đọc & phân tích file (dùng tool):**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Đọc sample_robot.log, đếm lỗi theo mức và chỉ ra lỗi lặp nhiều nhất", "tools": ["Read","Grep","Glob"]}'
```

**Khi có token (chế độ mở):**
```bash
curl -X POST http://192.168.1.20:8000/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "hello", "tools": []}'
```

---

## Dùng từ máy khác

### Cùng mạng WiFi/LAN (KHÔNG cần expose ra Internet)
1. Trên PC: `.\run.ps1 -Expose` (bind `0.0.0.0`)
2. Lấy IP nội bộ: `ipconfig` → ví dụ `192.168.1.20`
3. Mở firewall (PowerShell Admin, 1 lần):
   ```powershell
   New-NetFirewallRule -DisplayName "ClaudeAPI" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
   ```
4. Máy khác gọi: `http://192.168.1.20:8000/chat`

### Mạng khác / ngoài đường (cần tunnel)
```bash
cloudflared tunnel --url http://localhost:8000
```
→ Dùng URL `https://...trycloudflare.com` nó in ra. **Chỉ bật khi cần, xong tắt.**

---

## ⚠️ Bảo mật

- **Bật `API_TOKEN`** trước khi mở ra bất kỳ mạng nào. "Link bí mật" KHÔNG phải bảo mật — bot quét tunnel rất nhanh.
- **Tắt `Bash`** (`CLAUDE_TOOLS=Read,Grep,Glob`) khi mở ra ngoài — nếu không, người gọi có thể khiến Claude chạy lệnh trên máy bạn.
- **Không commit secret:** `.token.txt`, `.env`, file credentials đã được `.gitignore`.
- **Đừng port-forward thẳng ra Internet.** Dùng tunnel tạm và tắt sau khi xong.

---

## Hạn chế

- Server **phải chạy trên máy đang bật** thì API mới connect được. PC tắt = API chết.
- Dùng tài khoản login → tính theo hạn mức gói; từ 15/06/2026 trừ vào quỹ "Agent SDK credit" riêng.
- Muốn always-on (không cần PC) → đổi sang **API key + deploy cloud**.

---

## Cấu trúc

```
claude-api-test/
├── api.py            # FastAPI app (endpoint /chat, /health, auth, tools)
├── run.ps1           # Script chạy nhanh (local / expose)
├── requirements.txt  # claude-agent-sdk, fastapi, uvicorn
├── sample_robot.log  # File log mẫu để test tool Read
├── .gitignore
└── README.md
```

## License

MIT (code). Việc dùng Claude Agent SDK tuân theo điều khoản của Anthropic.
