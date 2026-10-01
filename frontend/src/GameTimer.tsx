import { useEffect, useRef, useState } from 'react'

type TimerStatus = 'idle' | 'running' | 'paused' | 'finished'
type Announcement = { at: number; text: string; language?: string }
type WakeLock = { release: () => Promise<void> }

const NATIVE_TIMER_MODE = new URLSearchParams(window.location.search).get('nativeTimer') === '1'

const ANNOUNCEMENTS: Announcement[] = [
  { at: 300, text: 'נשארו חמש דקות' },
  { at: 120, text: 'נשארו שתי דקות' },
  { at: 60, text: 'נשארה דקה אחת' },
  { at: 30, text: 'נשארו שלושים שניות' },
  { at: 10, text: 'עשר' },
  { at: 9, text: 'תשע' },
  { at: 8, text: 'שמונה' },
  { at: 7, text: 'שבע' },
  { at: 6, text: 'שש' },
  { at: 5, text: 'חמש' },
  { at: 4, text: 'ארבע' },
  { at: 3, text: 'שלוש' },
  { at: 2, text: 'שתיים' },
  { at: 1, text: 'אחת' },
  { at: 0, text: 'Game Over', language: 'en-US' },
]

function speak(text: string, language = 'he-IL') {
  if (NATIVE_TIMER_MODE) return true
  if (!('speechSynthesis' in window)) return false

  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = language
  utterance.rate = 1.15
  window.speechSynthesis.speak(utterance)
  return true
}

function sendNativeTimerCommand(action: 'start' | 'resume' | 'pause' | 'stop', seconds = 0) {
  if (!NATIVE_TIMER_MODE) return
  const intentUrl = `intent://timer/${action}?seconds=${Math.max(0, Math.ceil(seconds))}#Intent;scheme=yomshishi;package=com.yomshishi.app;end`
  window.location.assign(intentUrl)
}

function formatTime(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

export default function GameTimer({ hidden }: { hidden: boolean }) {
  const [durationMinutes, setDurationMinutes] = useState(10)
  const [remainingSeconds, setRemainingSeconds] = useState(600)
  const [status, setStatus] = useState<TimerStatus>('idle')
  const [lastAnnouncement, setLastAnnouncement] = useState('')
  const [voiceAvailable, setVoiceAvailable] = useState(true)
  const [alwaysOnDisplay, setAlwaysOnDisplay] = useState(false)
  const deadlineRef = useRef(0)
  const previousSecondRef = useRef(601)
  const remainingMillisecondsRef = useRef(600_000)
  const wakeLockRef = useRef<WakeLock | null>(null)

  function announce(text: string, language?: string) {
    const available = speak(text, language)
    setVoiceAvailable(available)
    setLastAnnouncement(text)
  }

  function resetTimer() {
    window.speechSynthesis?.cancel()
    sendNativeTimerCommand('stop')
    const seconds = durationMinutes * 60
    remainingMillisecondsRef.current = seconds * 1000
    previousSecondRef.current = seconds + 1
    setRemainingSeconds(seconds)
    setLastAnnouncement('')
    setStatus('idle')
  }

  function startTimer() {
    const wasPaused = status === 'paused'
    const seconds = wasPaused ? remainingMillisecondsRef.current / 1000 : durationMinutes * 60
    if (!wasPaused) {
      remainingMillisecondsRef.current = seconds * 1000
      previousSecondRef.current = Math.ceil(seconds) + 1
      setRemainingSeconds(Math.ceil(seconds))
    }
    window.speechSynthesis?.cancel()
    deadlineRef.current = Date.now() + remainingMillisecondsRef.current
    sendNativeTimerCommand(wasPaused ? 'resume' : 'start', seconds)
    setStatus('running')
  }

  function pauseTimer() {
    remainingMillisecondsRef.current = Math.max(0, deadlineRef.current - Date.now())
    setRemainingSeconds(Math.ceil(remainingMillisecondsRef.current / 1000))
    window.speechSynthesis?.cancel()
    sendNativeTimerCommand('pause', remainingMillisecondsRef.current / 1000)
    setStatus('paused')
  }

  useEffect(() => {
    if (hidden || (status !== 'running' && !alwaysOnDisplay)) return

    const tick = () => {
      const millisecondsLeft = Math.max(0, deadlineRef.current - Date.now())
      const secondsLeft = Math.ceil(millisecondsLeft / 1000)
      setRemainingSeconds(secondsLeft)
      remainingMillisecondsRef.current = millisecondsLeft

      const previousSecond = previousSecondRef.current
      ANNOUNCEMENTS.filter(({ at }) => at < previousSecond && at >= secondsLeft)
        .sort((left, right) => right.at - left.at)
        .forEach(({ at, text, language }) => {
          if (at === 0) setStatus('finished')
          announce(text, language)
        })
      previousSecondRef.current = secondsLeft
    }

    const intervalId = window.setInterval(tick, 100)
    tick()
    return () => window.clearInterval(intervalId)
  }, [status])

  useEffect(() => {
    if (status !== 'running') return

    const requestWakeLock = async () => {
      const wakeLockApi = (navigator as Navigator & { wakeLock?: { request: (type: 'screen') => Promise<WakeLock> } }).wakeLock
      if (!wakeLockApi || document.visibilityState !== 'visible' || wakeLockRef.current) return
      try {
        wakeLockRef.current = await wakeLockApi.request('screen')
      } catch (_error) {
        wakeLockRef.current = null
      }
    }
    const releaseWakeLock = () => {
      const wakeLock = wakeLockRef.current
      wakeLockRef.current = null
      void wakeLock?.release().catch(() => undefined)
    }
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && (status === 'running' || alwaysOnDisplay)) void requestWakeLock()
      else releaseWakeLock()
    }

    void requestWakeLock()
    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      releaseWakeLock()
    }
  }, [alwaysOnDisplay, hidden, status])

  useEffect(() => () => window.speechSynthesis?.cancel(), [])

  function changeDuration(value: string) {
    const parsed = Number(value)
    if (!Number.isFinite(parsed)) return
    const minutes = Math.min(120, Math.max(1, Math.floor(parsed)))
    setDurationMinutes(minutes)
    const seconds = minutes * 60
    remainingMillisecondsRef.current = seconds * 1000
    previousSecondRef.current = seconds + 1
    setRemainingSeconds(seconds)
  }

  const isRunning = status === 'running'
  const isFinished = status === 'finished'
  const toggleAlwaysOnDisplay = () => setAlwaysOnDisplay((enabled) => !enabled)

  return (
    <article className={`card full-width game-timer-card ${alwaysOnDisplay ? 'game-timer-aod' : ''}`} hidden={hidden}>
      <div className="section-head">
        <div>
          <p className="section-kicker">Game Clock</p>
          <h2>טיימר משחק</h2>
        </div>
        <span className={`status-badge ${isRunning ? 'status-CONFIRMED' : isFinished ? 'status-CANCELLED' : 'status-OPEN'}`}>
          {isRunning ? 'המשחק רץ' : isFinished ? 'GAME OVER' : status === 'paused' ? 'מושהה' : 'מוכן'}
        </span>
      </div>

      <div className={`game-timer-display ${isFinished ? 'game-timer-finished' : ''}`} role="timer" aria-label={`זמן נותר ${formatTime(remainingSeconds)}`}>
        {formatTime(remainingSeconds)}
      </div>

      <div className="game-timer-controls">
        <label className="game-timer-duration">
          <span>משך המשחק בדקות</span>
          <input
            type="number"
            min="1"
            max="120"
            value={durationMinutes}
            disabled={status === 'running' || status === 'paused'}
            onChange={(event) => changeDuration(event.target.value)}
          />
        </label>
        <div className="game-timer-actions">
          {isRunning ? (
            <button type="button" className="cta cta-secondary" onClick={pauseTimer}>השהיה</button>
          ) : status === 'paused' ? (
            <button type="button" className="cta cta-primary" onClick={startTimer}>המשך משחק</button>
          ) : (
            <button type="button" className="cta cta-primary" onClick={startTimer}>
              {isFinished ? 'משחק חדש' : 'התחלת משחק'}
            </button>
          )}
          <button type="button" className="cta cta-ghost" onClick={resetTimer}>איפוס</button>
          <button
            type="button"
            className={`cta ${alwaysOnDisplay ? 'cta-primary' : 'cta-secondary'} game-timer-aod-toggle`}
            aria-pressed={alwaysOnDisplay}
            onClick={toggleAlwaysOnDisplay}
          >
            {alwaysOnDisplay ? 'יציאה מ־ALWAYS ON DISPLAY' : 'ALWAYS ON DISPLAY'}
          </button>
        </div>
      </div>

      <p className="game-timer-announcement" aria-live="off">
        {lastAnnouncement || (NATIVE_TIMER_MODE
          ? 'הכריזה הקולית פועלת גם כשהמסך כבוי'
          : voiceAvailable ? 'הכריזה הקולית מוכנה' : 'הכריזה הקולית אינה זמינה במכשיר הזה')}
      </p>
    </article>
  )
}