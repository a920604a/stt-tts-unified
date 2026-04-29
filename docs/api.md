# API 文件

| 環境 | Base URL |
|---|---|
| 本地開發（`make dev`） | `http://localhost:8000` |
| Docker（`make up`） | `http://localhost:8008` |

互動式文件：`{BASE_URL}/docs`（Swagger UI）

---

## TTS — 語音合成 `/api/tts`

### `GET /api/tts/voices`

取得所有可用語音列表。

**Response 200**
```json
[
  { "name": "zh-TW-YunJheNeural", "gender": "Male",   "locale": "zh-TW" },
  { "name": "zh-TW-HsiaoChenNeural", "gender": "Female", "locale": "zh-TW" }
]
```

---

### `POST /api/tts/synthesize`

文字轉語音，回傳音檔 URL 與歷史 ID。

**Request Body**
```json
{
  "text": "你好，世界！",
  "voice": { "name": "zh-TW-YunJheNeural", "gender": "Male", "locale": "zh-TW" }
}
```

`voice` 接受三種格式：
- 物件 `{ name, gender, locale }` — 前端標準格式
- 字串 `"zh-TW-YunJheNeural"` — 直接指定語音名稱
- `null` / 省略 — 使用 `/api/settings` 中儲存的 `default_tts_voice`

**Response 200**
```json
{
  "audio_url": "/api/tts/audio/tts_20240101_120000_123456.wav",
  "srt_url":   "/api/tts/audio/tts_20240101_120000_123456.srt",
  "history_id": 42
}
```

**Errors**
| Code | 說明 |
|---|---|
| 400 | 文字為空 或 語音名稱無效 |

---

### `POST /api/tts/stream`

即時串流 TTS 音訊（`audio/mpeg`），適合低延遲播放，不寫入檔案也不記錄歷史。

**Request Body**：同 `/api/tts/synthesize`

**Response**：`audio/mpeg` 串流

---

### `GET /api/tts/audio/{filename}`

下載或播放已合成的音檔（WAV）或字幕檔（SRT）。

---

## STT — 語音辨識 `/api/stt`

### `GET /api/stt/health`

健康檢查。

**Response 200**
```json
{ "status": "ok" }
```

---

### `GET /api/stt/models`

取得可用 Whisper 模型列表。

**Response 200**
```json
["tiny", "base", "small", "medium", "large"]
```

---

### `POST /api/stt/upload`

上傳音訊／影片檔案。

**Request** `multipart/form-data`
- `file` — 音訊檔，支援格式：`mp3 wav m4a flac ogg mp4 avi mov mkv webm`
- 大小上限：500 MB

**Response 200**
```json
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "interview.mp3",
  "size": 15728640,
  "estimated_processing_time": 1.5
}
```

**Errors**
| Code | 說明 |
|---|---|
| 400 | 不支援的檔案格式 |
| 413 | 檔案超過大小限制 |

---

### `POST /api/stt/transcribe`

啟動非同步轉換任務。立即回傳，轉換在背景執行。

**Request Body**
```json
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "model_size": "base",
  "language": "auto",
  "include_timestamps": false
}
```

| 欄位 | 預設值 | 說明 |
|---|---|---|
| `model_size` | `"base"` | `tiny / base / small / medium / large` |
| `language` | `"auto"` | `auto / zh / en / ja / ko` |
| `include_timestamps` | `false` | 是否包含 `[mm:ss - mm:ss]` 時間戳 |

**Response 200**
```json
{ "success": true, "file_id": "550e8400-..." }
```

---

### `GET /api/stt/stream/{file_id}`

SSE 端點，持續推送進度事件直到轉換完成或失敗。前端使用 `EventSource` 接收。

**Response** `text/event-stream`

每個事件 `data:` 欄位為 JSON，格式與 `/api/stt/status/{file_id}` 相同。當 `status` 為 `completed`、`error` 或 `file_not_found` 時，串流結束。

---

### `GET /api/stt/status/{file_id}`

輪詢轉換進度（當不支援 EventSource 時的備用方案）。

**Response 200**
```json
{
  "status": "processing",
  "progress": 65,
  "stage": "語音識別",
  "message": "正在轉換音頻...",
  "timestamp": 1704067200.0,
  "processing_time": 0.0
}
```

| `status` 值 | 說明 |
|---|---|
| `processing` | 轉換中 |
| `completed` | 完成，可取結果 |
| `error` | 失敗，見 `message` |
| `file_not_found` | 找不到此 file_id |

---

### `GET /api/stt/result/{file_id}`

取得轉換完成的文字結果。

**Response 200**
```json
{
  "text": "今天天氣很好，...",
  "word_count": 128,
  "char_count": 512
}
```

**Errors**
| Code | 說明 |
|---|---|
| 404 | 結果尚未完成 |

---

### `GET /api/stt/download/{file_id}`

下載轉換結果為 `.txt` 純文字檔。

---

## 設定 `/api/settings`

### `GET /api/settings`

取得目前套用的設定值。若資料庫中尚未覆寫，回傳 `.env` / `config.py` 的預設值。

**Response 200**
```json
{
  "default_tts_voice": "zh-TW-HsiaoChenNeural"
}
```

---

### `PATCH /api/settings`

更新一個或多個設定，並回傳更新後的完整設定。

**Request Body**（所有欄位皆可選）
```json
{
  "default_tts_voice": "zh-TW-YunJheNeural"
}
```

**Response 200**
```json
{
  "default_tts_voice": "zh-TW-YunJheNeural"
}
```

設定持久化於 SQLite `app_settings` table，重啟後仍生效。

---

## 歷史紀錄 `/api/history`

### `GET /api/history`

取得歷史紀錄清單，依時間倒序排列。

**Query Parameters**

| 參數 | 預設 | 說明 |
|---|---|---|
| `type` | `all` | `all / tts / stt` |
| `limit` | `50` | 最多 200 |
| `offset` | `0` | 分頁偏移 |

**Response 200**
```json
{
  "records": [
    {
      "id": 1,
      "created_at": "2024-01-01T12:00:00+00:00",
      "type": "tts",
      "title": "你好，世界！",
      "voice": "zh-TW-YunJheNeural",
      "audio_filename": "tts_20240101_120000.wav",
      "srt_filename": "tts_20240101_120000.srt"
    },
    {
      "id": 3,
      "created_at": "2024-01-01T11:00:00+00:00",
      "type": "stt",
      "title": "interview.mp3",
      "transcript": "今天天氣很好...",
      "model_size": "base",
      "language": "auto",
      "processing_time": 12.3
    }
  ],
  "total": 2
}
```

---

### `DELETE /api/history/{type}/{id}`

刪除單筆紀錄（硬刪除）。

```
DELETE /api/history/tts/1
DELETE /api/history/stt/3
```

**Response 200**
```json
{ "success": true }
```

**Errors**
| Code | 說明 |
|---|---|
| 404 | 紀錄不存在 |
