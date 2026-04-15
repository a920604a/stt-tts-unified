import { useEffect, useRef, useState } from 'react'
import { startTranscribe, getStatus, getResult, downloadUrl } from '../../api/stt'
import type { StatusResult, TranscriptResult } from '../../api/stt'
import './ProgressPoller.css'

interface Props {
  fileId: string
  modelSize: string
  language: string
  includeTimestamps: boolean
  onReset: () => void
}

export default function ProgressPoller({ fileId, modelSize, language, includeTimestamps, onReset }: Props) {
  const [status, setStatus] = useState<StatusResult | null>(null)
  const [result, setResult] = useState<TranscriptResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const startedRef = useRef(false)

  useEffect(() => {
    if (startedRef.current) return
    startedRef.current = true

    const run = async () => {
      try {
        await startTranscribe(fileId, modelSize, language, includeTimestamps)
        poll()
      } catch (e: any) {
        setError(e.message)
      }
    }

    const poll = () => {
      intervalRef.current = setInterval(async () => {
        try {
          const s = await getStatus(fileId)
          setStatus(s)

          if (s.status === 'completed') {
            clearInterval(intervalRef.current!)
            const r = await getResult(fileId)
            setResult(r)
          } else if (s.status === 'error') {
            clearInterval(intervalRef.current!)
            setError(s.message || '轉換失敗')
          }
        } catch {
          clearInterval(intervalRef.current!)
          setError('無法取得狀態')
        }
      }, 2000)
    }

    run()
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [fileId])

  const progress = status?.progress ?? 0

  return (
    <div className="poller">
      {!result && !error && (
        <div className="card poller-card animate-in">
          <div className="poller-header">
            <p className="poller-stage">{status?.stage ?? '準備中'}</p>
            <span className="poller-pct">{progress}%</span>
          </div>
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
          <p className="poller-message">{status?.message ?? '正在啟動...'}</p>
        </div>
      )}

      {error && (
        <div className="card poller-card animate-in">
          <div className="poller-error">
            <span className="error-icon">⚠️</span>
            <p>{error}</p>
          </div>
          <button className="btn btn-ghost" onClick={onReset}>重新開始</button>
        </div>
      )}

      {result && (
        <div className="card result-card animate-in">
          <div className="result-stats">
            <div className="stat">
              <span className="stat-value">{result.word_count}</span>
              <span className="stat-label">詞數</span>
            </div>
            <div className="stat">
              <span className="stat-value">{result.char_count}</span>
              <span className="stat-label">字數</span>
            </div>
            {status?.processing_time && (
              <div className="stat">
                <span className="stat-value">{status.processing_time.toFixed(1)}s</span>
                <span className="stat-label">耗時</span>
              </div>
            )}
          </div>
          <textarea className="textarea result-textarea" readOnly value={result.text} rows={10} />
          <div className="result-actions">
            <a href={downloadUrl(fileId)} download className="btn btn-primary">下載文字檔</a>
            <button className="btn btn-ghost" onClick={onReset}>再轉一個</button>
          </div>
        </div>
      )}
    </div>
  )
}
