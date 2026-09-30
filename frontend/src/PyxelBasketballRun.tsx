import { useEffect, useRef, useState } from 'react'

export default function PyxelBasketballRun() {
  const frameRef = useRef<HTMLDivElement>(null)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [isLandscapePhone, setIsLandscapePhone] = useState(false)
  const [dismissedLandscape, setDismissedLandscape] = useState(false)
  const isExpanded = isFullscreen || (isLandscapePhone && !dismissedLandscape)

  useEffect(() => {
    const landscape = window.matchMedia('(pointer: coarse) and (orientation: landscape)')
    const syncLandscape = () => {
      setIsLandscapePhone(landscape.matches)
      setDismissedLandscape(false)
    }
    syncLandscape()
    landscape.addEventListener('change', syncLandscape)
    const syncFullscreen = () => {
      const active = document.fullscreenElement === frameRef.current
      setIsFullscreen(active)
      if (!active) {
        setDismissedLandscape(true)
        window.screen.orientation?.unlock?.()
      }
    }

    document.addEventListener('fullscreenchange', syncFullscreen)
    return () => {
      landscape.removeEventListener('change', syncLandscape)
      document.removeEventListener('fullscreenchange', syncFullscreen)
      window.screen.orientation?.unlock?.()
    }
  }, [])

  useEffect(() => {
    if (!isExpanded) return
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = previousOverflow }
  }, [isExpanded])

  async function toggleFullscreen() {
    const frame = frameRef.current
    if (!frame) return

    if (document.fullscreenElement === frame) {
      await document.exitFullscreen()
      return
    }

    if (isExpanded) {
      setIsFullscreen(false)
      setDismissedLandscape(true)
      window.screen.orientation?.unlock?.()
      return
    }

    setIsFullscreen(true)
    try {
      await frame.requestFullscreen()
    } catch {
      setIsFullscreen(true)
    }
    if (window.matchMedia('(pointer: coarse)').matches) {
      try {
        await window.screen.orientation?.lock('landscape')
      } catch {
        return
      }
    }
  }

  return (
    <section className="basketball-run" aria-label="משחק כדורסל">
      <header className="arcade-header">
        <div>
          <p className="section-kicker">COURT RUN / 02</p>
          <h2>איתי שלומי · בדרך לסל</h2>
        </div>
        <div className="arcade-heading-actions">
          <button
            className="arcade-fullscreen-button"
            type="button"
            title={isExpanded ? 'יציאה ממסך מלא' : 'הפעלת מסך מלא'}
            aria-label={isExpanded ? 'יציאה ממסך מלא' : 'הפעלת מסך מלא'}
            aria-pressed={isExpanded}
            onClick={() => void toggleFullscreen()}
          >
            <span aria-hidden="true">⛶</span>
            {isExpanded ? 'יציאה' : 'מסך מלא'}
          </button>
        </div>
      </header>

      <div className={`arcade-frame${isExpanded ? ' arcade-frame-fullscreen' : ''}`} ref={frameRef}>
        {isExpanded && (
          <button
            className="arcade-fullscreen-button arcade-fullscreen-exit"
            type="button"
            title="יציאה ממסך מלא"
            aria-label="יציאה ממסך מלא"
            onClick={() => void toggleFullscreen()}
          >
            <span aria-hidden="true">⛶</span>
            יציאה
          </button>
        )}
        <iframe
          className="pyxel-game-frame"
          src={`${import.meta.env.BASE_URL}games/basketball-run.html?v=2`}
          title="איתי שלומי · בדרך לסל"
          allow="fullscreen"
        />
      </div>
    </section>
  )
}