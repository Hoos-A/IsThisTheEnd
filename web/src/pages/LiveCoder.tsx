import { useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import { MicrophoneIcon, PauseIcon, ArrowPathIcon } from "@heroicons/react/24/solid";
import { createResilientWebSocket, ResilientWebSocket } from "../lib/ws";
import { AudioRecorder } from "../lib/audio";
import { useApiBase } from "../lib/useApiBase";
import { saveAs } from "file-saver";

type ProviderStatus = {
  stt: string;
  llm: string;
};

type Counts = {
  hsc: number;
  modifiers: number;
  icd9: number;
};

type HealthResponse = {
  status: "ok" | "degraded" | "error";
  details: string[];
  providers: ProviderStatus;
  counts: Counts;
  data_dir: string;
};

type Extraction = {
  problems: string[];
  procedures: string[];
  duration_minutes: number | null;
  setting: string | null;
  visit_type_hint: string | null;
  participants: string[];
  negatives: string[];
  extras: {
    after_hours?: boolean;
    complexity?: "low" | "moderate" | "high";
  };
};

type CandidateModifier = {
  code: string;
  description: string;
  units?: number;
};

type CandidateDiagnosis = {
  code: string;
  description: string;
};

type Candidate = {
  hsc_code: string;
  description: string;
  score: number;
  why: string[];
  citations: string[];
  modifiers: CandidateModifier[];
  diagnoses: CandidateDiagnosis[];
  notes?: string | null;
};

type SuggestionPayload = {
  candidates: Candidate[];
  rationale: string;
  latencyMs: number;
};

type ValidationItem = {
  level: "info" | "warning" | "error";
  message: string;
};

type ValidationResult = {
  ok: boolean;
  items: ValidationItem[];
};

function Pill({ label }: { label: string }) {
  return <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">{label}</span>;
}

function formatDuration(duration: number | null) {
  if (!duration) return "—";
  return `${duration} min`;
}

export default function LiveCoderPage() {
  const apiBase = useApiBase();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<string[]>([]);
  const [partial, setPartial] = useState("");
  const [extraction, setExtraction] = useState<Extraction | null>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [wsInstance, setWsInstance] = useState<ResilientWebSocket | null>(null);
  const recorderRef = useRef<AudioRecorder | null>(null);
  const [recording, setRecording] = useState(false);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [validating, setValidating] = useState(false);

  useEffect(() => {
    axios
      .get<HealthResponse>(`${apiBase}/health`)
      .then((res) => {
        setHealth(res.data);
        setHealthError(null);
      })
      .catch(() => {
        setHealth(null);
        setHealthError("Unable to reach health endpoint");
      });
  }, [apiBase]);

  useEffect(() => {
    const url = `${apiBase.replace(/^http/, "ws")}/stream`;
    const socket = createResilientWebSocket({
      url,
      onMessage: (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "stt_partial") {
          setPartial(data.payload.text ?? "");
        }
        if (data.type === "stt_final") {
          setTranscript((prev) => [...prev, data.payload.text]);
          setPartial("");
        }
        if (data.type === "codes_update") {
          const payload: SuggestionPayload = data.payload;
          setCandidates(payload.candidates);
        }
      },
    });
    setWsInstance(socket);
    return () => socket.close();
  }, [apiBase]);

  const combinedTranscript = useMemo(() => [...transcript, partial].filter(Boolean).join("\n"), [transcript, partial]);

  const statusBadge = useMemo(() => {
    if (!health) {
      return <Pill label="Status: Unknown" />;
    }
    const statusColor =
      health.status === "ok"
        ? "bg-teal-100 text-teal-700"
        : health.status === "degraded"
        ? "bg-amber-100 text-amber-700"
        : "bg-red-100 text-red-700";
    return (
      <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusColor}`}>
        Status: {health.status.toUpperCase()}
      </span>
    );
  }, [health]);

  const handleStart = async () => {
    if (!wsInstance) return;
    if (health?.status === "error") {
      setHealthError("Datasets or credentials missing. Check Admin tab before recording.");
      return;
    }
    setTranscript([]);
    setPartial("");
    setExtraction(null);
    setCandidates([]);
    setValidation(null);
    const recorder = new AudioRecorder({
      onChunk: (chunk) => wsInstance.send(chunk),
      onStop: () => wsInstance.send(JSON.stringify({ type: "audio_stop" })),
    });
    recorderRef.current = recorder;
    await recorder.start();
    wsInstance.send(JSON.stringify({ type: "audio_start", sampleRate: 48000, encoding: "opus" }));
    setRecording(true);
  };

  const handleStop = () => {
    recorderRef.current?.stop();
    setRecording(false);
  };

  useEffect(() => {
    if (!combinedTranscript || health?.status === "error") return;
    setValidation(null);
    const fetchExtraction = async () => {
      try {
        const { data } = await axios.post<{ extraction: Extraction; candidates: Candidate[] }>(
          `${apiBase}/llm/suggest`,
          { transcript: combinedTranscript }
        );
        setExtraction(data.extraction);
        setCandidates(data.candidates);
      } catch (err) {
        console.error(err);
      }
    };
    const debounce = setTimeout(fetchExtraction, 1000);
    return () => clearTimeout(debounce);
  }, [combinedTranscript, apiBase, health?.status]);

  const handleValidate = async () => {
    if (!extraction || candidates.length === 0) return;
    setValidating(true);
    try {
      const { data } = await axios.post<ValidationResult>(`${apiBase}/llm/validate`, {
        candidate: candidates[0],
        extraction,
      });
      setValidation(data);
    } catch (err) {
      console.error(err);
    } finally {
      setValidating(false);
    }
  };

  const handleExport = () => {
    const rows = candidates.map((candidate) => ({
      hsc_code: candidate.hsc_code,
      description: candidate.description,
      modifiers: candidate.modifiers.map((m) => `${m.code}${m.units ? `:${m.units}` : ""}`).join(";"),
      diagnoses: candidate.diagnoses.map((d) => d.code).join(";"),
      why: candidate.why.join(";"),
      citations: candidate.citations.join(";"),
      generated_at: new Date().toISOString(),
    }));
    const header = Object.keys(rows[0] ?? { hsc_code: "", description: "", modifiers: "", diagnoses: "", why: "", citations: "", generated_at: "" });
    const csv = [header.join(","), ...rows.map((row) => header.map((key) => `"${(row as any)[key] ?? ""}"`).join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    saveAs(blob, `ahs-billing-${Date.now()}.csv`);
  };

  return (
    <section className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Live coder</h1>
          <p className="text-sm text-slate-500">Capture the patient encounter, surface codes, validate, and export.</p>
        </div>
        <div className="flex items-center gap-2">
          {statusBadge}
          <Pill label={`STT: ${health?.providers.stt ?? "?"}`} />
          <Pill label={`LLM: ${health?.providers.llm ?? "?"}`} />
          <Pill label={`Data: ${health?.counts.hsc ?? 0} HSC / ${health?.counts.modifiers ?? 0} Mod / ${health?.counts.icd9 ?? 0} ICD`} />
        </div>
      </header>

      {(healthError || (health && health.details.length > 0)) && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <p className="font-semibold">Environment notice</p>
          <ul className="list-disc pl-6">
            {health?.details.map((detail, idx) => (
              <li key={idx}>{detail}</li>
            ))}
            {healthError && <li>{healthError}</li>}
          </ul>
        </div>
      )}

      <div className="flex flex-col gap-6 lg:flex-row">
        <div className="flex-1 space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-800">Microphone</h2>
              <button
                onClick={recording ? handleStop : handleStart}
                disabled={health?.status === "error"}
                className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-white transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:ring-offset-2 ${
                  recording ? "bg-red-500 hover:bg-red-600" : "bg-teal-500 hover:bg-teal-600"
                } disabled:cursor-not-allowed disabled:bg-slate-300`}
                aria-pressed={recording}
                aria-label={recording ? "Stop recording" : "Start recording"}
              >
                {recording ? <PauseIcon className="h-5 w-5" /> : <MicrophoneIcon className="h-5 w-5" />}
                {recording ? "Stop" : "Record"}
              </button>
            </div>
            <p className="mt-2 text-sm text-slate-500">Press record to stream audio securely to the assistant.</p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <h2 className="text-lg font-semibold text-slate-800">Transcript</h2>
            <div className="mt-4 max-h-72 space-y-3 overflow-y-auto text-sm leading-relaxed text-slate-700">
              {transcript.map((chunk, index) => (
                <p key={index} className="rounded-xl bg-slate-100 px-3 py-2">
                  {chunk}
                </p>
              ))}
              {partial && <p className="rounded-xl border border-dashed border-teal-400 px-3 py-2 text-teal-600">{partial}</p>}
            </div>
          </div>
        </div>

        <aside className="w-full max-w-sm space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <h2 className="text-lg font-semibold text-slate-800">Entities</h2>
            <dl className="mt-4 space-y-3 text-sm text-slate-600">
              <div>
                <dt className="font-medium text-slate-500">Problems</dt>
                <dd>{extraction?.problems.join(", ") || "—"}</dd>
              </div>
              <div>
                <dt className="font-medium text-slate-500">Procedures</dt>
                <dd>{extraction?.procedures.join(", ") || "—"}</dd>
              </div>
              <div>
                <dt className="font-medium text-slate-500">Duration</dt>
                <dd>{formatDuration(extraction?.duration_minutes ?? null)}</dd>
              </div>
              <div>
                <dt className="font-medium text-slate-500">Setting</dt>
                <dd>{extraction?.setting ?? "—"}</dd>
              </div>
              <div>
                <dt className="font-medium text-slate-500">Visit Type</dt>
                <dd>{extraction?.visit_type_hint ?? "—"}</dd>
              </div>
              <div>
                <dt className="font-medium text-slate-500">Participants</dt>
                <dd>{extraction?.participants.join(", ") || "—"}</dd>
              </div>
              <div>
                <dt className="font-medium text-slate-500">Negatives</dt>
                <dd>{extraction?.negatives.join(", ") || "—"}</dd>
              </div>
              <div>
                <dt className="font-medium text-slate-500">After Hours</dt>
                <dd>{extraction?.extras.after_hours ? "Yes" : "No"}</dd>
              </div>
              <div>
                <dt className="font-medium text-slate-500">Complexity</dt>
                <dd>{extraction?.extras.complexity ?? "—"}</dd>
              </div>
            </dl>
          </div>
        </aside>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-800">Code suggestions</h2>
          <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {candidates.length} candidates
          </span>
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full table-fixed divide-y divide-slate-200 text-left text-sm">
            <thead className="sticky top-0 bg-slate-100 text-xs uppercase tracking-wide text-slate-600">
              <tr>
                <th className="sticky left-0 bg-slate-100 px-4 py-3">HSC</th>
                <th className="px-4 py-3">Description</th>
                <th className="px-4 py-3">Modifiers</th>
                <th className="px-4 py-3">Diagnoses</th>
                <th className="px-4 py-3">Why</th>
                <th className="px-4 py-3">Citations</th>
                <th className="px-4 py-3">Score</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {candidates.map((candidate) => (
                <tr key={candidate.hsc_code} className="align-top">
                  <td className="sticky left-0 bg-white px-4 py-3 font-semibold text-slate-800">
                    {candidate.hsc_code}
                  </td>
                  <td className="px-4 py-3 text-slate-700">
                    <p className="font-medium text-slate-900">{candidate.description}</p>
                    {candidate.notes && <p className="mt-1 text-xs text-slate-500">{candidate.notes}</p>}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      {candidate.modifiers.map((modifier, idx) => (
                        <label key={modifier.code} className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">
                          <span className="font-semibold text-slate-700">{modifier.code}</span>
                          <input
                            type="number"
                            className="w-16 rounded border border-slate-300 px-2 py-1 text-xs focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
                            value={modifier.units ?? ""}
                            onChange={(event) => {
                              const raw = event.target.value;
                              const units = raw === "" ? undefined : Number(raw);
                              setCandidates((prev) =>
                                prev.map((item) =>
                                  item.hsc_code === candidate.hsc_code
                                    ? {
                                        ...item,
                                        modifiers: item.modifiers.map((mod, i) =>
                                          i === idx
                                            ? {
                                                ...mod,
                                                units: units !== undefined && Number.isFinite(units) ? Number(units) : undefined,
                                              }
                                            : mod
                                        ),
                                      }
                                    : item
                                )
                              );
                            }}
                            min={0}
                            aria-label={`Units for modifier ${modifier.code}`}
                          />
                        </label>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      {candidate.diagnoses.map((diagnosis) => (
                        <span key={diagnosis.code} className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">
                          {diagnosis.code}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      {candidate.why.map((reason, idx) => (
                        <span key={`${candidate.hsc_code}-why-${idx}`} className="rounded-full bg-teal-50 px-3 py-1 text-xs text-teal-600">
                          {reason}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-500">{candidate.citations.join(", ")}</td>
                  <td className="px-4 py-3 text-sm font-semibold text-slate-700">{candidate.score.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <footer className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white px-6 py-4 shadow-soft">
        <div className="flex items-center gap-2 text-sm text-slate-600">
          <ArrowPathIcon className="h-5 w-5 text-teal-500" />
          <span>Validate suggested codes against deterministic rules.</span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleValidate}
            disabled={!candidates.length || validating}
            className="rounded-full border border-teal-500 px-4 py-2 text-sm font-semibold text-teal-500 transition hover:bg-teal-50 disabled:cursor-not-allowed disabled:border-slate-300 disabled:text-slate-400"
          >
            {validating ? "Validating…" : "Validate"}
          </button>
          <button
            onClick={handleExport}
            disabled={!candidates.length}
            className="rounded-full bg-teal-500 px-4 py-2 text-sm font-semibold text-white shadow-soft transition hover:bg-teal-600 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            Export CSV
          </button>
        </div>
      </footer>

      {validation && (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
          <h3 className={`text-lg font-semibold ${validation.ok ? "text-teal-600" : "text-red-600"}`}>
            {validation.ok ? "Validation passed" : "Validation issues"}
          </h3>
          <ul className="mt-3 space-y-2 text-sm">
            {validation.items.map((item, idx) => (
              <li
                key={idx}
                className={`rounded-lg px-3 py-2 ${
                  item.level === "error"
                    ? "bg-red-100 text-red-700"
                    : item.level === "warning"
                    ? "bg-amber-100 text-amber-700"
                    : "bg-teal-50 text-teal-700"
                }`}
              >
                {item.message}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
