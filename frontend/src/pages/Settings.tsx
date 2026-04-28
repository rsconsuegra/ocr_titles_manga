import { useCallback, useEffect, useState } from "react";

import {
  deleteCredential,
  getCredential,
  getOllamaSettings,
  pingOllamaUrl,
  updateCredential,
  updateOllamaUrl,
  validateCredential,
} from "../api/settings";
import type { CredentialInfo, OllamaModelInfo, OllamaSettingsResponse } from "../api/types";
import { DsoButton, DsoErrorBanner, DsoSelect } from "../components/dso";

export default function Settings() {
  const [error, setError] = useState<string | null>(null);

  return (
    <div>
      <h1 className="mb-6 font-display text-xl font-bold text-bright">Settings</h1>
      {error && <DsoErrorBanner onClick={() => setError(null)}>{error}</DsoErrorBanner>}
      <div className="grid gap-6 lg:grid-cols-2">
        <OllamaSection onError={setError} />
        <OpenRouterSection onError={setError} />
      </div>
    </div>
  );
}

function OllamaSection({ onError }: { onError: (e: string) => void }) {
  const [settings, setSettings] = useState<OllamaSettingsResponse | null>(null);
  const [baseUrl, setBaseUrl] = useState("");
  const [savedUrl, setSavedUrl] = useState("");
  const [defaultModel, setDefaultModel] = useState("");
  const [savedDefaultModel, setSavedDefaultModel] = useState("");
  const [defaultVisionModel, setDefaultVisionModel] = useState("");
  const [savedDefaultVisionModel, setSavedDefaultVisionModel] = useState("");
  const [saving, setSaving] = useState(false);
  const [pinging, setPinging] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await getOllamaSettings();
      setSettings(data);
      setBaseUrl(data.base_url);
      setSavedUrl(data.base_url);
      setDefaultModel(data.default_model);
      setSavedDefaultModel(data.default_model);
      setDefaultVisionModel(data.default_vision_model);
      setSavedDefaultVisionModel(data.default_vision_model);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Failed to load Ollama settings");
    }
  }, [onError]);

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => { load(); }, [load]);
  /* eslint-enable react-hooks/set-state-in-effect */

  async function handlePing() {
    setPinging(true);
    setMessage(null);
    try {
      const res = await pingOllamaUrl(baseUrl);
      if (res.available_llm_models.length > 0 || res.available_vision_models.length > 0) {
        setSettings((prev) => prev ? {
          ...prev,
          available_llm_models: res.available_llm_models,
          available_vision_models: res.available_vision_models,
        } : prev);
      }
      setMessage({ ok: res.validated, text: res.message });
    } catch (e) {
      setMessage({ ok: false, text: e instanceof Error ? e.message : "Ping failed" });
    } finally {
      setPinging(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    setMessage(null);
    try {
      const res = await updateOllamaUrl({
        base_url: baseUrl,
        default_model: defaultModel,
        default_vision_model: defaultVisionModel,
      });
      setSavedUrl(baseUrl);
      setSavedDefaultModel(defaultModel);
      setSavedDefaultVisionModel(defaultVisionModel);
      setSettings((prev) => prev ? {
        ...prev,
        base_url: res.base_url,
        default_model: res.default_model,
        default_vision_model: res.default_vision_model,
        available_llm_models: res.available_llm_models,
        available_vision_models: res.available_vision_models,
      } : prev);
      setMessage({ ok: res.validated, text: `Saved. ${res.message}` });
    } catch (e) {
      onError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  const hasChanges =
    baseUrl !== savedUrl ||
    defaultModel !== savedDefaultModel ||
    defaultVisionModel !== savedDefaultVisionModel;

  const llmModels = settings?.available_llm_models ?? [];
  const visionModels = settings?.available_vision_models ?? [];

  return (
    <div className="neo-panel rounded-lg p-4">
      <h2 className="mb-3 font-display text-sm font-bold uppercase tracking-wider text-muted">
        Ollama Connection
      </h2>
      <p className="mb-3 text-xs text-muted">
        Ephemeral URL (e.g. Cloudflare tunnel). Saved to configs.toml on disk.
      </p>
      <div className="space-y-3">
        <div>
          <label className="mb-1 block text-xs text-muted">Base URL</label>
          <input
            type="text"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="https://your-tunnel.trycloudflare.com"
            className="w-full rounded border border-highlight/20 bg-inset p-2 text-sm text-bright placeholder:text-muted/50 focus:border-teal/50 focus:outline-none"
          />
        </div>

        <DsoSelect
          label="Default Vision Model"
          value={defaultVisionModel}
          onChange={(e) => setDefaultVisionModel(e.target.value)}
        >
          <option value="">— Not set —</option>
          {visionModels.length > 0 ? (
            visionModels.map((m: OllamaModelInfo) => (
              <option key={m.name} value={m.name}>
                {m.name}
              </option>
            ))
          ) : (
            <option disabled>No models — ping Ollama first</option>
          )}
        </DsoSelect>

        <DsoSelect
          label="Default LLM Model"
          value={defaultModel}
          onChange={(e) => setDefaultModel(e.target.value)}
        >
          <option value="">— Not set —</option>
          {llmModels.length > 0 ? (
            llmModels.map((m: OllamaModelInfo) => (
              <option key={m.name} value={m.name}>
                {m.name} {m.parameter_size ? `(${m.parameter_size})` : ""}
              </option>
            ))
          ) : (
            <option disabled>No models — ping Ollama first</option>
          )}
        </DsoSelect>

        {message && (
          <div
            className={`rounded border p-2 text-xs ${
              message.ok
                ? "border-teal/30 bg-teal/10 text-teal"
                : "border-red-500/30 bg-red-500/10 text-red-400"
            }`}
          >
            {message.text}
          </div>
        )}
        <div className="flex gap-2">
          <DsoButton onClick={handleSave} disabled={saving || !hasChanges} className="flex-1">
            {saving ? "Saving..." : "Save All"}
          </DsoButton>
          <DsoButton
            onClick={handlePing}
            disabled={pinging || !baseUrl}
            className="flex-1"
            variant="secondary"
          >
            {pinging ? "Pinging..." : "Ping"}
          </DsoButton>
        </div>
      </div>
    </div>
  );
}

function OpenRouterSection({ onError }: { onError: (e: string) => void }) {
  const [info, setInfo] = useState<CredentialInfo | null>(null);
  const [newKey, setNewKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const [showKeyInput, setShowKeyInput] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await getCredential("openrouter");
      setInfo(data);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Failed to load credentials");
    }
  }, [onError]);

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => { load(); }, [load]);
  /* eslint-enable react-hooks/set-state-in-effect */

  async function handleValidate() {
    setValidating(true);
    setMessage(null);
    try {
      const res = await validateCredential("openrouter", newKey);
      setMessage({ ok: res.valid, text: res.message });
    } catch (e) {
      setMessage({ ok: false, text: e instanceof Error ? e.message : "Validation failed" });
    } finally {
      setValidating(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    setMessage(null);
    try {
      const res = await updateCredential("openrouter", newKey);
      setMessage({ ok: res.valid, text: res.message });
      setNewKey("");
      setShowKeyInput(false);
      load();
    } catch (e) {
      onError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleReset() {
    if (!confirm("Reset to environment default key?")) return;
    try {
      await deleteCredential("openrouter");
      setMessage({ ok: true, text: "Reverted to env default" });
      load();
    } catch (e) {
      onError(e instanceof Error ? e.message : "Reset failed");
    }
  }

  return (
    <div className="neo-panel rounded-lg p-4">
      <h2 className="mb-3 font-display text-sm font-bold uppercase tracking-wider text-muted">
        OpenRouter API Key
      </h2>
      <div className="space-y-3">
        {info && (
          <div className="flex items-center justify-between rounded border border-highlight/10 bg-inset p-2">
            <div>
              <div className="text-xs text-muted">Status</div>
              <div className="flex items-center gap-2">
                <span className={`led ${info.has_key ? "led-active" : "led-inactive"}`} />
                <span className="text-sm text-bright">
                  {info.has_key ? (info.masked_key || "Key set") : "No key configured"}
                </span>
              </div>
              {info.source && (
                <div className="mt-1 text-xs text-muted">Source: {info.source}</div>
              )}
            </div>
            {info.is_active && (
              <DsoButton onClick={handleReset} variant="secondary" className="text-xs">
                Reset to Default
              </DsoButton>
            )}
          </div>
        )}

        {!showKeyInput ? (
          <DsoButton onClick={() => setShowKeyInput(true)} className="w-full">
            {info?.has_key ? "Update API Key" : "Configure API Key"}
          </DsoButton>
        ) : (
          <div className="space-y-2">
            <div>
              <label className="mb-1 block text-xs text-muted">New API Key</label>
              <input
                type="password"
                value={newKey}
                onChange={(e) => setNewKey(e.target.value)}
                placeholder="sk-or-..."
                className="w-full rounded border border-highlight/20 bg-inset p-2 text-sm text-bright placeholder:text-muted/50 focus:border-teal/50 focus:outline-none"
              />
            </div>
            {message && (
              <div
                className={`rounded border p-2 text-xs ${
                  message.ok
                    ? "border-teal/30 bg-teal/10 text-teal"
                    : "border-red-500/30 bg-red-500/10 text-red-400"
                }`}
              >
                {message.text}
              </div>
            )}
            <div className="flex gap-2">
              <DsoButton onClick={handleSave} disabled={saving || !newKey} className="flex-1">
                {saving ? "Saving..." : "Save Key"}
              </DsoButton>
              <DsoButton
                onClick={handleValidate}
                disabled={validating || !newKey}
                variant="secondary"
                className="flex-1"
              >
                {validating ? "Checking..." : "Validate"}
              </DsoButton>
              <DsoButton
                onClick={() => { setShowKeyInput(false); setMessage(null); setNewKey(""); }}
                variant="secondary"
              >
                Cancel
              </DsoButton>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
