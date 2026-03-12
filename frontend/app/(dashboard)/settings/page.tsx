"use client";

import { useEffect, useState } from "react";
import { User as UserIcon, Building, CreditCard, Bell } from "lucide-react";
import { User } from "@/lib/api";

export default function SettingsPage() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const userData = localStorage.getItem("user");
    if (userData) {
      setUser(JSON.parse(userData));
    }
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
              <p className="text-sm text-gray-500">Free - 30 minutes/month</p>
            </div>
            <span className="px-3 py-1 bg-green-100 text-green-800 text-sm font-medium rounded-full">
              Active
            </span>
          </div>

          <div className="bg-gray-50 rounded-lg p-4 mb-6">
            <div className="flex justify-between mb-2">
              <span className="text-sm text-gray-600">Usage this month</span>
              <span className="text-sm font-medium">0 / 30 minutes</span>
            </div>
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary-600 rounded-full"
                style={{ width: "0%" }}
              />
            </div>
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
