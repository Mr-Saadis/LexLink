import { useState } from "react";
import BatchProgressCard from "../components/ingestion/BatchProgressCard";
import UploadDropzone from "../components/ingestion/UploadDropzone";
import MetadataForm from "../components/ingestion/MetadataForm";
import PipelineQueue from "../components/ingestion/PipelineQueue";

import type { Job } from "../components/ingestion/PipelineJobCard";

type DocType = "judgment" | "statute";

// Helper to map UI dropdown selection to backend court_type code
const getCourtTypeCode = (courtType: string): string => {
  if (courtType.includes("Supreme Court")) return "SC";
  if (courtType.includes("High Court")) return "HC";
  return "DC";
};

const initialQueue: Job[] = [
  {
    id: 1,
    name: "SC_Judgment_2023_45.pdf",
    meta: "CASE REF: 2023-CIV-009 • 1.2MB",
    status: "verified",
    stageIndex: 3,
  },
  {
    id: 2,
    name: "LHC_Appeal_Review_22.pdf",
    meta: "CASE REF: 2022-LHC-KBB • 4.5MB",
    status: "processing",
    stageIndex: 1,
  },
  {
    id: 3,
    name: "SHC_Injunction_991.pdf",
    meta: "CASE REF: SHC-002 • 0.5MB",
    status: "failed",
    stageIndex: 1,
    error: "Cloudflare Worker Timeout - PDF resolution too high for extraction node.",
  },
];

export default function DocumentIngestion() {
  const [courtType, setCourtType] = useState<string>("High Court (HC)");
  const [docType, setDocType] = useState<DocType>("judgment");
  const [titleTemplate, setTitleTemplate] = useState<string>("");
  const [queue, setQueue] = useState<Job[]>(initialQueue);

  const doneCount = queue.filter(
    (q) => (q.status as string) === "done" || q.status === "verified" || q.status === "completed"
  ).length;

  // Single file extraction handler
  const processFileIngestion = async (file: File, jobId: number) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("court_type", getCourtTypeCode(courtType));
    formData.append("dry_run", "true"); // Change to "false" for live database saving

    try {
      const response = await fetch("http://localhost:8000/api/upload-judgment", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Extraction failed");
      }

      // Update queue item on success
      setQueue((prev) =>
        prev.map((job) =>
          job.id === jobId
            ? {
                ...job,
                status: "verified",
                stageIndex: 3,
                meta: `CASE REF: ${data.metadata?.case_number || "EXTRACTED"} • ${(file.size / 1024 / 1024).toFixed(1)}MB`,
              }
            : job
        )
      );
    } catch (err: any) {
      // Update queue item on error
      setQueue((prev) =>
        prev.map((job) =>
          job.id === jobId
            ? {
                ...job,
                status: "failed",
                stageIndex: 1,
                error: err.message || "Extraction process failed",
              }
            : job
        )
      );
    }
  };

  const handleFilesSelected = (files: File[]) => {
    files.forEach((file, idx) => {
      const jobId = Date.now() + idx;

      const newJob: Job = {
        id: jobId,
        name: file.name,
        meta: `CASE REF: PROCESSING • ${(file.size / 1024 / 1024).toFixed(1)}MB`,
        status: "processing",
        stageIndex: 1,
      };

      setQueue((prev) => [newJob, ...prev]);

      // Trigger backend API upload
      processFileIngestion(file, jobId);
    });
  };

  const retryJob = (id: number) => {
    setQueue((prev) =>
      prev.map((j) =>
        j.id === id ? { ...j, status: "processing" as const, stageIndex: 1, error: undefined } : j
      )
    );
  };

  const ignoreJob = (id: number) => {
    setQueue((prev) => prev.filter((j) => j.id !== id));
  };

  const handleResumeBatch = () => {
    console.log("Resume batch clicked");
  };

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col gap-6">
      {/* Page Header & Batch Progress */}
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

      {/* Main Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 items-start">
        <div className="flex flex-col gap-5">
          <UploadDropzone onFilesSelected={handleFilesSelected} />
          <MetadataForm
            courtType={courtType}
            onCourtTypeChange={setCourtType}
            docType={docType}
            onDocTypeChange={setDocType}
            titleTemplate={titleTemplate}
            onTitleTemplateChange={setTitleTemplate}
          />
        </div>

        <PipelineQueue queue={queue} onRetry={retryJob} onIgnore={ignoreJob} />
      </div>
    </div>
  );
}