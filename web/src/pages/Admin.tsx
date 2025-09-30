import { useEffect, useState } from "react";
import axios from "axios";
import { useApiBase } from "../lib/useApiBase";

type Counts = {
  hsc: number;
  modifiers: number;
  icd9: number;
};

interface DataStatusResponse {
  counts: Counts;
  last_loaded_at: number | null;
  data_dir: string;
}

export default function AdminPage() {
  const apiBase = useApiBase();
  const [status, setStatus] = useState<DataStatusResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await axios.get<DataStatusResponse>(`${apiBase}/data/status`);
      setStatus(data);
    } catch (err) {
      setError("Unable to fetch data status");
    } finally {
      setLoading(false);
    }
  };

  const handleReload = async () => {
    setLoading(true);
    setError(null);
    try {
      await axios.post(`${apiBase}/admin/reload`, null, { params: { force: true } });
      await fetchStatus();
    } catch (err) {
      setError("Reload failed");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  return (
    <section className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-slate-900">Admin</h1>
        <p className="text-sm text-slate-500">Monitor dataset health and trigger CSV reloads.</p>
      </header>
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-800">Dataset status</h2>
            <p className="text-sm text-slate-500">Directory: {status?.data_dir ?? ""}</p>
          </div>
          <button
            onClick={handleReload}
            className="rounded-full bg-teal-500 px-4 py-2 text-sm font-medium text-white shadow-soft transition hover:bg-teal-600 disabled:cursor-not-allowed disabled:bg-slate-300"
            disabled={loading}
          >
            Reload from CSV
          </button>
        </div>
        {error && <p className="mt-4 rounded-lg bg-red-100 px-3 py-2 text-sm text-red-700">{error}</p>}
        <dl className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-slate-200 p-4">
            <dt className="text-xs uppercase tracking-wide text-slate-500">HSC Codes</dt>
            <dd className="text-2xl font-semibold text-slate-800">{status?.counts.hsc ?? 0}</dd>
          </div>
          <div className="rounded-xl border border-slate-200 p-4">
            <dt className="text-xs uppercase tracking-wide text-slate-500">Modifiers</dt>
            <dd className="text-2xl font-semibold text-slate-800">{status?.counts.modifiers ?? 0}</dd>
          </div>
          <div className="rounded-xl border border-slate-200 p-4">
            <dt className="text-xs uppercase tracking-wide text-slate-500">ICD9</dt>
            <dd className="text-2xl font-semibold text-slate-800">{status?.counts.icd9 ?? 0}</dd>
          </div>
        </dl>
        <p className="mt-4 text-xs text-slate-500">
          Last loaded: {status?.last_loaded_at ? new Date(status.last_loaded_at * 1000).toLocaleString() : "unknown"}
        </p>
      </div>
    </section>
  );
}
