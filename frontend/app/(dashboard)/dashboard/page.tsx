"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Plus, Video, Trash2, Clock, FileText, AlertCircle } from "lucide-react";
import { Video as VideoType, listVideos, deleteVideo } from "@/lib/api";
import {
  formatRelativeTime,
  formatDuration,
  formatFileSize,
  getVideoStatusColor,
  getVideoStatusText,
} from "@/lib/utils";

export default function DashboardPage() {
  const [videos, setVideos] = useState<VideoType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchVideos = async () => {
    const result = await listVideos();
    if (result.error) {
      setError(result.error);
    } else if (result.data) {
      setVideos(result.data);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchVideos();
    // Poll for updates every 5 seconds if there are processing videos
    const interval = setInterval(() => {
      if (videos.some((v) => !["completed", "failed"].includes(v.status))) {
        fetchVideos();
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [videos]);

  const handleDelete = async (videoId: string) => {
    if (!confirm("Are you sure you want to delete this video?")) return;

    const result = await deleteVideo(videoId);
    if (result.error) {
      alert(result.error);
    } else {
      setVideos(videos.filter((v) => v.id !== videoId));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">My Videos</h1>
          <p className="text-gray-600">
            {videos.length} video{videos.length !== 1 ? "s" : ""}
          </p>
        </div>
        <Link
          href="/upload"
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition"
        >
          <Plus className="h-5 w-5" />
          Upload Video
        </Link>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-lg mb-6 flex items-center gap-2">
          <AlertCircle className="h-5 w-5" />
          {error}
        </div>
      )}

      {videos.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border">
          <Video className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            No videos yet
          </h2>
          <p className="text-gray-600 mb-6">
            Upload your first video to get started with transcription.
          </p>
          <Link
            href="/upload"
            className="inline-flex items-center gap-2 px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition"
          >
            <Plus className="h-5 w-5" />
            Upload Video
          </Link>
        </div>
      ) : (
        <div className="grid gap-4">
          {videos.map((video) => (
            <div
              key={video.id}
              className="bg-white rounded-xl border p-4 hover:shadow-md transition"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <Link
                    href={`/transcripts/${video.id}`}
                    className="text-lg font-medium text-gray-900 hover:text-primary-600 truncate block"
                  >
                    {video.title || video.original_filename || "Untitled"}
                  </Link>
                  <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-gray-500">
                    <span className="flex items-center gap-1">
                      <Clock className="h-4 w-4" />
                      {video.duration_seconds
                        ? formatDuration(video.duration_seconds)
                        : "Processing..."}
                    </span>
                    {video.file_size_bytes && (
                      <span>{formatFileSize(video.file_size_bytes)}</span>
                    )}
                    <span>{formatRelativeTime(video.created_at)}</span>
                  </div>
                </div>

                <div className="flex items-center gap-3 ml-4">
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-medium ${getVideoStatusColor(
                      video.status
                    )}`}
                  >
                    {getVideoStatusText(video.status)}
                    {video.status === "transcribing" && ` ${video.progress}%`}
                  </span>

                  {video.status === "completed" && (
                    <Link
                      href={`/transcripts/${video.id}`}
                      className="p-2 text-gray-500 hover:text-primary-600 hover:bg-gray-100 rounded-lg transition"
                      title="View Transcript"
                    >
                      <FileText className="h-5 w-5" />
                    </Link>
                  )}

                  <button
                    onClick={() => handleDelete(video.id)}
                    className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition"
                    title="Delete"
                  >
                    <Trash2 className="h-5 w-5" />
                  </button>
                </div>
              </div>

              {/* Progress bar for processing videos */}
              {!["completed", "failed", "pending"].includes(video.status) && (
                <div className="mt-3">
                  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary-600 transition-all duration-500"
                      style={{ width: `${video.progress}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Error message */}
              {video.status === "failed" && video.error_message && (
                <div className="mt-3 text-sm text-red-600 flex items-center gap-2">
                  <AlertCircle className="h-4 w-4" />
                  {video.error_message}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
