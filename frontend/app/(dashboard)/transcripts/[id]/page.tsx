"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Download,
  Copy,
  Check,
  Clock,
  FileText,
  Loader2,
  AlertCircle,
  Languages,
  X,
} from "lucide-react";
import {
  Video,
  Transcript,
  TranscriptSegment,
  SupportedLanguage,
  getVideo,
  exportTranscript,
  getSupportedLanguages,
  translateTranscript,
} from "@/lib/api";
import { formatDuration, getVideoStatusColor, getVideoStatusText } from "@/lib/utils";

export default function TranscriptPage() {
  const params = useParams();
  const router = useRouter();
  const videoId = params.id as string;

  const [video, setVideo] = useState<(Video & { transcript?: Transcript }) | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  // Translation state
  const [showTranslateModal, setShowTranslateModal] = useState(false);
  const [languages, setLanguages] = useState<SupportedLanguage[]>([]);
  const [selectedLang, setSelectedLang] = useState<string>("");
  const [translating, setTranslating] = useState(false);
  const [translatedSegments, setTranslatedSegments] = useState<TranscriptSegment[] | null>(null);
  const [translatedLang, setTranslatedLang] = useState<string | null>(null);

  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchVideo = useCallback(async () => {
    const result = await getVideo(videoId);
    if (result.error) {
      setError(result.error);
    } else if (result.data) {
      setVideo(result.data);
    }
    setLoading(false);
  }, [videoId]);

  const fetchLanguages = useCallback(async () => {
    const result = await getSupportedLanguages();
    if (result.data) {
      setLanguages(result.data);
    }
  }, []);

  // Initial fetch on mount
  useEffect(() => {
    fetchVideo();
    fetchLanguages();
  }, [fetchVideo, fetchLanguages]);

  // Separate effect for polling - only when still processing
  useEffect(() => {
    const isProcessing = video && !["completed", "failed"].includes(video.status);

    // Clear any existing interval
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    // Only poll if still processing
    if (isProcessing) {
      intervalRef.current = setInterval(() => {
        fetchVideo();
      }, 3000);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [video?.status, fetchVideo]);

  const handleTranslate = async () => {
    if (!selectedLang) return;
    setTranslating(true);

    const result = await translateTranscript(videoId, selectedLang);
    if (result.data) {
      setTranslatedSegments(result.data.segments);
      setTranslatedLang(result.data.target_language_name);
      setShowTranslateModal(false);
    } else if (result.error) {
      alert(`Translation failed: ${result.error}`);
    }
    setTranslating(false);
  };

  const clearTranslation = () => {
    setTranslatedSegments(null);
    setTranslatedLang(null);
  };

  const handleCopy = async () => {
    if (!video?.transcript?.full_text) return;
    await navigator.clipboard.writeText(video.transcript.full_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExport = async (format: "txt" | "json" | "srt" | "vtt") => {
    const response = await exportTranscript(videoId, format);
    if (response.ok) {
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${video?.title || "transcript"}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    );
  }

  if (error || !video) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-red-50 text-red-700 p-6 rounded-lg flex items-center gap-3">
          <AlertCircle className="h-6 w-6" />
          <div>
            <p className="font-medium">Error loading video</p>
            <p className="text-sm">{error || "Video not found"}</p>
          </div>
        </div>
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 mt-4 text-primary-600 hover:text-primary-700"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Dashboard
        </Link>
      </div>
    );
  }

  const isProcessing = !["completed", "failed"].includes(video.status);

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Dashboard
        </Link>

        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {video.title || video.original_filename || "Untitled"}
            </h1>
            <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
              {video.duration_seconds && (
                <span className="flex items-center gap-1">
                  <Clock className="h-4 w-4" />
                  {formatDuration(video.duration_seconds)}
                </span>
              )}
              <span
                className={`px-2 py-0.5 rounded-full text-xs font-medium ${getVideoStatusColor(
                  video.status
                )}`}
              >
                {getVideoStatusText(video.status)}
              </span>
            </div>
          </div>

          {video.transcript && (
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowTranslateModal(true)}
                className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition"
              >
                <Languages className="h-4 w-4" />
                Translate
              </button>
              <button
                onClick={handleCopy}
                className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition"
              >
                {copied ? (
                  <Check className="h-4 w-4 text-green-600" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
                {copied ? "Copied!" : "Copy"}
              </button>
              <div className="relative group">
                <button className="flex items-center gap-2 px-3 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition">
                  <Download className="h-4 w-4" />
                  Export
                </button>
                <div className="absolute right-0 mt-2 w-40 bg-white rounded-lg shadow-lg border opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
                  {(["txt", "srt", "vtt", "json"] as const).map((format) => (
                    <button
                      key={format}
                      onClick={() => handleExport(format)}
                      className="block w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 first:rounded-t-lg last:rounded-b-lg"
                    >
                      {format.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Processing state */}
      {isProcessing && (
        <div className="bg-white rounded-xl border p-8 text-center">
          <Loader2 className="h-12 w-12 text-primary-600 animate-spin mx-auto mb-4" />
          <p className="text-lg font-medium text-gray-900 mb-2">
            {getVideoStatusText(video.status)}
          </p>
          <p className="text-gray-500 mb-4">
            {video.status === "extracting_audio"
              ? "Extracting audio from your video..."
              : video.status === "transcribing"
              ? "Transcribing with AI... This may take a few minutes."
              : "Preparing your video..."}
          </p>
          <div className="max-w-xs mx-auto">
            <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary-600 transition-all duration-500"
                style={{ width: `${video.progress}%` }}
              />
            </div>
            <p className="text-sm text-gray-500 mt-2">{video.progress}%</p>
          </div>
        </div>
      )}

      {/* Failed state */}
      {video.status === "failed" && (
        <div className="bg-red-50 rounded-xl border border-red-200 p-6">
          <div className="flex items-center gap-3 text-red-700">
            <AlertCircle className="h-6 w-6" />
            <div>
              <p className="font-medium">Transcription Failed</p>
              <p className="text-sm">{video.error_message || "An error occurred during processing"}</p>
            </div>
          </div>
        </div>
      )}

      {/* Completed state - Transcript View */}
      {video.status === "completed" && video.transcript && (
        <div className="bg-white rounded-xl border">
          {/* Stats bar */}
          <div className="px-6 py-4 border-b flex items-center justify-between">
            <div className="flex items-center gap-6 text-sm text-gray-500">
              <span className="flex items-center gap-1">
                <FileText className="h-4 w-4" />
                {video.transcript.word_count?.toLocaleString() || 0} words
              </span>
              {video.transcript.language && (
                <span>Language: {video.transcript.language.toUpperCase()}</span>
              )}
              {video.transcript.segments && (
                <span>{video.transcript.segments.length} segments</span>
              )}
            </div>
            {translatedLang && (
              <div className="flex items-center gap-2">
                <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                  Translated to {translatedLang}
                </span>
                <button
                  onClick={clearTranslation}
                  className="text-gray-400 hover:text-gray-600"
                  title="Clear translation"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            )}
          </div>

          {/* Segments view */}
          {video.transcript.segments && video.transcript.segments.length > 0 ? (
            <div className="divide-y max-h-[600px] overflow-y-auto">
              {(translatedSegments || video.transcript.segments).map((segment, index) => (
                <div
                  key={index}
                  className="px-6 py-4 hover:bg-gray-50 transition"
                >
                  <div className="flex items-start gap-4">
                    <span className="text-xs text-primary-600 font-mono whitespace-nowrap pt-1">
                      {formatDuration(segment.start)}
                    </span>
                    <p className="text-gray-800 leading-relaxed">{segment.text}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-6">
              <p className="text-gray-800 leading-relaxed whitespace-pre-wrap">
                {video.transcript.full_text || "No transcript content available."}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Translation Modal */}
      {showTranslateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Translate Transcript</h3>
              <button
                onClick={() => setShowTranslateModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <p className="text-sm text-gray-600 mb-4">
              Select a language to translate the transcript. The original transcript will be preserved.
            </p>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Target Language
              </label>
              <select
                value={selectedLang}
                onChange={(e) => setSelectedLang(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="">Select a language...</option>
                {languages
                  .filter((lang) => lang.code !== video?.transcript?.language)
                  .map((lang) => (
                    <option key={lang.code} value={lang.code}>
                      {lang.name}
                    </option>
                  ))}
              </select>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setShowTranslateModal(false)}
                className="flex-1 px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleTranslate}
                disabled={!selectedLang || translating}
                className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {translating ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Translating...
                  </>
                ) : (
                  <>
                    <Languages className="h-4 w-4" />
                    Translate
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
