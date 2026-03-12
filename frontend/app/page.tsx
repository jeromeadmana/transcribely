import Link from "next/link";
import { Upload, Zap, FileText, Users } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-gray-50">
      {/* Navigation */}
      <nav className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="flex items-center gap-2">
              <FileText className="h-8 w-8 text-primary-600" />
              <span className="text-xl font-bold">Transcribely</span>
            </div>
            <div className="flex items-center gap-4">
              <Link
                href="/login"
                className="text-gray-600 hover:text-gray-900 px-4 py-2"
              >
                Login
              </Link>
              <Link
                href="/register"
                className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 transition"
              >
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="py-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            Turn Videos into Text with{" "}
            <span className="text-primary-600">AI-Powered</span> Transcription
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Upload your videos and get accurate, searchable transcripts in
            minutes. Perfect for meetings, interviews, podcasts, and more.
          </p>
          <div className="flex justify-center gap-4">
            <Link
              href="/register"
              className="bg-primary-600 text-white px-8 py-3 rounded-lg text-lg font-medium hover:bg-primary-700 transition"
            >
              Start Free Trial
            </Link>
            <Link
              href="#features"
              className="border border-gray-300 text-gray-700 px-8 py-3 rounded-lg text-lg font-medium hover:bg-gray-50 transition"
            >
              Learn More
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 px-4 bg-white">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-12">
            Everything You Need for Video Transcription
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            <FeatureCard
              icon={<Upload className="h-8 w-8" />}
              title="Easy Upload"
              description="Drag and drop your videos or paste a link. We support MP4, MOV, AVI, and more formats up to 2GB."
            />
            <FeatureCard
              icon={<Zap className="h-8 w-8" />}
              title="Fast & Accurate"
              description="Powered by OpenAI Whisper, get highly accurate transcriptions with speaker detection and timestamps."
            />
            <FeatureCard
              icon={<Users className="h-8 w-8" />}
              title="Team Collaboration"
              description="Share transcripts with your team, edit together, and export in multiple formats including SRT and VTT."
            />
          </div>
        </div>
      </section>

      {/* Pricing Preview */}
      <section className="py-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-4">Simple, Transparent Pricing</h2>
          <p className="text-gray-600 mb-8">
            Start with 30 minutes free. No credit card required.
          </p>
          <div className="grid md:grid-cols-3 gap-6">
            <PricingCard
              name="Free"
              price="$0"
              features={["30 min/month", "Basic export formats", "7-day history"]}
            />
            <PricingCard
              name="Starter"
              price="$19"
              features={["5 hours/month", "All export formats", "Speaker detection", "Priority support"]}
              highlighted
            />
            <PricingCard
              name="Pro"
              price="$49"
              features={["20 hours/month", "Team collaboration", "API access", "Custom vocabulary"]}
            />
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-8 px-4">
        <div className="max-w-6xl mx-auto flex justify-between items-center">
          <div className="flex items-center gap-2">
            <FileText className="h-6 w-6 text-primary-600" />
            <span className="font-semibold">Transcribely</span>
          </div>
          <p className="text-gray-500 text-sm">
            Built with Next.js, FastAPI, and Whisper AI
          </p>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="p-6 rounded-xl border bg-gray-50 hover:shadow-md transition">
      <div className="text-primary-600 mb-4">{icon}</div>
      <h3 className="text-xl font-semibold mb-2">{title}</h3>
      <p className="text-gray-600">{description}</p>
    </div>
  );
}

function PricingCard({
  name,
  price,
  features,
  highlighted = false,
}: {
  name: string;
  price: string;
  features: string[];
  highlighted?: boolean;
}) {
  return (
    <div
      className={`p-6 rounded-xl border ${
        highlighted
          ? "border-primary-600 bg-primary-50 ring-2 ring-primary-600"
          : "bg-white"
      }`}
    >
      <h3 className="text-lg font-semibold mb-2">{name}</h3>
      <p className="text-3xl font-bold mb-4">
        {price}
        <span className="text-sm font-normal text-gray-500">/month</span>
      </p>
      <ul className="space-y-2 text-sm text-gray-600">
        {features.map((feature, i) => (
          <li key={i} className="flex items-center gap-2">
            <span className="text-primary-600">✓</span>
            {feature}
          </li>
        ))}
      </ul>
    </div>
  );
}
