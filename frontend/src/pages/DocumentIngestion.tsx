import { useState } from "react";
import BatchProgressCard from "../components/ingestion/BatchProgressCard";
import UploadDropzone from "../components/ingestion/UploadDropzone";
import PipelineQueue from "../components/ingestion/PipelineQueue";

import type { Job } from "../components/ingestion/PipelineJobCard";

const initialQueue: Job[] = [];

export default function DocumentIngestion() {
  const [queue, setQueue] = useState<Job[]>(initialQueue);
  const filesRef = useState(() => new Map<number, File>())[0];

  const doneCount = queue.filter(
    (q) => (q.status as string) === "done" || q.status === "verified" || q.status === "completed"
  ).length;

  const updateJob = (id: number, patch: Partial<Job>) => {
    setQueue((prev) =>
      prev.map((job) => (job.id === id ? { ...job, ...patch } : job))
    );
  };

  const processFileIngestion = async (file: File, jobId: number) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("dry_run", "true");

    try {
      const response = await fetch("http://localhost:8000/api/upload-judgment", {
        method: "POST",
        body: formData,
      });

      if (!response.ok || !response.body) {
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
          updateJob(jobId, {
            status: "verified",
            stageIndex: 3,
            meta: `CASE REF: ${event.metadata?.case_number || "EXTRACTED"} • ${(file.size / 1024 / 1024).toFixed(1)}MB`,
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

  const handleFilesSelected = (files: File[]) => {
    files.forEach((file, idx) => {
      const jobId = Date.now() + idx;

      filesRef.set(jobId, file);

      const newJob: Job = {
        id: jobId,
        name: file.name,
        meta: `CASE REF: PROCESSING • ${(file.size / 1024 / 1024).toFixed(1)}MB`,
        status: "processing",
        stageIndex: 0,
      };

      setQueue((prev) => [newJob, ...prev]);

      processFileIngestion(file, jobId);
    });
  };

  const retryJob = (id: number) => {
    const file = filesRef.get(id);
    if (!file) {
      updateJob(id, { error: "Original file not found — please re-upload." });
      return;
    }

    updateJob(id, { status: "processing", stageIndex: 0, error: undefined });
    processFileIngestion(file, id);
  };

  const ignoreJob = (id: number) => {
    filesRef.delete(id);
    setQueue((prev) => prev.filter((j) => j.id !== id));
  };

  const handleResumeBatch = () => {
    console.log("Resume batch clicked");
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 items-stretch">
        <UploadDropzone onFilesSelected={handleFilesSelected} />

        <PipelineQueue queue={queue} onRetry={retryJob} onIgnore={ignoreJob} />
      </div>
    </div>
  );
}