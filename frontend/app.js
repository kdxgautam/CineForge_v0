const form = document.querySelector("#process-form");
const jobForm = document.querySelector("#job-form");
const sampleButton = document.querySelector("#sample-button");
const submitButton = document.querySelector("#submit-button");
const stateDot = document.querySelector("#state-dot");
const stateLabel = document.querySelector("#state-label");
const stageLabel = document.querySelector("#stage-label");
const elapsed = document.querySelector("#elapsed");
const output = document.querySelector("#output");
const clips = document.querySelector("#clips");
const summary = document.querySelector("#summary");
const stageList = document.querySelector("#stage-list");
const progressFill = document.querySelector("#progress-fill");

let timer = null;
let poller = null;
let startedAt = 0;

const STAGE_LABELS = {
  queued: "Queued",
  download_youtube_video: "Downloading video",
  extract_audio: "Extracting audio",
  transcribe_full_video: "Transcribing source",
  generate_highlights: "Finding highlights",
  generate_clips: "Cutting clips",
  run_asd_on_clips: "Running active speaker detection",
  process_all_clips: "Cropping vertical clips",
  generate_srts_from_transcript: "Generating subtitles",
  burn_subtitles_on_all_clips: "Burning subtitles",
  complete: "Complete",
  failed: "Failed",
};

function setState(label, mode = "idle") {
  stateLabel.textContent = label;
  stateDot.className = `dot ${mode}`;
}

function formatStage(stage) {
  return STAGE_LABELS[stage] || stage || "Waiting";
}

function startTimer() {
  startedAt = Date.now();
  elapsed.textContent = "00:00";
  clearInterval(timer);
  timer = setInterval(() => {
    const seconds = Math.floor((Date.now() - startedAt) / 1000);
    const mins = String(Math.floor(seconds / 60)).padStart(2, "0");
    const secs = String(seconds % 60).padStart(2, "0");
    elapsed.textContent = `${mins}:${secs}`;
  }, 1000);
}

function stopTimer() {
  clearInterval(timer);
  timer = null;
}

function stopPolling() {
  clearInterval(poller);
  poller = null;
}

function showJson(data) {
  output.textContent = JSON.stringify(data, null, 2);
}

function addSummary(data) {
  summary.innerHTML = "";
  const rows = [
    ["Job", data.job_id || "-"],
    ["Status", data.status || data.stage || "-"],
    ["Final clips", Array.isArray(data.final_clips) ? data.final_clips.length : 0],
  ];

  for (const [label, value] of rows) {
    const row = document.createElement("div");
    row.className = "summary-row";
    row.innerHTML = `<span class="muted">${label}</span><strong>${value}</strong>`;
    summary.appendChild(row);
  }
}

function renderStages(data) {
  const stages = data.stages || [];
  const active = data.stage || "queued";
  const activeIndex = stages.indexOf(active);
  const progress = Number.isFinite(data.progress) ? data.progress : 0;
  const finalClipCount = Number(data.final_clip_count);
  const totalFinalClips = Number(data.total_final_clips);

  let activeLabel = formatStage(active);
  if (
    active === "burn_subtitles_on_all_clips"
    && Number.isFinite(finalClipCount)
    && Number.isFinite(totalFinalClips)
    && totalFinalClips > 0
  ) {
    activeLabel = `${activeLabel} (${finalClipCount}/${totalFinalClips})`;
  }

  stageLabel.textContent = activeLabel;
  progressFill.style.width = `${Math.max(0, Math.min(1, progress)) * 100}%`;
  stageList.innerHTML = "";

  for (const [index, stage] of stages.entries()) {
    const item = document.createElement("li");
    if (stage === "failed") continue;
    item.className = "stage-item";
    if (index < activeIndex || active === "complete") item.classList.add("done");
    if (index === activeIndex && active !== "complete") item.classList.add("active");
    item.innerHTML = `<span>${index + 1}</span><strong>${formatStage(stage)}</strong>`;
    stageList.appendChild(item);
  }
}

function mediaUrlForPath(path) {
  const value = String(path);
  const jobsPrefix = "jobs/";
  const absoluteJobsMarker = "/jobs/";

  if (value.startsWith(jobsPrefix)) {
    return `/media/${value.slice(jobsPrefix.length)}`;
  }

  const markerIndex = value.indexOf(absoluteJobsMarker);
  if (markerIndex !== -1) {
    return `/media/${value.slice(markerIndex + absoluteJobsMarker.length)}`;
  }

  return value;
}

function addClipLinks(paths = []) {
  clips.innerHTML = "";
  for (const path of paths) {
    const link = document.createElement("a");
    link.className = "clip-link";
    link.textContent = path;
    link.href = mediaUrlForPath(path);
    link.target = "_blank";
    link.rel = "noreferrer";
    clips.appendChild(link);
  }
}

function payloadFromForm() {
  const formData = new FormData(form);
  return {
    url: formData.get("url"),
    quality: formData.get("quality"),
    model_size: formData.get("model_size"),
    device: formData.get("device"),
    batch_size: Number(formData.get("batch_size")),
    compute_type: formData.get("compute_type"),
    max_segments: Number(formData.get("max_segments")),
    words_per_subtitle: Number(formData.get("words_per_subtitle")),
    subtitle_font_size: Number(formData.get("subtitle_font_size")),
    subtitle_margin_v: Number(formData.get("subtitle_margin_v")),
  };
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw data;
  }
  return data;
}

async function loadJob(jobId) {
  const response = await fetch(`/jobs/${encodeURIComponent(jobId)}`);
  const data = await response.json();
  if (!response.ok) throw data;
  return data;
}

function consumeJobStatus(data) {
  renderStages(data);
  addSummary(data.result || data);
  addClipLinks((data.result && data.result.final_clips) || data.final_clips || []);
  showJson(data);

  if (data.status === "complete" || data.stage === "complete") {
    setState("Complete", "ok");
    stopTimer();
    stopPolling();
    submitButton.disabled = false;
    return true;
  }

  if (data.status === "failed" || data.stage === "failed") {
    setState("Failed", "error");
    stopTimer();
    stopPolling();
    submitButton.disabled = false;
    return true;
  }

  setState(data.status === "queued" ? "Queued" : "Running", "running");
  return false;
}

function startPolling(jobId) {
  stopPolling();
  poller = setInterval(async () => {
    try {
      consumeJobStatus(await loadJob(jobId));
    } catch (error) {
      showJson(error);
      setState("Status check failed", "error");
    }
  }, 2500);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  submitButton.disabled = true;
  clips.innerHTML = "";
  summary.innerHTML = "";
  stageList.innerHTML = "";
  progressFill.style.width = "0%";
  showJson({status: "submitting"});
  setState("Submitting", "running");
  stageLabel.textContent = "Creating job";
  startTimer();

  try {
    const data = await postJson("/process-video-async", payloadFromForm());
    document.querySelector("#job-id").value = data.job_id;
    consumeJobStatus(data);
    startPolling(data.job_id);
  } catch (error) {
    showJson(error);
    setState("Failed", "error");
    submitButton.disabled = false;
    stopTimer();
  }
});

sampleButton.addEventListener("click", () => {
  document.querySelector("#url").value = "https://www.youtube.com/watch?v=ef3D5Ak1HP4&t=4s";
  document.querySelector("#quality").value = "1080";
  document.querySelector("#model_size").value = "small";
  document.querySelector("#device").value = "cpu";
  document.querySelector("#compute_type").value = "int8";
  document.querySelector("#batch_size").value = "2";
  document.querySelector("#max_segments").value = "80";
  document.querySelector("#words_per_subtitle").value = "3";
  document.querySelector("#subtitle_font_size").value = "11";
  document.querySelector("#subtitle_margin_v").value = "35";
});

jobForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const jobId = document.querySelector("#job-id").value.trim();
  if (!jobId) return;
  setState("Checking", "running");

  try {
    const data = await loadJob(jobId);
    consumeJobStatus(data);
    if (data.status !== "complete" && data.status !== "failed") {
      startPolling(jobId);
      startTimer();
    }
  } catch (error) {
    showJson(error);
    setState("Failed", "error");
  }
});
