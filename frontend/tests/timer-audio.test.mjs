import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { stripTypeScriptTypes } from 'node:module'
import { afterEach, beforeEach, test } from 'node:test'

const source = await readFile(new URL('../src/timerAudio.ts', import.meta.url), 'utf8')
const javascript = stripTypeScriptTypes(source).replace('import.meta.env.BASE_URL', '"/yomshishi/"')
const {
  ANNOUNCEMENTS,
  createRandomCommentarySchedule,
  GAME_START,
  getTimerAnnouncement,
  RANDOM_COMMENTARY,
  TimerAudioPlayer,
} = await import(`data:text/javascript;base64,${Buffer.from(javascript).toString('base64')}`)

let requests
let contexts
const originalFetch = globalThis.fetch
const originalAudioContext = globalThis.AudioContext

class MockAudioContext {
  destination = {}
  sources = []
  resumeCalls = 0
  closed = false
  constructor() { contexts.push(this) }
  async resume() { this.resumeCalls++ }
  async decodeAudioData(bytes) { return { bytes } }
  createBufferSource() {
    const source = {
      buffer: null,
      started: false,
      stopped: false,
      disconnected: false,
      connect() {},
      disconnect() { this.disconnected = true },
      start() { this.started = true },
      stop() { this.stopped = true; this.onended?.() },
    }
    this.sources.push(source)
    return source
  }
  async close() { this.closed = true }
}

beforeEach(() => {
  requests = []
  contexts = []
  globalThis.AudioContext = MockAudioContext
  globalThis.fetch = async (url) => {
    requests.push(url)
    return { ok: true, arrayBuffer: async () => new ArrayBuffer(1) }
  }
})

afterEach(() => {
  globalThis.fetch = originalFetch
  globalThis.AudioContext = originalAudioContext
})

test('recordings cover the exact milestones, with no synthesized 30-second cue', () => {
  assert.deepEqual(ANNOUNCEMENTS.map(({ at }) => at), [300, 120, 60, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0])
  assert.equal(GAME_START.file, 'game-start.mp3')
  for (const announcement of ANNOUNCEMENTS) {
    assert.equal(getTimerAnnouncement(announcement.at + 1, announcement.at), announcement)
    assert.equal(getTimerAnnouncement(announcement.at, announcement.at), undefined)
  }
  assert.equal(getTimerAnnouncement(31, 30), undefined)
  assert.equal(getTimerAnnouncement(600, 599), undefined)
})

test('a delayed tick selects the current number/end instead of replaying a backlog', () => {
  assert.equal(getTimerAnnouncement(301, 8)?.file, 'countdown-8.mp3')
  assert.equal(getTimerAnnouncement(11, 1)?.file, 'countdown-1.mp3')
  assert.equal(getTimerAnnouncement(301, 0)?.file, 'game-over.mp3')
  assert.equal(getTimerAnnouncement(0, 0), undefined)
})

test('web and Android package identical MP3s for every event', async () => {
  const nativeSource = await readFile(new URL('../../android/app/src/main/java/com/yomshishi/app/GameTimerService.java', import.meta.url), 'utf8')
  const times = nativeSource.match(/ANNOUNCEMENT_TIMES = \{([^}]+)\}/)[1]
    .split(',').map(Number)
  assert.deepEqual(times, ANNOUNCEMENTS.filter(({ at }) => at > 0).map(({ at }) => at))
  assert.equal(RANDOM_COMMENTARY.length, 7)
  for (const { file } of [GAME_START, ...ANNOUNCEMENTS, ...RANDOM_COMMENTARY]) {
    const web = await readFile(new URL(`../public/audio/timer/${file}`, import.meta.url))
    const nativeName = `timer_${file.replaceAll('-', '_')}`
    const native = await readFile(new URL(`../../android/app/src/main/res/raw/${nativeName}`, import.meta.url))
    assert.ok(web.length > 1000, file)
    assert.deepEqual(native, web, file)
    assert.ok(nativeSource.includes(`R.raw.${nativeName.replace('.mp3', '')}`), file)
  }
})

test('random commentary schedule covers all 7 phrases in a 10-minute game and avoids official milestones', () => {
  const schedule = createRandomCommentarySchedule(600, () => 0.35)
  assert.ok(schedule.length >= 7)
  const files = new Set(schedule.map(({ file }) => file))
  assert.equal(files.size, 7)
  for (const { at } of schedule) {
    assert.ok(at >= 15 && at <= 595, `unexpected random timestamp ${at}`)
    for (const milestone of [300, 120, 60]) {
      assert.ok(Math.abs(at - milestone) >= 5, `random timestamp ${at} too close to ${milestone}`)
    }
  }
  const cue = schedule[0]
  assert.equal(getTimerAnnouncement(cue.at + 1, cue.at, schedule)?.file, cue.file)
  assert.equal(getTimerAnnouncement(301, 300, [{ at: 300, text: 'x', file: 'random-fali.mp3' }])?.file, 'five-minutes.mp3')
})

test('preloads all recordings under the Pages base path and unlocks audio on prepare', async () => {
  const player = new TimerAudioPlayer()
  const prepared = player.prepare()
  assert.equal(contexts[0].resumeCalls, 1)
  await prepared
  assert.equal(requests.length, 22)
  assert.ok(requests.every((url) => url.startsWith('/yomshishi/audio/timer/')))
  await player.prepare()
  assert.equal(requests.length, 22)
  await player.play('game-start.mp3', Infinity)
  assert.equal(contexts[0].sources[0].started, true)
  await player.dispose()
})

test('pause/reset cancels pending playback as well as an active clip', async () => {
  const player = new TimerAudioPlayer()
  await player.prepare()
  const pending = player.play('countdown-10.mp3', Infinity)
  player.stop()
  await pending
  assert.equal(contexts[0].sources.length, 0)
  await player.play('countdown-9.mp3', Infinity)
  const active = contexts[0].sources[0]
  player.stop()
  assert.equal(active.stopped, true)
  assert.equal(active.disconnected, true)
  await player.dispose()
})

test('a new cue interrupts the prior clip and expired cues are not played', async () => {
  const player = new TimerAudioPlayer()
  await player.prepare()
  await player.play('countdown-2.mp3', Infinity)
  await player.play('countdown-1.mp3', Infinity)
  assert.equal(contexts[0].sources[0].stopped, true)
  assert.equal(contexts[0].sources[1].started, true)
  await player.play('five-minutes.mp3', Date.now() - 1)
  assert.equal(contexts[0].sources.length, 2)
  await player.dispose()
  assert.equal(contexts[0].closed, true)
})

test('HTTP failures are explicit and preparation can be retried', async () => {
  const player = new TimerAudioPlayer()
  globalThis.fetch = async () => ({ ok: false, status: 404 })
  await assert.rejects(player.prepare(), /HTTP 404/)
  globalThis.fetch = async () => ({ ok: true, arrayBuffer: async () => new ArrayBuffer(1) })
  await player.prepare()
  await player.play('game-over.mp3', Infinity)
  assert.equal(contexts[0].sources[0].started, true)
  await player.dispose()
})

test('playback waits for autoplay unlock and cannot queue audio in a suspended context', async () => {
  const player = new TimerAudioPlayer()
  await player.prepare()
  let unlock
  contexts[0].resume = () => new Promise((resolve) => { unlock = resolve })
  const prepared = player.prepare()
  const pending = player.play('game-start.mp3', Infinity)
  await Promise.resolve()
  assert.equal(contexts[0].sources.length, 0)
  player.stop()
  unlock()
  await Promise.all([prepared, pending])
  assert.equal(contexts[0].sources.length, 0)
  contexts[0].resume = async () => { throw new Error('Playback blocked') }
  await assert.rejects(player.prepare(), /Playback blocked/)
  await assert.rejects(player.play('game-start.mp3', Infinity), /Playback blocked/)
  assert.equal(contexts[0].sources.length, 0)
  await player.dispose()
})

test('decode, autoplay and missing recording errors are not hidden', async () => {
  const player = new TimerAudioPlayer()
  const prepared = player.prepare()
  contexts[0].decodeAudioData = async () => { throw new Error('Invalid MP3') }
  await assert.rejects(prepared, /Invalid MP3/)
  contexts[0].decodeAudioData = MockAudioContext.prototype.decodeAudioData
  contexts[0].resume = async () => { throw new Error('Playback blocked') }
  await assert.rejects(player.prepare(), /Playback blocked/)
  contexts[0].resume = MockAudioContext.prototype.resume
  await player.prepare()
  await assert.rejects(player.play('missing.mp3', Infinity), /Missing timer recording/)
  await player.dispose()
})
