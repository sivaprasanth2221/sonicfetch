import { useEffect, useRef, useState } from "react";
import sonicFetchLogo from "./assets/sonicfetch-logo-cropped.png";

const DEFAULT_FORM = {
  url: "",
  audioFormat: "mp3",
  audioQuality: "192"
};

function formatDate(value) {
  if (!value) return "Just now";
  return new Date(value).toLocaleString();
}

function formatProgress(progress) {
  if (typeof progress !== "number") return "";
  return `${Math.round(progress)}%`;
}

function basename(filePath) {
  return filePath.replace(/\\/g, "/").split("/").pop();
}


export default function App() {
  const [form, setForm] = useState(DEFAULT_FORM);
  const [jobs, setJobs] = useState([]);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const pollingRef = useRef(null);
  const noticeTimerRef = useRef(null);

  function showNotice(message) {
    setNotice(message);
    if (noticeTimerRef.current) {
      window.clearTimeout(noticeTimerRef.current);
    }
    noticeTimerRef.current = window.setTimeout(() => {
      setNotice(null);
    }, 2800);
  }

  async function loadJobs() {
    try {
      const response = await fetch("/api/downloads");
      if (!response.ok) {
        throw new Error("Unable to load recent jobs.");
      }
      const payload = await response.json();
      setJobs(Array.isArray(payload.jobs) ? payload.jobs : []);
    } catch (err) {
      console.error("Failed to load jobs", err);
      setError("Unable to reach the backend. Make sure the SonicFetch server is running.");
    }
  }

  useEffect(() => {
    loadJobs();
    pollingRef.current = window.setInterval(loadJobs, 2500);

    return () => {
      if (pollingRef.current) {
        window.clearInterval(pollingRef.current);
      }
      if (noticeTimerRef.current) {
        window.clearTimeout(noticeTimerRef.current);
      }
    };
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const response = await fetch("/api/downloads", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(form)
      });

      if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload.detail || "Failed to start the download.");
      }

      setForm(DEFAULT_FORM);
      await loadJobs();
      showNotice("Download queued successfully.");
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function deleteJob(jobId) {
    const confirmed = window.confirm(
      "Delete this job from history? If it is still running, SonicFetch will cancel it and remove any downloaded files."
    );
    if (!confirmed) {
      return;
    }
    try {
      const response = await fetch(`/api/downloads/${jobId}`, {
        method: "DELETE"
      });
      if (!response.ok) {
        throw new Error("Unable to delete the selected job.");
      }
      await loadJobs();
      showNotice("Job removed.");
    } catch (err) {
      console.error("Failed to delete job:", err);
      setError(err.message || "Failed to delete the selected job.");
    }
  }

  async function clearCompletedJobs() {
    const finishedCount = jobs.filter((job) =>
      ["completed", "failed", "cancelled"].includes(job.status)
    ).length;
    if (!finishedCount) {
      return;
    }
    const confirmed = window.confirm(
      `Clear ${finishedCount} finished job${finishedCount === 1 ? "" : "s"} from history and delete their files from disk?`
    );
    if (!confirmed) {
      return;
    }
    try {
      const response = await fetch("/api/downloads/clear", {
        method: "POST"
      });
      if (!response.ok) {
        throw new Error("Unable to clear finished jobs.");
      }
      const payload = await response.json();
      await loadJobs();
      showNotice(`Cleared ${payload.cleared ?? 0} finished job${payload.cleared === 1 ? "" : "s"}.`);
    } catch (err) {
      console.error("Failed to clear completed jobs:", err);
      setError(err.message || "Failed to clear finished jobs.");
    }
  }

  function updateField(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  const hasFinishedJobs = jobs.some((job) =>
    ["completed", "failed", "cancelled"].includes(job.status)
  );

  return (
    <div className="app-shell">
      {notice ? <div className="toast-banner">{notice}</div> : null}
      <section className="hero">
        <div className="hero-copy">
          <div className="brand-lockup">
            <img className="brand-logo" src={sonicFetchLogo} alt="SonicFetch logo" />
          </div>
          <h1>Blazing fast YouTube to MP3 converter.</h1>
          <p className="lede">
            Paste any YouTube video, shorts, live, or playlist URL. SonicFetch uses
            <code> yt-dlp </code>
            plus
            <code> ffmpeg </code>
            to fetch the source and convert it into audio files.
          </p>
          <div className="hero-points">
            <span>Single videos, playlists, shorts, and live links</span>
            <span>Cross-platform downloads with automatic cleanup</span>
            <span>Smart skip handling for unavailable playlist items</span>
          </div>
        </div>

        <form className="download-form" onSubmit={handleSubmit}>
          <label>
            YouTube URL
            <input
              name="url"
              type="url"
              placeholder="https://www.youtube.com/watch?v=..."
              value={form.url}
              onChange={updateField}
              required
              disabled={submitting}
            />
          </label>

          <div className="inline-fields">
            <label>
              Audio format
              <select name="audioFormat" value={form.audioFormat} onChange={updateField} disabled={submitting}>
                <option value="mp3">MP3</option>
                <option value="m4a">M4A</option>
                <option value="wav">WAV</option>
              </select>
            </label>

            <label>
              Quality
              <select name="audioQuality" value={form.audioQuality} onChange={updateField} disabled={submitting}>
                <option value="128">128 kbps</option>
                <option value="192">192 kbps</option>
                <option value="256">256 kbps</option>
                <option value="320">320 kbps</option>
              </select>
            </label>
          </div>

          <button type="submit" disabled={submitting}>
            {submitting ? "Fetching..." : "Fetch Audio"}
          </button>

          {error ? <p className="form-error">{error}</p> : null}
        </form>
      </section>

      <section className="jobs-panel">
        <div className="panel-heading">
          <h2>Recent jobs</h2>
          <div className="panel-actions">
            {hasFinishedJobs && (
              <button
                type="button"
                className="ghost-button clear-btn"
                onClick={clearCompletedJobs}
                title="Remove all finished jobs"
              >
                Clear all finished
              </button>
            )}
            <button type="button" className="ghost-button" onClick={() => loadJobs()}>
              Refresh
            </button>
          </div>
        </div>

        {jobs.length === 0 ? (
          <div className="empty-state">
            <p>No downloads yet. Start with a single video or an entire playlist.</p>
          </div>
        ) : (
          <div className="job-list">
            {jobs.map((job) => (
              <article className="job-card" key={job.jobId}>
                <div className="job-header">
                  <div className="job-header-left">
                    <p className={`status-pill status-${job.status}`}>{job.status}</p>
                    <h3>{job.title || job.url}</h3>
                  </div>
                  <div className="job-header-right">
                    <button
                      type="button"
                      className="delete-btn"
                      onClick={() => deleteJob(job.jobId)}
                      title="Delete job and clear disk space"
                    >
                      🗑️
                    </button>
                    <span className="job-date">{formatDate(job.updatedAt)}</span>
                  </div>
                </div>

                <p className="job-message">{job.message}</p>

                <div className="progress-track" aria-hidden="true">
                  <div
                    className="progress-bar"
                    style={{ width: formatProgress(job.progress) }}
                  />
                </div>

                <div className="job-meta">
                  <span>{formatProgress(job.progress)}</span>
                  <span>{job.isPlaylist ? "Playlist" : "Single item"}</span>
                  <span>
                    {job.itemsDownloaded}
                    {job.totalItems ? ` / ${job.totalItems}` : ""} file(s)
                  </span>
                </div>

                {job.error ? <p className="job-error">{job.error}</p> : null}
                {job.warning ? <p className="job-warning">{job.warning}</p> : null}

                {job.files?.length ? (
                  <div className="job-files">
                    {job.files.map((file, index) => (
                      <div className="job-file-row" key={file}>
                        <span className="job-file-name" title={file}>
                          {basename(file)}
                        </span>
                        <a
                          className="file-download-btn"
                          href={`/api/downloads/${job.jobId}/files/${index}`}
                          download={basename(file)}
                        >
                          ↓ Download
                        </a>
                      </div>
                    ))}
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
