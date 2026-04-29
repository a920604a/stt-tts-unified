# 開發指南

## 環境需求

| 工具 | 版本 | 說明 |
|---|---|---|
| Python | 3.11+ | 後端執行環境 |
| Node.js | 20+ | 前端建置工具 |
| ffmpeg | 任意 | Whisper 音訊解碼必要 |
| Docker | 20+ | 容器部署（可選）|

### 安裝 ffmpeg

```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt install ffmpeg

# Windows（Chocolatey）
choco install ffmpeg
```

---

## 快速上手

```bash
# 1. 安裝所有依賴
make install

# 2. 啟動開發伺服器（後端 + 前端同時啟動）
make dev
```

| 服務 | URL |
|---|---|
| 前端（Vite dev server） | http://localhost:5173 |
| 後端（FastAPI） | http://localhost:8000 |
| API 互動文件 | http://localhost:8000/docs |

> 開發模式下，前端透過 Vite proxy 將 `/api/*` 請求轉發至後端，CORS 不會有問題。

---

## 設定

### config.yaml（主要設定，推薦）

根目錄的 `config.yaml` 支援階層式設定：

```yaml
server:
  cors_origins: ["*"]
  log_level: info

storage:
  upload_dir: data/uploads
  result_dir: data/results
  audio_dir: data/audio
  db_path: data/history.db
  max_file_size_mb: 500

stt:
  engine: whisper
  whisper:
    model: base        # tiny | base | small | medium | large
    device: cpu        # cpu | cuda | mps
    language: auto     # auto or ISO 639-1 code

tts:
  engine: edge-tts
  edge_tts:
    default_voice: zh-TW-HsiaoChenNeural
    retry_count: 3
    retry_delay_seconds: 2
```

### 環境變數覆蓋

環境變數優先於 `config.yaml`，使用 `__` 作為階層分隔符：

| 環境變數 | 對應 YAML 路徑 | 說明 |
|---|---|---|
| `STT__WHISPER__MODEL` | `stt.whisper.model` | Whisper 模型大小 |
| `STT__WHISPER__DEVICE` | `stt.whisper.device` | 執行裝置 |
| `TTS__EDGE_TTS__DEFAULT_VOICE` | `tts.edge_tts.default_voice` | 預設語音 |
| `STORAGE__MAX_FILE_SIZE_MB` | `storage.max_file_size_mb` | 上傳大小上限 |

優先順序：`環境變數 > .env 檔案 > config.yaml`

> Docker Compose 的 `environment` 區塊繼續有效。

---

## 常用指令

```bash
make help           # 顯示所有指令說明
make install        # 安裝依賴
make dev            # 啟動後端 + 前端
make dev-backend    # 僅啟動後端（hot-reload）
make dev-frontend   # 僅啟動前端
make build          # 建置 React 前端 → frontend/dist/
make lint           # 執行 ruff + tsc 型別檢查
make fmt            # 自動格式化 Python + TypeScript
make clean          # 移除建置產物
make clean-data     # 清除所有執行期資料（謹慎使用）
make up             # docker compose up --build
make down           # docker compose down
make logs           # 追蹤 docker 日誌
make shell          # 進入 container shell
```

---

## 後端架構

```
backend/
├── main.py          FastAPI app factory；掛載 router 與 StaticFiles
├── config.py        Pydantic nested settings（讀取 config.yaml + env var）
├── database.py      aiosqlite 連線池；建立 tts_history / stt_history 表
├── routers/
│   ├── tts.py       /api/tts/* — 語音合成
│   ├── stt.py       /api/stt/* — 語音辨識
│   ├── history.py   /api/history/* — 歷史紀錄
│   └── settings.py  /api/settings — 應用程式設定
├── services/
│   ├── protocols.py         STTEngine / TTSEngine Protocol 介面定義
│   ├── engine_factory.py    get_stt_engine() / get_tts_engine() 工廠函式
│   ├── whisper_service.py   WhisperEngine（實作 STTEngine Protocol）
│   ├── tts_service.py       EdgeTTSEngine（實作 TTSEngine Protocol）
│   ├── settings_service.py  app_settings SQLite KV store
│   └── history_service.py   HistoryService（SQLite CRUD）
└── utils/
    └── file_handler.py      檔案上傳、狀態追蹤、元資料管理
```

### Protocol + Factory 引擎架構

STT / TTS 引擎透過 Protocol 抽象介面定義，factory 依 `config.yaml` 的 `engine` 欄位載入：

```python
# protocols.py
class STTEngine(Protocol):
    async def transcribe(self, file_path, model_size, language, ...) -> dict: ...

class TTSEngine(Protocol):
    async def list_voices(self) -> list[dict]: ...
    async def synthesize(self, text, voice) -> tuple[str, str]: ...

# engine_factory.py
def get_stt_engine() -> STTEngine:   # 讀 config.stt.engine，回傳對應實作
def get_tts_engine() -> TTSEngine:   # 讀 config.tts.engine，回傳對應實作
```

新增引擎只需：實作對應 Protocol → 在 factory 新增 `elif engine == "your-engine"` 分支，**無需修改現有 router 或 service 邏輯**。

### 異步 Whisper 執行

`model.transcribe()` 是 CPU-bound 阻塞呼叫，**必須**用 `asyncio.run_in_executor` 包裝，否則會凍結 FastAPI event loop：

```python
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(
    None,                              # 使用預設 ThreadPoolExecutor
    lambda: model.transcribe(path)     # 阻塞呼叫包在 lambda
)
```

轉換任務透過 `asyncio.create_task()` 在背景執行，進度透過 SSE（`/api/stt/stream/{file_id}`）即時推送。

---

## 前端架構

```
frontend/src/
├── App.tsx                  根元件（ThemeProvider wraps AppShell）
├── context/
│   └── ThemeContext.tsx     Dark mode 狀態（localStorage 持久化）
├── api/
│   ├── tts.ts               TTS API 呼叫
│   ├── stt.ts               STT API 呼叫（upload / transcribe / poll）
│   └── history.ts           History API 呼叫
├── styles/
│   └── globals.css          Apple HIG CSS 變數（light + dark token）
└── components/
    ├── Layout/AppShell.tsx  Header + Tab Nav + Theme Toggle
    ├── TTS/TTSPanel.tsx     文字輸入 → 合成 → 播放
    ├── STT/
    │   ├── STTPanel.tsx     Tab 容器（上傳 / 錄音）+ 設定
    │   ├── FileUpload.tsx   拖曳上傳
    │   ├── Recorder.tsx     MediaRecorder 即時錄音
    │   └── ProgressPoller.tsx  進度輪詢 + 結果顯示
    └── History/
        ├── HistoryPanel.tsx 列表 + filter
        └── HistoryItem.tsx  展開 / 播放 / 刪除
```

### Dark Mode

所有顏色使用 CSS 變數，**不使用** hardcoded hex 值：

```css
/* 正確 */
color: var(--color-label);
background: var(--color-bg-secondary);

/* 錯誤 */
color: #333;
background: #f5f5f5;
```

切換主題時，只需切換 `document.documentElement` 的 `data-theme` 屬性：

```ts
document.documentElement.setAttribute('data-theme', 'dark')
```

---

## 新增語言支援

STT 語言選單位於 [`STTPanel.tsx`](../frontend/src/components/STT/STTPanel.tsx)，新增 `<option>` 即可：

```tsx
<option value="fr">Français</option>
```

Whisper 支援 99 種語言，完整列表見 [openai/whisper](https://github.com/openai/whisper#available-models-and-languages)。

---

## 新增 TTS 引擎

1. 在 `backend/services/` 新增 `your_tts_service.py`，實作 `TTSEngine` Protocol（`list_voices`、`synthesize`、`stream_audio`、`get_audio_path`）
2. 在 `backend/services/engine_factory.py` 的 `get_tts_engine()` 加入：
   ```python
   elif engine == "your-engine":
       return YourTTSEngine(...)
   ```
3. 在 `config.yaml` 設定 `tts.engine: your-engine`

前端與 router 無需任何修改。

同理，新增 STT 引擎：實作 `STTEngine` Protocol → 在 `get_stt_engine()` 註冊 → 更新 `config.yaml`。

---

## 常見問題

### ffmpeg 找不到

```
Error: ffmpeg not found
```

確認 ffmpeg 已安裝並在 PATH 中：

```bash
ffmpeg -version
```

### Whisper 模型下載很慢

模型第一次使用時會從 HuggingFace 下載，快取位於 `~/.cache/whisper`。  
Docker 環境中已透過 `./whisper-cache` volume 持久化，重建 image 不需重新下載。

### Docker image 很大

包含 PyTorch CPU 版本約 ~3 GB。  
若需要 GPU 支援，修改 `Dockerfile` 中的 torch 安裝指令，移除 `--index-url` 改用 CUDA 版本。

### 前端 API 呼叫 404

確認後端已啟動，且 `vite.config.ts` 中的 proxy 設定正確：

```ts
// 本地開發（make dev）
proxy: {
  '/api': { target: 'http://localhost:8000', changeOrigin: true }
}

// 使用 Docker（make up）
proxy: {
  '/api': { target: 'http://localhost:8008', changeOrigin: true }
}
```
