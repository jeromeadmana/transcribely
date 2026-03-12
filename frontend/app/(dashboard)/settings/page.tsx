"use client";

import { useEffect, useState } from "react";
import { User as UserIcon, Building, CreditCard, Bell } from "lucide-react";
import { User, UsageStats, getUsage } from "@/lib/api";

export default function SettingsPage() {
  const [user, setUser] = useState<User | null>(null);
  const [usage, setUsage] = useState<UsageStats | null>(null);

  useEffect(() => {
    const userData = localStorage.getItem("user");
    if (userData) {
      setUser(JSON.parse(userData));
    }

    const fetchUsage = async () => {
      const result = await getUsage();
      if (result.data) {
        setUsage(result.data);
      }
    };
    fetchUsage();
  }, []);

  if (!user) return null;

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-8">Settings</h1>

      {/* Profile Section */}
      <section className="bg-white rounded-xl border mb-6">
        <div className="px-6 py-4 border-b">
          <div className="flex items-center gap-3">
            <UserIcon className="h-5 w-5 text-gray-500" />
            <h2 className="font-semibold text-gray-900">Profile</h2>
          </div>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Name
            </label>
            <input
              type="text"
              defaultValue={user.name || ""}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Your name"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              type="email"
              value={user.email}
              disabled
              className="w-full px-3 py-2 border border-gray-200 rounded-lg bg-gray-50 text-gray-500"
            />
          </div>
          <button className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition">
            Save Changes
          </button>
        </div>
      </section>

      {/* Organization Section */}
      <section className="bg-white rounded-xl border mb-6">
        <div className="px-6 py-4 border-b">
          <div className="flex items-center gap-3">
            <Building className="h-5 w-5 text-gray-500" />
            <h2 className="font-semibold text-gray-900">Organization</h2>
          </div>
        </div>
        <div className="p-6">
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Organization Name
            </label>
            <input
              type="text"
              defaultValue={`${user.name || user.email.split("@")[0]}'s Workspace`}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <button className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition">
            Save Changes
          </button>
        </div>
      </section>

      {/* Billing Section */}
      <section className="bg-white rounded-xl border mb-6">
        <div className="px-6 py-4 border-b">
          <div className="flex items-center gap-3">
            <CreditCard className="h-5 w-5 text-gray-500" />
            <h2 className="font-semibold text-gray-900">Billing & Usage</h2>
          </div>
        </div>
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <p className="font-medium text-gray-900">Current Plan</p>
              <p className="text-sm text-gray-500 capitalize">
                {usage ? `${usage.plan} - ${usage.is_unlimited ? "Unlimited" : `${usage.limit_minutes} minutes/month`}` : "Loading..."}
              </p>
            </div>
            <span className="px-3 py-1 bg-green-100 text-green-800 text-sm font-medium rounded-full">
              Active
            </span>
          </div>

          <div className="bg-gray-50 rounded-lg p-4 mb-6">
            <div className="flex justify-between mb-2">
              <span className="text-sm text-gray-600">Usage this month</span>
              <span className="text-sm font-medium">
                {usage
                  ? usage.is_unlimited
                    ? `${usage.used_minutes.toFixed(1)} minutes used`
                    : `${usage.used_minutes.toFixed(1)} / ${usage.limit_minutes} minutes`
                  : "Loading..."}
              </span>
            </div>
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  usage && usage.percentage_used >= 100
                    ? "bg-red-500"
                    : usage && usage.percentage_used >= 80
                    ? "bg-yellow-500"
                    : "bg-primary-600"
                }`}
                style={{ width: `${usage ? Math.min(usage.percentage_used, 100) : 0}%` }}
              />
            </div>
            {usage && !usage.is_unlimited && usage.remaining_minutes !== null && (
              <p className="text-xs text-gray-500 mt-2">
                {usage.remaining_minutes.toFixed(1)} minutes remaining this month
              </p>
            )}
          </div>

          <button className="px-4 py-2 border border-primary-600 text-primary-600 rounded-lg hover:bg-primary-50 transition">
            Upgrade Plan
          </button>
        </div>
      </section>

      {/* Notifications Section */}
      <section className="bg-white rounded-xl border">
        <div className="px-6 py-4 border-b">
          <div className="flex items-center gap-3">
            <Bell className="h-5 w-5 text-gray-500" />
            <h2 className="font-semibold text-gray-900">Notifications</h2>
          </div>
        </div>
        <div className="p-6 space-y-4">
          <label className="flex items-center justify-between cursor-pointer">
            <div>
              <p className="font-medium text-gray-900">Email notifications</p>
              <p className="text-sm text-gray-500">
                Receive emails when transcription is complete
              </p>
            </div>
            <input
              type="checkbox"
              defaultChecked
              className="w-5 h-5 text-primary-600 rounded focus:ring-primary-500"
            />
          </label>
        </div>
      </section>
    </div>
  );
}
