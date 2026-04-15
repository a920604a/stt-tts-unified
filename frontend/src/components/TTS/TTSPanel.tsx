import { useEffect, useRef, useState } from 'react'
import { listVoices, synthesize } from '../../api/tts'
import type { Voice } from '../../api/tts'
import './TTSPanel.css'

export default function TTSPanel() {
  const [voices, setVoices] = useState<Voice[]>([])
  const [selectedVoice, setSelectedVoice] = useState('zh-TW-YunJheNeural')
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement>(null)

  useEffect(() => {
    listVoices()
      .then(v => { setVoices(v) })
      .catch(() => setError('無法載入語音列表'))
  }, [])

  useEffect(() => {
    if (audioUrl && audioRef.current) {
      audioRef.current.play().catch(() => {})
    }
  }, [audioUrl])

  const handleSynthesize = async () => {
    if (!text.trim()) return
    setLoading(true)
    setError(null)
    setAudioUrl(null)
    try {
      const result = await synthesize(text, selectedVoice)
      setAudioUrl(result.audio_url)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const zhVoices = voices.filter(v => v.locale.startsWith('zh'))
  const otherVoices = voices.filter(v => !v.locale.startsWith('zh'))

  return (
    <div className="tts-panel">
      <div className="card tts-card">
        <h2 className="panel-title">文字轉語音</h2>
        <p className="panel-desc">輸入文字，選擇語音，即可生成音訊</p>

        <div className="separator" />

        <label className="field-label" htmlFor="tts-text">輸入文字</label>
        <textarea
          id="tts-text"
          className="textarea"
          placeholder="請輸入要合成的文字..."
          value={text}
          onChange={e => setText(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSynthesize()
          }}
          rows={5}
        />
        <p className="char-count">{text.length} 字</p>

        <label className="field-label" htmlFor="voice-select" style={{ marginTop: 'var(--space-4)' }}>
          選擇語音
        </label>
        <select
          id="voice-select"
          className="select"
          value={selectedVoice}
          onChange={e => setSelectedVoice(e.target.value)}
        >
          {zhVoices.length > 0 && (
            <optgroup label="中文語音">
              {zhVoices.map(v => (
                <option key={v.name} value={v.name}>
                  {v.name} ({v.gender})
                </option>
              ))}
            </optgroup>
          )}
          {otherVoices.length > 0 && (
            <optgroup label="其他語音">
              {otherVoices.map(v => (
                <option key={v.name} value={v.name}>
                  {v.name} ({v.locale} · {v.gender})
                </option>
              ))}
            </optgroup>
          )}
        </select>

        {error && <div className="alert alert-error">{error}</div>}

        <button
          className="btn btn-primary tts-submit"
          onClick={handleSynthesize}
          disabled={loading || !text.trim()}
        >
          {loading ? (
            <><span className="spinner" />合成中...</>
          ) : (
            '▶ 開始合成'
          )}
        </button>
        <p className="hint">⌘ + Enter 快捷鍵</p>
      </div>

      {audioUrl && (
        <div className="card audio-result animate-in">
          <h3 className="result-title">合成結果</h3>
          <audio ref={audioRef} controls src={audioUrl} className="audio-player" />
          <div className="audio-actions">
            <a href={audioUrl} download className="btn btn-ghost">下載音檔</a>
          </div>
        </div>
      )}
    </div>
  )
}
