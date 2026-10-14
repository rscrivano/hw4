/*
 * Interactive effects (Problem 10): Handsome Dan's bark, a growl, and the "fly to cart" bubble.
 *
 * Sounds are synthesized with the Web Audio API (no audio files to license or download).
 * They only ever play right after a click, respect the 🔊/🔇 toggle in the nav bar, and the
 * animation is skipped for shoppers who ask their device for reduced motion.
 */

const SOUND_KEY = 'cc_sound'
let ctx: AudioContext | null = null

export function soundOn(): boolean {
  try {
    return localStorage.getItem(SOUND_KEY) !== 'off'
  } catch {
    return true
  }
}

export function setSoundOn(on: boolean) {
  try {
    localStorage.setItem(SOUND_KEY, on ? 'on' : 'off')
  } catch {
    /* storage blocked: setting lasts for this page view */
  }
}

function audio(): AudioContext | null {
  if (!soundOn()) return null
  try {
    ctx ??= new AudioContext()
    if (ctx.state === 'suspended') void ctx.resume()
    return ctx
  } catch {
    return null // very old browser: stay silent
  }
}

function noiseBuffer(ac: BaseAudioContext, seconds: number): AudioBuffer {
  const buf = ac.createBuffer(1, Math.ceil(ac.sampleRate * seconds), ac.sampleRate)
  const data = buf.getChannelData(0)
  for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1
  return buf
}

/** One short "woof": a falling, nasal tone plus a breathy burst, shaped by a fast envelope. */
function woof(ac: BaseAudioContext, out: AudioNode, t: number, pitch = 1) {
  const osc = ac.createOscillator()
  osc.type = 'sawtooth'
  osc.frequency.setValueAtTime(560 * pitch, t)
  osc.frequency.setValueAtTime(560 * pitch, t + 0.04)
  osc.frequency.exponentialRampToValueAtTime(190 * pitch, t + 0.24)

  const formant = ac.createBiquadFilter()
  formant.type = 'bandpass'
  formant.frequency.setValueAtTime(950, t)
  formant.Q.value = 1.4

  const body = ac.createGain()
  body.gain.setValueAtTime(0.0001, t)
  body.gain.exponentialRampToValueAtTime(0.9, t + 0.012)
  body.gain.setValueAtTime(0.9, t + 0.07)
  body.gain.exponentialRampToValueAtTime(0.0001, t + 0.28)
  osc.connect(formant).connect(body).connect(out)

  const breath = ac.createBufferSource()
  breath.buffer = noiseBuffer(ac, 0.12)
  const hiss = ac.createBiquadFilter()
  hiss.type = 'bandpass'
  hiss.frequency.value = 1600
  const air = ac.createGain()
  air.gain.setValueAtTime(0.35, t)
  air.gain.exponentialRampToValueAtTime(0.0001, t + 0.09)
  breath.connect(hiss).connect(air).connect(out)

  osc.start(t)
  osc.stop(t + 0.3)
  breath.start(t)
}

/** "Woof-woof!" Two quick barks, the second a little higher. Exposed for offline testing. */
export function scheduleBark(ac: BaseAudioContext, out: AudioNode, t0: number) {
  woof(ac, out, t0, 1)
  woof(ac, out, t0 + 0.32, 1.12)
}

/** A low, rumbling ~1 second growl: a wobbling sawtooth under a lowpass, plus throaty noise. */
export function scheduleGrowl(ac: BaseAudioContext, out: AudioNode, t0: number) {
  const dur = 1.0
  const osc = ac.createOscillator()
  osc.type = 'sawtooth'
  osc.frequency.setValueAtTime(95, t0)
  osc.frequency.linearRampToValueAtTime(80, t0 + dur)
  const wobble = ac.createOscillator() // vibrato: the "rrrr" in the growl
  wobble.frequency.value = 22
  const wobbleDepth = ac.createGain()
  wobbleDepth.gain.value = 14
  wobble.connect(wobbleDepth).connect(osc.frequency)

  const tone = ac.createBiquadFilter()
  tone.type = 'lowpass'
  tone.frequency.value = 650

  const rumble = ac.createGain() // tremolo for a rough, uneven texture
  rumble.gain.value = 0.55
  const trem = ac.createOscillator()
  trem.frequency.value = 17
  const tremDepth = ac.createGain()
  tremDepth.gain.value = 0.35
  trem.connect(tremDepth).connect(rumble.gain)

  const env = ac.createGain()
  env.gain.setValueAtTime(0.0001, t0)
  env.gain.exponentialRampToValueAtTime(0.8, t0 + 0.15)
  env.gain.setValueAtTime(0.8, t0 + dur - 0.3)
  env.gain.exponentialRampToValueAtTime(0.0001, t0 + dur)
  osc.connect(tone).connect(rumble).connect(env).connect(out)

  const throat = ac.createBufferSource()
  throat.buffer = noiseBuffer(ac, dur)
  const throatTone = ac.createBiquadFilter()
  throatTone.type = 'lowpass'
  throatTone.frequency.value = 380
  const throatGain = ac.createGain()
  throatGain.gain.value = 0.25
  throat.connect(throatTone).connect(throatGain).connect(env)

  for (const node of [osc, wobble, trem]) {
    node.start(t0)
    node.stop(t0 + dur + 0.05)
  }
  throat.start(t0)
}

function play(schedule: (ac: BaseAudioContext, out: AudioNode, t0: number) => void, volume: number) {
  const ac = audio()
  if (!ac) return
  const master = ac.createGain()
  master.gain.value = volume
  master.connect(ac.destination)
  schedule(ac, master, ac.currentTime + 0.01)
}

export const bark = () => play(scheduleBark, 0.35)
export const growl = () => play(scheduleGrowl, 0.45)

const reducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

/** The visible cart icon (desktop nav link, or the phone cart button). */
function cartTarget(): HTMLElement | null {
  const candidates = document.querySelectorAll<HTMLElement>('.cart-mobile, .cart-link')
  for (const el of candidates) if (el.offsetParent !== null) return el
  return null
}

/** Make the cart icon do a little hop so the shopper sees where the item went. */
export function bumpCart() {
  const el = cartTarget()
  if (!el || reducedMotion()) return
  el.animate(
    [{ transform: 'scale(1)' }, { transform: 'scale(1.3) rotate(-8deg)' }, { transform: 'scale(1)' }],
    { duration: 380, easing: 'ease-out' },
  )
}

/**
 * The "fly to cart" bubble: a round bubble holding the product photo starts at `from`
 * (the product image or the Add to cart button), arcs up and over, shrinks into the cart icon,
 * then the cart icon hops.
 */
export function flyToCart(imageUrl: string, from: Element | null) {
  const target = cartTarget()
  if (!from || !target || reducedMotion()) return bumpCart()

  const a = from.getBoundingClientRect()
  const b = target.getBoundingClientRect()
  const size = 84
  const bubble = document.createElement('div')
  bubble.className = 'fly-bubble'
  bubble.setAttribute('aria-hidden', 'true')
  bubble.style.backgroundImage = `url("${imageUrl}")`
  bubble.style.width = bubble.style.height = `${size}px`
  bubble.style.left = `${a.left + a.width / 2 - size / 2}px`
  bubble.style.top = `${a.top + a.height / 2 - size / 2}px`
  document.body.appendChild(bubble)

  const dx = b.left + b.width / 2 - (a.left + a.width / 2)
  const dy = b.top + b.height / 2 - (a.top + a.height / 2)
  const anim = bubble.animate(
    [
      { transform: 'translate(0, 0) scale(0.4)', opacity: 0 },
      { transform: 'translate(0, -24px) scale(1.1)', opacity: 1, offset: 0.15 },
      { transform: `translate(${dx * 0.5}px, ${dy * 0.5 - 90}px) scale(0.85)`, opacity: 1, offset: 0.55 },
      { transform: `translate(${dx}px, ${dy}px) scale(0.18)`, opacity: 0.6 },
    ],
    { duration: 850, easing: 'cubic-bezier(.45,.05,.35,1)' },
  )
  anim.onfinish = () => {
    bubble.remove()
    bumpCart()
  }
}
