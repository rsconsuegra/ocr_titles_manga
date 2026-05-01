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
import { Button, Card, ErrorBanner, FormSkeleton, Input, Select } from "../components/ui";

export default function Settings() {
  const [error, setError] = useState<string | null>(null);

  return (
    <div>
      <h1 className="mb-6 font-display text-xl font-bold text-ink">Settings</h1>
      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}
      <div className="space-y-6">
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
  useEffect(() => {
    load();
  }, [load]);
  /* eslint-enable react-hooks/set-state-in-effect */

  async function handlePing() {
    setPinging(true);
    setMessage(null);
    try {
      const res = await pingOllamaUrl(baseUrl);
      if (res.available_llm_models.length > 0 || res.available_vision_models.length > 0) {
        setSettings((prev) =>
          prev
            ? {
                ...prev,
                available_llm_models: res.available_llm_models,
                available_vision_models: res.available_vision_models,
              }
            : prev,
        );
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
      setSettings((prev) =>
        prev
          ? {
              ...prev,
              base_url: res.base_url,
              default_model: res.default_model,
              default_vision_model: res.default_vision_model,
              available_llm_models: res.available_llm_models,
              available_vision_models: res.available_vision_models,
            }
          : prev,
      );
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

  if (!settings) return <FormSkeleton />;

  return (
    <Card>
      <h2 className="mb-3 font-display text-sm font-bold uppercase tracking-wider text-sand">
        Ollama Connection
      </h2>
      <p className="mb-3 text-xs text-sand">
        Ephemeral URL (e.g. Cloudflare tunnel). Saved to configs.toml on disk.
      </p>
      <div className="space-y-3">
        <Input
          label="Base URL"
          type="text"
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          placeholder="https://your-tunnel.trycloudflare.com"
        />

        <Select
          label="Default Vision Model"
          value={defaultVisionModel}
          onChange={(e) => setDefaultVisionModel(e.target.value)}
          options={
            visionModels.length > 0
              ? [
                  { value: "", label: "\u2014 Not set \u2014" },
                  ...visionModels.map((m: OllamaModelInfo) => ({ value: m.name, label: m.name })),
                ]
              : [
                  { value: "", label: "\u2014 Not set \u2014" },
                  { value: "__none__", label: "No models \u2014 ping Ollama first" },
                ]
          }
        />

        <Select
          label="Default LLM Model"
          value={defaultModel}
          onChange={(e) => setDefaultModel(e.target.value)}
          options={
            llmModels.length > 0
              ? [
                  { value: "", label: "\u2014 Not set \u2014" },
                  ...llmModels.map((m: OllamaModelInfo) => ({
                    value: m.name,
                    label: `${m.name} ${m.parameter_size ? `(${m.parameter_size})` : ""}`,
                  })),
                ]
              : [
                  { value: "", label: "\u2014 Not set \u2014" },
                  { value: "__none__", label: "No models \u2014 ping Ollama first" },
                ]
          }
        />

        {message && (
          <div className="flex items-center gap-2 text-xs">
            <span
              className={`size-2 shrink-0 rounded-full ${message.ok ? "bg-success" : "bg-error"}`}
            />
            <span className={message.ok ? "text-indigo" : "text-red-500"}>{message.text}</span>
          </div>
        )}
        <div className="flex gap-2">
          <Button onClick={handleSave} disabled={saving || !hasChanges} className="flex-1">
            {saving ? "Saving..." : "Save All"}
          </Button>
          <Button
            onClick={handlePing}
            disabled={pinging || !baseUrl}
            className="flex-1"
            variant="secondary"
          >
            {pinging ? "Pinging..." : "Ping"}
          </Button>
        </div>
      </div>
    </Card>
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
  useEffect(() => {
    load();
  }, [load]);
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

  if (!info) return <FormSkeleton />;

  return (
    <Card>
      <h2 className="mb-3 font-display text-sm font-bold uppercase tracking-wider text-sand">
        OpenRouter API Key
      </h2>
      <div className="space-y-3">
        {info && (
          <div className="flex items-center justify-between rounded border border-linen bg-cream p-2">
            <div>
              <div className="text-xs text-sand">Status</div>
              <div className="flex items-center gap-2">
                <span
                  className={`size-2 inline-block rounded-full ${info.has_key ? "bg-indigo" : "bg-sand/50"}`}
                />
                <span className="text-sm text-charcoal">
                  {info.has_key ? info.masked_key || "Key set" : "No key configured"}
                </span>
              </div>
              {info.source && <div className="mt-1 text-xs text-sand">Source: {info.source}</div>}
            </div>
            {info.is_active && (
              <Button onClick={handleReset} variant="secondary" className="text-xs">
                Reset to Default
              </Button>
            )}
          </div>
        )}

        {!showKeyInput ? (
          <Button onClick={() => setShowKeyInput(true)} className="w-full">
            {info?.has_key ? "Update API Key" : "Configure API Key"}
          </Button>
        ) : (
          <div className="space-y-2">
            <Input
              label="New API Key"
              type="password"
              value={newKey}
              onChange={(e) => setNewKey(e.target.value)}
              placeholder="sk-or-..."
            />
            {message && (
              <div className="flex items-center gap-2 text-xs">
                <span
                  className={`size-2 shrink-0 rounded-full ${message.ok ? "bg-success" : "bg-error"}`}
                />
                <span className={message.ok ? "text-indigo" : "text-red-500"}>{message.text}</span>
              </div>
            )}
            <div className="flex gap-2">
              <Button onClick={handleSave} disabled={saving || !newKey} className="flex-1">
                {saving ? "Saving..." : "Save Key"}
              </Button>
              <Button
                onClick={handleValidate}
                disabled={validating || !newKey}
                variant="secondary"
                className="flex-1"
              >
                {validating ? "Checking..." : "Validate"}
              </Button>
              <Button
                onClick={() => {
                  setShowKeyInput(false);
                  setMessage(null);
                  setNewKey("");
                }}
                variant="secondary"
              >
                Cancel
              </Button>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
