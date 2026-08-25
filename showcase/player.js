import { showcaseData } from "./showcase-data.js";
import { durationMs, renderFrame, renderSlide, slideAtTime, timelineSlides } from "./render.js";

const errors = [];
window.__SHOWCASE_READY__ = false;
window.__SHOWCASE_DONE__ = false;
window.__SHOWCASE_ERROR__ = null;
window.__LOOP_SHOWCASE_READY__ = false;
window.__LOOP_SHOWCASE_DONE__ = false;
window.__LOOP_SHOWCASE_RECORD_ERROR__ = null;
window.__LOOP_SHOWCASE_ERRORS__ = errors;
window.__LOOP_SHOWCASE_SCENE_COUNT__ = timelineSlides.length;
window.__LOOP_SHOWCASE_DURATION_SECONDS__ = durationMs / 1000;

window.addEventListener("error", (event) => {
  const message = event.error?.stack || event.message || String(event.error || event);
  errors.push(message);
  window.__SHOWCASE_ERROR__ = message;
});

window.addEventListener("unhandledrejection", (event) => {
  const message = event.reason?.stack || String(event.reason);
  errors.push(message);
  window.__SHOWCASE_ERROR__ = message;
});

const elements = {
  body: document.body,
  canvas: document.getElementById("showcase-stage"),
  controls: document.getElementById("showcase-controls"),
  playPause: document.getElementById("play-pause"),
  previous: document.getElementById("previous-scene"),
  next: document.getElementById("next-scene"),
  restart: document.getElementById("restart"),
  scrubber: document.getElementById("timeline-scrubber"),
  timelineLabel: document.getElementById("timeline-label"),
  speed: document.getElementById("speed-select"),
  speedLabel: document.getElementById("speed-label"),
  reducedMotion: document.getElementById("reduced-motion"),
  motionLabel: document.getElementById("motion-label"),
  counter: document.getElementById("scene-counter"),
  caption: document.getElementById("showcase-caption"),
  sceneNavigation: document.getElementById("scene-navigation"),
  sceneNavigationTitle: document.getElementById("scene-navigation-title"),
  sceneList: document.getElementById("scene-list"),
  printPages: document.getElementById("print-pages")
};

const ctx = elements.canvas.getContext("2d", { alpha: false });
const query = new URLSearchParams(window.location.search);
const printMode = query.get("print") === "1";
const recordMode = query.get("record") === "1";
const requestedScene = query.get("scene");
const systemReducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches || false;

const state = {
  timeMs: 0,
  playing: false,
  speed: 1,
  reducedMotion: systemReducedMotion,
  recording: false,
  animationFrame: 0,
  previousFrameTime: 0,
  sceneIndex: 0
};

function sceneIndexFromQuery(rawValue) {
  if (rawValue === null || rawValue === undefined || rawValue === "") return null;
  const numericValue = Number(rawValue);
  if (!Number.isFinite(numericValue)) return 0;
  if (numericValue >= 1) return Math.min(timelineSlides.length - 1, Math.floor(numericValue) - 1);
  return 0;
}

function formatCounter(scene) {
  return showcaseData.ui.sceneCounterTemplate
    .replace("{current}", String(scene.index + 1))
    .replace("{total}", String(timelineSlides.length));
}

function initializeLabels() {
  const ui = showcaseData.ui;
  document.title = ui.documentTitle;
  elements.canvas.setAttribute("aria-label", ui.stageLabel);
  elements.controls.setAttribute("aria-label", ui.controlsLabel);
  elements.sceneNavigation.setAttribute("aria-label", ui.scenesLabel);
  elements.caption.setAttribute("aria-label", ui.captionLabel);
  elements.previous.textContent = ui.previous;
  elements.next.textContent = ui.next;
  elements.restart.textContent = ui.restart;
  elements.timelineLabel.textContent = ui.timeline;
  elements.speedLabel.textContent = ui.speed;
  elements.motionLabel.textContent = ui.reducedMotion;
  elements.sceneNavigationTitle.textContent = ui.scenesLabel;
  elements.scrubber.max = String(Math.round(durationMs));
  elements.scrubber.setAttribute("aria-label", ui.timeline);
  elements.speed.setAttribute("aria-label", ui.speed);
  elements.reducedMotion.setAttribute("aria-label", ui.reducedMotion);
  ui.speedOptions.forEach((speedOption) => {
    const option = document.createElement("option");
    option.value = String(speedOption.value);
    option.textContent = speedOption.label;
    if (speedOption.value === 1) option.selected = true;
    elements.speed.append(option);
  });
  elements.reducedMotion.checked = state.reducedMotion;
}

function initializeSceneList() {
  timelineSlides.forEach((slide) => {
    const listItem = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.sceneIndex = String(slide.index);
    button.dataset.sceneId = slide.id;
    button.textContent = `${String(slide.index + 1).padStart(2, "0")}: ${slide.title}`;
    button.addEventListener("click", () => goToScene(slide.index));
    listItem.append(button);
    elements.sceneList.append(listItem);
  });
}

function setCompletion(value) {
  window.__SHOWCASE_DONE__ = value;
  window.__LOOP_SHOWCASE_DONE__ = value;
}

function renderCurrent() {
  window.__showcaseReducedMotion = state.reducedMotion;
  const scene = renderFrame(state.timeMs, ctx);
  state.sceneIndex = scene.index;
  elements.body.dataset.currentScene = String(scene.index + 1);
  elements.scrubber.value = String(Math.round(state.timeMs));
  elements.caption.textContent = scene.caption;
  elements.counter.textContent = formatCounter(scene);
  elements.playPause.textContent = state.playing ? showcaseData.ui.pause : showcaseData.ui.play;
  elements.playPause.setAttribute("aria-label", state.playing ? showcaseData.ui.pause : showcaseData.ui.play);
  elements.sceneList.querySelectorAll("button[data-scene-index]").forEach((button) => {
    const active = Number(button.dataset.sceneIndex) === scene.index;
    if (active) button.setAttribute("aria-current", "true");
    else button.removeAttribute("aria-current");
  });
  return scene;
}

function pause() {
  state.playing = false;
  state.previousFrameTime = 0;
  if (state.animationFrame) cancelAnimationFrame(state.animationFrame);
  state.animationFrame = 0;
  renderCurrent();
}

function tick(frameTime) {
  if (!state.playing) return;
  if (!state.previousFrameTime) state.previousFrameTime = frameTime;
  const elapsed = Math.max(0, frameTime - state.previousFrameTime);
  state.previousFrameTime = frameTime;
  state.timeMs = Math.min(durationMs - 1, state.timeMs + elapsed * state.speed);
  renderCurrent();
  if (state.timeMs >= durationMs - 1) {
    pause();
    setCompletion(true);
    return;
  }
  state.animationFrame = requestAnimationFrame(tick);
}

function play() {
  if (state.recording) return;
  if (state.timeMs >= durationMs - 2) state.timeMs = 0;
  setCompletion(false);
  state.playing = true;
  state.previousFrameTime = 0;
  renderCurrent();
  state.animationFrame = requestAnimationFrame(tick);
}

function togglePlayback() {
  if (state.playing) pause();
  else play();
}

function seek(timeMs) {
  pause();
  state.timeMs = Math.max(0, Math.min(durationMs - 1, Number(timeMs) || 0));
  setCompletion(state.timeMs >= durationMs - 2);
  return renderCurrent();
}

function goToScene(index) {
  const safeIndex = Math.max(0, Math.min(timelineSlides.length - 1, Number(index) || 0));
  const scene = timelineSlides[safeIndex];
  return seek(scene.startMs + scene.durationMs * 0.9);
}

function setProgress(progress) {
  const bounded = Math.max(0, Math.min(1, Number(progress) || 0));
  return seek(bounded * (durationMs - 1));
}

function setReducedMotion(value) {
  state.reducedMotion = Boolean(value);
  elements.reducedMotion.checked = state.reducedMotion;
  elements.body.dataset.reducedMotion = String(state.reducedMotion);
  return renderCurrent();
}

function restart() {
  pause();
  state.timeMs = 0;
  setCompletion(false);
  return renderCurrent();
}

function changeScene(offset) {
  const current = slideAtTime(state.timeMs);
  return goToScene(current.index + offset);
}

function getState() {
  const scene = slideAtTime(state.timeMs);
  return {
    sceneIndex: scene.index,
    sceneNumber: scene.index + 1,
    sceneId: scene.id,
    playing: state.playing,
    speed: state.speed,
    reducedMotion: state.reducedMotion,
    timeMs: state.timeMs,
    progress: durationMs ? state.timeMs / durationMs : 0,
    durationMs,
    recording: state.recording
  };
}

function delay(milliseconds) {
  return new Promise((resolve) => window.setTimeout(resolve, Math.max(0, milliseconds)));
}

function chooseRecordingType() {
  const candidates = ["video/webm;codecs=vp9", "video/webm;codecs=vp8", "video/webm"];
  return candidates.find((candidate) => window.MediaRecorder?.isTypeSupported(candidate)) || "";
}

function downloadRecording(blob) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = showcaseData.ui.recordingFileName;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 2000);
}

async function recordShowcase() {
  if (state.recording) return null;
  try {
    if (!elements.canvas.captureStream || !window.MediaRecorder) {
      throw new Error(showcaseData.ui.recordingUnsupported);
    }
    pause();
    state.recording = true;
    setCompletion(false);
    elements.body.dataset.recording = "true";
    const fps = showcaseData.meta.framesPerSecond;
    const frameDuration = 1000 / fps;
    const stream = elements.canvas.captureStream(0);
    const track = stream.getVideoTracks()[0];
    const mimeType = chooseRecordingType();
    const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
    const chunks = [];
    recorder.addEventListener("dataavailable", (event) => {
      if (event.data?.size) chunks.push(event.data);
    });
    const stopped = new Promise((resolve, reject) => {
      recorder.addEventListener("stop", resolve, { once: true });
      recorder.addEventListener("error", (event) => reject(event.error || new Error(String(event))), { once: true });
    });
    recorder.start(1000);
    const totalFrames = Math.ceil(durationMs / frameDuration);
    const wallStart = performance.now();
    for (let frame = 0; frame < totalFrames; frame += 1) {
      state.timeMs = Math.min(durationMs - 1, frame * frameDuration);
      renderCurrent();
      if (typeof track.requestFrame === "function") track.requestFrame();
      const targetTime = wallStart + (frame + 1) * frameDuration;
      await delay(targetTime - performance.now());
    }
    state.timeMs = durationMs - 1;
    renderCurrent();
    if (typeof track.requestFrame === "function") track.requestFrame();
    await delay(frameDuration * 2);
    recorder.stop();
    await stopped;
    track.stop();
    const blob = new Blob(chunks, { type: recorder.mimeType || "video/webm" });
    downloadRecording(blob);
    state.recording = false;
    elements.body.dataset.recording = "false";
    setCompletion(true);
    return blob;
  } catch (error) {
    const message = error?.stack || String(error);
    errors.push(message);
    window.__SHOWCASE_ERROR__ = message;
    window.__LOOP_SHOWCASE_RECORD_ERROR__ = message;
    state.recording = false;
    elements.body.dataset.recording = "false";
    throw error;
  }
}

function buildPrintPages() {
  timelineSlides.forEach((slide) => {
    const pageCanvas = document.createElement("canvas");
    pageCanvas.width = showcaseData.meta.width;
    pageCanvas.height = showcaseData.meta.height;
    pageCanvas.className = "print-page";
    pageCanvas.dataset.printSceneIndex = String(slide.index);
    pageCanvas.dataset.printSceneId = slide.id;
    pageCanvas.setAttribute("aria-label", `${showcaseData.ui.slideLabel} ${slide.index + 1}: ${slide.title}`);
    const pageContext = pageCanvas.getContext("2d", { alpha: false });
    window.__showcaseReducedMotion = true;
    renderSlide(slide.index, pageContext, 1);
    elements.printPages.append(pageCanvas);
  });
}

function bindControls() {
  elements.playPause.addEventListener("click", togglePlayback);
  elements.previous.addEventListener("click", () => changeScene(-1));
  elements.next.addEventListener("click", () => changeScene(1));
  elements.restart.addEventListener("click", restart);
  elements.scrubber.addEventListener("input", () => seek(Number(elements.scrubber.value)));
  elements.speed.addEventListener("change", () => {
    state.speed = Number(elements.speed.value) || 1;
  });
  elements.reducedMotion.addEventListener("change", () => setReducedMotion(elements.reducedMotion.checked));
  window.addEventListener("keydown", (event) => {
    const targetName = event.target?.tagName?.toLowerCase();
    if (targetName === "input" || targetName === "select" || targetName === "button") return;
    if (event.code === "Space") {
      event.preventDefault();
      togglePlayback();
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      changeScene(-1);
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      changeScene(1);
    } else if (event.key === "Home") {
      event.preventDefault();
      restart();
    } else if (event.key === "Escape") {
      pause();
    }
  });
}

function initialize() {
  initializeLabels();
  initializeSceneList();
  bindControls();
  setReducedMotion(state.reducedMotion);
  const sceneIndex = sceneIndexFromQuery(requestedScene);
  if (printMode && sceneIndex === null) {
    buildPrintPages();
    renderSlide(0, ctx, 1);
  } else if (sceneIndex !== null) {
    const scene = timelineSlides[sceneIndex];
    state.timeMs = scene.startMs + scene.durationMs - 1;
    renderCurrent();
  } else {
    renderCurrent();
  }
  window.__SHOWCASE_READY__ = true;
  window.__LOOP_SHOWCASE_READY__ = true;
  if (recordMode) window.setTimeout(() => recordShowcase().catch(() => undefined), 60);
}

const api = {
  getState,
  goToScene,
  setProgress,
  setReducedMotion,
  seek,
  restart,
  play,
  pause,
  record: recordShowcase,
  renderFrame: (timeMs, targetContext = ctx) => renderFrame(timeMs, targetContext),
  durationMs,
  slides: timelineSlides
};

window.__showcase = api;
window.__LOOP_SHOWCASE_API__ = api;

initialize();
