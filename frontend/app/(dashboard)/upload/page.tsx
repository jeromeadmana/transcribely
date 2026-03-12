"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Upload, X, FileVideo, Loader2, CheckCircle } from "lucide-react";
import { uploadVideo } from "@/lib/api";
import { formatFileSize } from "@/lib/utils";

const ACCEPTED_TYPES = [
  "video/mp4",
  "video/quicktime",
  "video/x-msvideo",
  "video/x-matroska",
  "video/webm",
];

const MAX_SIZE = 500 * 1024 * 1024; // 500MB for direct upload

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState<"select" | "uploading" | "processing" | "done">("select");
  const [error, setError] = useState("");

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      validateAndSetFile(droppedFile);
    }
  }, []);

  const validateAndSetFile = (file: File) => {
    setError("");

    if (!ACCEPTED_TYPES.includes(file.type)) {
      setError("Please upload a valid video file (MP4, MOV, AVI, MKV, WebM)");
      return;
    }

    if (file.size > MAX_SIZE) {
      setError("File size must be less than 500MB");
      return;
    }

    setFile(file);
    setTitle(file.name.replace(/\.[^/.]+$/, ""));
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      validateAndSetFile(selectedFile);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError("");
    setStage("uploading");
    setProgress(0);

    try {
      // Upload file directly to server
      const result = await uploadVideo(file, title || undefined, (p) => {
        setProgress(p);
      });

      if (result.error || !result.data) {
        throw new Error(result.error || "Upload failed");
      }

      setStage("processing");

      // Brief delay to show processing state
      setTimeout(() => {
        setStage("done");

        // Redirect to dashboard
        setTimeout(() => {
          router.push("/dashboard");
        }, 1000);
      }, 500);

    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setStage("select");
    } finally {
      setUploading(false);
    }
  };

  const clearFile = () => {
    setFile(null);
    setTitle("");
    setError("");
    setStage("select");
    setProgress(0);
  };

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Upload Video</h1>
      <p className="text-gray-600 mb-8">
        Upload a video to transcribe. Supported formats: MP4, MOV, AVI, MKV, WebM (max 500MB).
      </p>

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-lg mb-6">
          {error}
        </div>
      )}

      {stage === "select" && !file && (
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-xl p-12 text-center transition ${
            dragActive
              ? "border-primary-500 bg-primary-50"
              : "border-gray-300 hover:border-gray-400"
          }`}
        >
          <Upload className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-lg font-medium text-gray-900 mb-2">
            Drag and drop your video here
          </p>
          <p className="text-gray-500 mb-4">or</p>
          <label className="inline-flex items-center gap-2 px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition cursor-pointer">
            <Upload className="h-5 w-5" />
            Choose File
            <input
              type="file"
              className="hidden"
              accept={ACCEPTED_TYPES.join(",")}
              onChange={handleFileSelect}
            />
          </label>
        </div>
      )}

      {file && stage === "select" && (
        <div className="bg-white rounded-xl border p-6">
          <div className="flex items-start gap-4 mb-6">
            <div className="p-3 bg-primary-100 rounded-lg">
              <FileVideo className="h-8 w-8 text-primary-600" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-gray-900 truncate">{file.name}</p>
              <p className="text-sm text-gray-500">{formatFileSize(file.size)}</p>
            </div>
            <button
              onClick={clearFile}
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Title (optional)
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Enter a title for your video"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
          </div>

          <button
            onClick={handleUpload}
            disabled={uploading}
            className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Upload className="h-5 w-5" />
            Upload and Transcribe
          </button>
        </div>
      )}

      {(stage === "uploading" || stage === "processing") && (
        <div className="bg-white rounded-xl border p-6">
          <div className="flex items-center gap-4 mb-6">
            <div className="p-3 bg-primary-100 rounded-lg">
              <Loader2 className="h-8 w-8 text-primary-600 animate-spin" />
            </div>
            <div>
              <p className="font-medium text-gray-900">
                {stage === "uploading" ? "Uploading video..." : "Starting transcription..."}
              </p>
              <p className="text-sm text-gray-500">
                {stage === "uploading"
                  ? `${progress}% complete`
                  : "Processing will continue in the background"}
              </p>
            </div>
          </div>

          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-primary-600 transition-all duration-300"
              style={{ width: stage === "uploading" ? `${progress}%` : "100%" }}
            />
          </div>
        </div>
      )}

      {stage === "done" && (
        <div className="bg-white rounded-xl border p-6 text-center">
          <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
          <p className="text-lg font-medium text-gray-900 mb-2">
            Upload Complete!
          </p>
          <p className="text-gray-500">
            Redirecting to dashboard...
          </p>
        </div>
      )}
    </div>
  );
}
