import { useState } from "react";
import BatchProgressCard from "../components/ingestion/BatchProgressCard";
import UploadDropzone from "../components/ingestion/UploadDropzone";
import PipelineQueue from "../components/ingestion/PipelineQueue";

import type { Job } from "../components/ingestion/PipelineJobCard";

const initialQueue: Job[] = [];

export default function DocumentIngestion() {
  const [queue, setQueue] = useState<Job[]>(initialQueue);
  const [saveToDb] = useState<boolean>(true);
  const filesRef = useState(() => new Map<number, { file: File; courtType: "SC" | "HC" }>())[0];

  const doneCount = queue.filter(
    (q) => (q.status as string) === "done" || q.status === "verified" || q.status === "completed"
  ).length;

  const updateJob = (id: number, patch: Partial<Job>) => {
    setQueue((prev) =>
      prev.map((job) => (job.id === id ? { ...job, ...patch } : job))
    );
  };

  const processFileIngestion = async (file: File, jobId: number, courtType: "SC" | "HC" = "SC") => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("dry_run", saveToDb ? "false" : "true");
    formData.append("declared_court_type", courtType);

    const token = localStorage.getItem("token") || localStorage.getItem("access_token") || localStorage.getItem("sb-access-token");
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    try {
      const response = await fetch("http://localhost:8000/api/upload-judgment", {
        method: "POST",
        headers,
        body: formData,
      });

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error("Authentication required. Please sign in to upload documents.");
        }
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Upload failed with status ${response.status}`);
      }

      if (!response.body) {
        throw new Error("Extraction failed - no response stream");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      const handleEvent = (line: string) => {
        if (!line.trim()) return;
        const event = JSON.parse(line);

        if (event.type === "progress") {
          updateJob(jobId, { stageIndex: event.stage_index });
        } else if (event.type === "final") {
          const finalCourt = event.metadata?.declared_court_type || event.metadata?.court_type || courtType;
          const isPersisted = event.db_persisted;
          const statusText = isPersisted ? "SAVED TO DB" : "EXTRACTED";
          
          updateJob(jobId, {
            status: isPersisted ? "completed" : "verified",
            stageIndex: isPersisted ? 4 : 3,
            courtType: finalCourt,
            meta: `REF: ${event.metadata?.case_number || statusText} • ${finalCourt} • ${(file.size / 1024 / 1024).toFixed(1)}MB${isPersisted ? ` (${event.chunks_saved} chunks saved)` : ""}`,
          });
        } else if (event.success === false) {
          throw new Error(event.detail || "Extraction failed");
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          handleEvent(line);
        }
      }

      if (buffer.trim()) {
        handleEvent(buffer);
      }
    } catch (err: any) {
      updateJob(jobId, {
        status: "failed",
        stageIndex: 1,
        error: err.message || "Extraction process failed",
      });
    }
  };

  const handleFilesSelected = (files: File[], courtType: "SC" | "HC" = "SC") => {
    files.forEach((file, idx) => {
      const jobId = Date.now() + idx;

      filesRef.set(jobId, { file, courtType });

      const newJob: Job = {
        id: jobId,
        name: file.name,
        meta: `CASE REF: PROCESSING • ${courtType} • ${(file.size / 1024 / 1024).toFixed(1)}MB`,
        status: "processing",
        stageIndex: 0,
        courtType: courtType,
      };

      setQueue((prev) => [newJob, ...prev]);

      processFileIngestion(file, jobId, courtType);
    });
  };

  const retryJob = (id: number) => {
    const entry = filesRef.get(id);
    if (!entry) {
      updateJob(id, { error: "Original file not found — please re-upload." });
      return;
    }

    updateJob(id, { status: "processing", stageIndex: 0, error: undefined });
    processFileIngestion(entry.file, id, entry.courtType);
  };

  const ignoreJob = (id: number) => {
    filesRef.delete(id);
    setQueue((prev) => prev.filter((j) => j.id !== id));
  };

  const handleResumeBatch = () => {
    // Find all failed jobs and retry them automatically
    const failedJobs = queue.filter((j) => j.status === "failed");
    if (failedJobs.length > 0) {
      failedJobs.forEach((job) => {
        retryJob(job.id);
      });
    }
  };

  const handleClearCompleted = () => {
    setQueue((prev) => prev.filter((j) => j.status !== "verified" && (j.status as string) !== "completed"));
  };

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Document Ingestion</h1>
          <p className="text-sm text-gray-500 mt-1">
            Initiate new batch processing for legal judgments and statutes.
          </p>
        </div>

        <BatchProgressCard
          doneCount={doneCount}
          totalCount={queue.length}
          onResume={handleResumeBatch}
        />
      </div>

      {/* Grid with items-start so UploadDropzone does NOT stretch vertically */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 items-start">
        <div className="sticky top-6">
          <UploadDropzone onFilesSelected={handleFilesSelected} />
        </div>

        <PipelineQueue 
          queue={queue} 
          onRetry={retryJob} 
          onIgnore={ignoreJob} 
          onClearCompleted={handleClearCompleted}
        />
      </div>
    </div>
  );
}