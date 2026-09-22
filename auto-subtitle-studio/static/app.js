const fileInput = document.getElementById("file-input");
const dropzone = document.getElementById("dropzone");
const fileName = document.getElementById("file-name");
const wordsSelect = document.getElementById("words-per-line");
const transcribeBtn = document.getElementById("transcribe-btn");
const regroupBtn = document.getElementById("regroup-btn");
const downloadBtn = document.getElementById("download-btn");
const statusEl = document.getElementById("status");
const cueBody = document.getElementById("cue-body");
const srtPreview = document.getElementById("srt-preview");

let selectedFile = null;
let words = [];
let cues = [];

function setStatus(text) {
  statusEl.textContent = text;
}

function msToSrt(ms) {
  const safe = Math.max(0, Number(ms) || 0);
  const hours = Math.floor(safe / 3600000);
  const minutes = Math.floor((safe % 3600000) / 60000);
  const seconds = Math.floor((safe % 60000) / 1000);
  const millis = Math.floor(safe % 1000);
  const pad = (value, size) => String(value).padStart(size, "0");
  return `${pad(hours, 2)}:${pad(minutes, 2)}:${pad(seconds, 2)},${pad(millis, 3)}`;
}

function joinTexts(texts) {
  const cleaned = texts.map((item) => String(item || "").trim()).filter(Boolean);
  if (!cleaned.length) return "";
  const thai = /[\u0E00-\u0E7F]/;
  if (cleaned.every((part) => thai.test(part) && !part.includes(" "))) {
    return cleaned.join("");
  }
  return cleaned.join(" ");
}

function groupWords(source, count) {
  const size = Math.min(4, Math.max(1, Number(count) || 1));
  const next = [];
  for (let i = 0; i < source.length; i += size) {
    const chunk = source.slice(i, i + size);
    const start = chunk[0].start_ms;
    const end = Math.max(chunk[chunk.length - 1].end_ms, start + 40);
    next.push({
      start_ms: start,
      end_ms: end,
      start: msToSrt(start),
      end: msToSrt(end),
      text: joinTexts(chunk.map((item) => item.text)),
    });
  }
  return next;
}

function toSrt(list) {
  return list
    .map((cue, index) => {
      const text = String(cue.text || "").trim();
      if (!text) return "";
      return `${index + 1}\n${cue.start} --> ${cue.end}\n${text}`;
    })
    .filter(Boolean)
    .join("\n\n");
}

function render() {
  if (!cues.length) {
    cueBody.innerHTML =
      '<tr><td colspan="4" class="empty">ยังไม่มีซับ อัปโหลดไฟล์แล้วกดถอดเสียง</td></tr>';
    srtPreview.textContent = "ยังไม่มีตัวอย่าง";
    return;
  }
  cueBody.innerHTML = cues
    .map(
      (cue, index) => `
      <tr>
        <td>${index + 1}</td>
        <td><input data-index="${index}" data-field="start" value="${cue.start}" /></td>
        <td><input data-index="${index}" data-field="end" value="${cue.end}" /></td>
        <td><input data-index="${index}" data-field="text" value="${String(cue.text || "").replaceAll('"', "&quot;")}" /></td>
      </tr>`
    )
    .join("");
  srtPreview.textContent = toSrt(cues) || "ยังไม่มีตัวอย่าง";
}

dropzone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropzone.classList.add("drag");
});
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag"));
dropzone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropzone.classList.remove("drag");
  const file = event.dataTransfer.files[0];
  if (file) {
    selectedFile = file;
    fileName.textContent = file.name;
  }
});
fileInput.addEventListener("change", () => {
  selectedFile = fileInput.files[0] || null;
  fileName.textContent = selectedFile ? selectedFile.name : "ยังไม่ได้เลือกไฟล์";
});

cueBody.addEventListener("input", (event) => {
  const input = event.target;
  const index = Number(input.dataset.index);
  const field = input.dataset.field;
  if (!Number.isInteger(index) || !cues[index]) return;
  cues[index][field] = input.value;
  srtPreview.textContent = toSrt(cues);
});

transcribeBtn.addEventListener("click", async () => {
  if (!selectedFile) {
    setStatus("เลือกไฟล์เสียงก่อนนะ");
    return;
  }
  const body = new FormData();
  body.append("audio", selectedFile);
  body.append("words_per_line", wordsSelect.value);
  transcribeBtn.disabled = true;
  setStatus("กำลังถอดเสียงด้วย gemini-3.5-transcribe ...");
  try {
    const response = await fetch("/api/transcribe", { method: "POST", body });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "ถอดเสียงไม่สำเร็จ");
    }
    words = data.words || [];
    cues = data.cues || [];
    render();
    setStatus(`ถอดเสียงสำเร็จ ${cues.length} บรรทัด จากไฟล์ ${data.filename}`);
  } catch (error) {
    setStatus(error.message);
  } finally {
    transcribeBtn.disabled = false;
  }
});

regroupBtn.addEventListener("click", () => {
  if (!words.length) {
    setStatus("ยังไม่มีคำที่ถอดได้ ให้ถอดเสียงก่อน");
    return;
  }
  cues = groupWords(words, wordsSelect.value);
  render();
  setStatus(`จัดกลุ่มใหม่แล้ว เป็น ${wordsSelect.value} คำต่อบรรทัด`);
});

downloadBtn.addEventListener("click", () => {
  const srt = toSrt(cues);
  if (!srt) {
    setStatus("ยังไม่มีซับให้ดาวน์โหลด");
    return;
  }
  const blob = new Blob([srt], { type: "application/x-subrip;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "subtitles.srt";
  link.click();
  URL.revokeObjectURL(url);
});

render();

fetch("/api/health")
  .then((response) => response.json())
  .then((data) => {
    if (!data.key_configured) {
      setStatus("ยังไม่พบคีย์ในไฟล์ .env — คัดลอกจาก .env.example แล้วใส่ GEMINI_API_KEY");
    }
  })
  .catch(() => {});
