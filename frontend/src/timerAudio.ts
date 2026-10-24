export type TimerAnnouncement = { at: number; text: string; file: string }
export type TimerClip = { text: string; file: string }

export const GAME_START: TimerClip = { text: 'המשחק התחיל', file: 'game-start.mp3' }
export const ANNOUNCEMENTS: TimerAnnouncement[] = [
  { at: 300, text: 'נשארו חמש דקות', file: 'five-minutes.mp3' },
  { at: 120, text: 'נשארו שתי דקות', file: 'two-minutes.mp3' },
  { at: 60, text: 'דקה אחרונה', file: 'last-minute.mp3' },
  ...['עשר', 'תשע', 'שמונה', 'שבע', 'שש', 'חמש', 'ארבע', 'שלוש', 'שתיים', 'אחת']
    .map((text, index) => ({ at: 10 - index, text, file: `countdown-${10 - index}.mp3` })),
  { at: 0, text: 'המשחק נגמר', file: 'game-over.mp3' },
]

export const RANDOM_COMMENTARY: TimerClip[] = [
  { text: 'איתי שלומי לשלוש...', file: 'random-itai-three.mp3' },
  { text: 'איליי מזנק ומציל את הכדור', file: 'random-elay-save.mp3' },
  { text: 'נועם בעוד שלשה אדירה', file: 'random-noam-three.mp3' },
  { text: 'מושון נכנס וקולע', file: 'random-moshon-score.mp3' },
  { text: 'זה לא נורא להפסיד לסלבדור', file: 'random-salvador.mp3' },
  { text: 'אוי, את הפאלי', file: 'random-fali.mp3' },
  { text: 'נטע את לא בן', file: 'random-neta.mp3' },
]

const RESERVED_MILESTONES = [300, 120, 60]
const MILESTONE_BUFFER_SECONDS = 5
const MIN_RANDOM_SECOND = 15

function isNearMilestone(second: number, totalSeconds: number) {
  if (totalSeconds - second < MILESTONE_BUFFER_SECONDS || second < MIN_RANDOM_SECOND) return true
  return RESERVED_MILESTONES.some((milestone) => Math.abs(second - milestone) < MILESTONE_BUFFER_SECONDS)
}

function shuffledClips(random: () => number) {
  const copy = [...RANDOM_COMMENTARY]
  for (let index = copy.length - 1; index > 0; index--) {
    const swapIndex = Math.floor(random() * (index + 1))
    ;[copy[index], copy[swapIndex]] = [copy[swapIndex], copy[index]]
  }
  return copy
}

export function createRandomCommentarySchedule(totalSeconds: number, random: () => number = Math.random): TimerAnnouncement[] {
  if (totalSeconds <= MIN_RANDOM_SECOND + MILESTONE_BUFFER_SECONDS) return []

  const schedule: TimerAnnouncement[] = []
  let deck: TimerClip[] = []
  let cursor = totalSeconds - (18 + Math.floor(random() * 23))

  while (cursor >= MIN_RANDOM_SECOND) {
    let target = cursor
    if (isNearMilestone(target, totalSeconds)) {
      target -= MILESTONE_BUFFER_SECONDS * 2
    }
    if (target >= MIN_RANDOM_SECOND && !isNearMilestone(target, totalSeconds)) {
      if (deck.length === 0) deck = shuffledClips(random)
      const clip = deck.pop()!
      schedule.push({ at: target, text: clip.text, file: clip.file })
    }
    cursor = Math.min(cursor, target) - (38 + Math.floor(random() * 33))
  }

  return schedule
}

export function getTimerAnnouncement(
  previousSecond: number,
  secondsLeft: number,
  randomSchedule: TimerAnnouncement[] = [],
) {
  // Official time announcements always take priority over random commentary.
  const official = ANNOUNCEMENTS.findLast(({ at }) => at < previousSecond && at >= secondsLeft)
  if (official) return official
  return randomSchedule.findLast(({ at }) => at < previousSecond && at === secondsLeft)
}

export class TimerAudioPlayer {
  private context: AudioContext | null = null
  private buffers: Promise<Map<string, AudioBuffer>> | null = null
  private ready: Promise<Map<string, AudioBuffer>> | null = null
  private source: AudioBufferSourceNode | null = null
  private generation = 0

  prepare() {
    this.context ??= new AudioContext()
    const context = this.context
    // Resume synchronously from the Start/Resume gesture for mobile autoplay policies.
    const resumed = context.resume()
    this.buffers ??= Promise.all(
      [GAME_START, ...ANNOUNCEMENTS, ...RANDOM_COMMENTARY].map(async ({ file }) => {
        const response = await fetch(`${import.meta.env.BASE_URL}audio/timer/${file}`)
        if (!response.ok) throw new Error(`Timer audio ${file}: HTTP ${response.status}`)
        const buffer = await context.decodeAudioData(await response.arrayBuffer())
        return [file, buffer] as const
      }),
    ).then((entries) => new Map(entries))
    this.ready = Promise.all([resumed, this.buffers])
      .then(([, buffers]) => buffers)
      .catch((error: unknown) => {
        this.buffers = null
        throw error
      })
    return this.ready
  }

  async play(file: string, expiresAt: number) {
    this.stop()
    const generation = this.generation
    if (!this.context || !this.ready) throw new Error('Timer audio is not prepared')
    const buffers = await this.ready
    if (generation !== this.generation || Date.now() >= expiresAt) return
    const buffer = buffers.get(file)
    if (!buffer) throw new Error(`Missing timer recording: ${file}`)
    const source = this.context.createBufferSource()
    source.buffer = buffer
    source.connect(this.context.destination)
    source.onended = () => {
      source.disconnect()
      if (this.source === source) this.source = null
    }
    this.source = source
    source.start()
  }

  stop() {
    this.generation++
    this.source?.stop()
    this.source = null
  }

  dispose() {
    this.stop()
    const context = this.context
    this.context = null
    this.buffers = null
    this.ready = null
    return context?.close()
  }
}
