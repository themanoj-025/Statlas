"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type {
  ExecutiveDashboard,
  AnalyticsAlert,
  FeatureUsageResult,
} from "@/lib/types";

type Tab = "executive" | "features" | "conversion" | "alerts";

export default function AnalyticsPage() {
  const [tab, setTab] = useState<Tab>("executive");
  const [dashboard, setDashboard] = useState<ExecutiveDashboard | null>(null);
  const [alerts, setAlerts] = useState<AnalyticsAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboard();
  }, []);

  async function loadDashboard() {
    try {
      setLoading(true);
      setError(null);
      const data = await api.executiveDashboard();
      setDashboard(data);
      const alertData = await api.analyticsAlerts(20);
      setAlerts(alertData.alerts);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen p-8">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-2xl font-bold mb-8">Analytics Dashboard</h1>
          <div className="animate-pulse space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-32 bg-gray-200 dark:bg-gray-800 rounded" />
            ))}
          </div>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="min-h-screen p-8">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-2xl font-bold mb-8">Analytics Dashboard</h1>
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
            <h2 className="text-red-800 dark:text-red-200 font-semibold">Error Loading Dashboard</h2>
            <p className="text-red-600 dark:text-red-400 mt-2">{error}</p>
          </div>
        </div>
      </main>
    );
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: "executive", label: "Executive" },
    { id: "features", label: "Features" },
    { id: "conversion", label: "Conversion" },
    { id: "alerts", label: "Alerts" },
  ];

  return (
    <main className="min-h-screen p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-2xl font-bold">Analytics Dashboard</h1>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            Internal use only
          </span>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-8 border-b border-gray-200 dark:border-gray-700">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                tab === t.id
                  ? "border-blue-500 text-blue-600 dark:text-blue-400"
                  : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Executive Tab */}
        {tab === "executive" && dashboard && (
          <div className="space-y-8">
            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <KpiCard
                label="DAU"
                value={dashboard.dau.dau_total}
                subtext={`${dashboard.dau.dau_pro} Pro / ${dashboard.dau.dau_free} Free`}
              />
              <KpiCard
                label="MAU"
                value={dashboard.mau.mau_total}
                subtext={`${dashboard.mau.mau_pro} Pro / ${dashboard.mau.mau_free} Free`}
              />
              <KpiCard
                label="MRR"
                value={`€${dashboard.arpu.mrr_eur.toLocaleString()}`}
                subtext={`${dashboard.arpu.pro_users} Pro users`}
              />
              <KpiCard
                label="Churn"
                value={`${dashboard.churn.churn_rate_pct}%`}
                subtext={`${dashboard.churn.annualized_churn_pct}% annualized`}
                alert={dashboard.churn.churn_rate_pct > 5}
              />
            </div>

            {/* Feature Usage */}
            <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
              <h2 className="text-lg font-semibold mb-4">Feature Adoption</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 dark:border-gray-700">
                      <th className="text-left py-2">Feature</th>
                      <th className="text-right py-2">Adoption</th>
                      <th className="text-right py-2">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dashboard.feature_usage.map((f: FeatureUsageResult) => (
                      <tr key={f.feature_name} className="border-b border-gray-100 dark:border-gray-800">
                        <td className="py-2 font-medium">{f.feature_name}</td>
                        <td className="py-2 text-right">{f.adoption_pct}%</td>
                        <td className="py-2 text-right">{f.actions_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Conversion Funnel */}
            <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
              <h2 className="text-lg font-semibold mb-4">Conversion Funnel</h2>
              <div className="space-y-3">
                <FunnelStep
                  label="Signups"
                  count={dashboard.conversion.step_1_signups}
                  rate={100}
                />
                <FunnelStep
                  label="Created Shortlist"
                  count={dashboard.conversion.step_2_created_shortlist}
                  rate={dashboard.conversion.step_2_rate}
                />
                <FunnelStep
                  label="Upgrade Attempted"
                  count={dashboard.conversion.step_3_upgrade_attempted}
                  rate={dashboard.conversion.step_3_rate}
                />
                <FunnelStep
                  label="Subscribed"
                  count={dashboard.conversion.step_4_subscribed}
                  rate={dashboard.conversion.step_4_rate}
                />
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-4">
                Overall conversion: {dashboard.conversion.overall_conversion}%
              </p>
            </div>

            {/* Data Governance Footer */}
            <div className="text-xs text-gray-500 dark:text-gray-400 border-t border-gray-200 dark:border-gray-700 pt-4">
              <p>
                Last updated: {new Date(dashboard.last_updated).toLocaleString()}.
                Data confidence: {dashboard.data_confidence}.
              </p>
              <p className="mt-1">{dashboard.caveat}</p>
            </div>
          </div>
        )}

        {/* Features Tab */}
        {tab === "features" && dashboard && (
          <div className="space-y-6">
            {dashboard.feature_usage.map((f: FeatureUsageResult) => (
              <FeatureCard key={f.feature_name} feature={f} />
            ))}
          </div>
        )}

        {/* Conversion Tab */}
        {tab === "conversion" && dashboard && (
          <div className="space-y-6">
            <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
              <h2 className="text-lg font-semibold mb-2">Conversion Funnel</h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                Period: {dashboard.conversion.period}
              </p>
              <div className="space-y-4">
                {[
                  { label: "Step 1: Signups", count: dashboard.conversion.step_1_signups, rate: 100 },
                  { label: "Step 2: Created Shortlist", count: dashboard.conversion.step_2_created_shortlist, rate: dashboard.conversion.step_2_rate },
                  { label: "Step 3: Upgrade Attempted", count: dashboard.conversion.step_3_upgrade_attempted, rate: dashboard.conversion.step_3_rate },
                  { label: "Step 4: Subscribed", count: dashboard.conversion.step_4_subscribed, rate: dashboard.conversion.step_4_rate },
                ].map((step) => (
                  <div key={step.label} className="flex items-center gap-4">
                    <div className="w-48 text-sm font-medium">{step.label}</div>
                    <div className="flex-1 bg-gray-100 dark:bg-gray-800 rounded-full h-6">
                      <div
                        className="bg-blue-500 h-6 rounded-full flex items-center px-3 text-xs text-white font-medium"
                        style={{ width: `${Math.max(step.rate, 5)}%` }}
                      >
                        {step.count} ({step.rate}%)
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Alerts Tab */}
        {tab === "alerts" && (
          <div className="space-y-4">
            {alerts.length === 0 ? (
              <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-6 text-center">
                <p className="text-green-800 dark:text-green-200 font-medium">
                  No alerts fired. All metrics within thresholds.
                </p>
              </div>
            ) : (
              alerts.map((alert: AnalyticsAlert) => (
                <div
                  key={alert.id}
                  className={`border rounded-lg p-4 ${
                    alert.acknowledged_at
                      ? "bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700"
                      : "bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold">{alert.alert_name}</h3>
                    <span className="text-xs text-gray-500">
                      {alert.fired_at ? new Date(alert.fired_at).toLocaleString() : "—"}
                    </span>
                  </div>
                  <p className="text-sm mt-1">{alert.message}</p>
                  <p className="text-xs text-gray-500 mt-2">
                    {alert.metric_name}: {alert.actual_value} (threshold: {alert.threshold_value})
                  </p>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </main>
  );
}

function KpiCard({
  label,
  value,
  subtext,
  alert,
}: {
  label: string;
  value: string | number;
  subtext: string;
  alert?: boolean;
}) {
  return (
    <div
      className={`border rounded-lg p-4 ${
        alert
          ? "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800"
          : "bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700"
      }`}
    >
      <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{subtext}</p>
    </div>
  );
}

function FunnelStep({
  label,
  count,
  rate,
}: {
  label: string;
  count: number;
  rate: number;
}) {
  return (
    <div className="flex items-center gap-3">
      <div className="w-40 text-sm">{label}</div>
      <div className="flex-1 bg-gray-100 dark:bg-gray-800 rounded-full h-5">
        <div
          className="bg-blue-500 h-5 rounded-full flex items-center px-2 text-xs text-white"
          style={{ width: `${Math.max(rate, 5)}%` }}
        >
          {count}
        </div>
      </div>
      <div className="w-16 text-right text-sm text-gray-500">{rate}%</div>
    </div>
  );
}

function FeatureCard({ feature }: { feature: FeatureUsageResult }) {
  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
      <div className="flex items-center justify-between">
        <h3 className="font-medium">{feature.feature_name}</h3>
        <span className="text-sm text-gray-500">
          {feature.adoption_pct}% adoption
        </span>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-4 text-sm">
        <div>
          <p className="text-gray-500 dark:text-gray-400">Users</p>
          <p className="font-medium">{feature.adoption_count}</p>
        </div>
        <div>
          <p className="text-gray-500 dark:text-gray-400">Actions</p>
          <p className="font-medium">{feature.actions_count}</p>
        </div>
        <div>
          <p className="text-gray-500 dark:text-gray-400">Avg Time</p>
          <p className="font-medium">{feature.avg_engagement_minutes}m</p>
        </div>
      </div>
    </div>
  );
}
