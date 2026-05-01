# US-FRE8: Redesigned Settings Page

**Sub-phase**: FR-E — Secondary Pages
**Depends on**: US-FRC7 (DSO removed, new components)
**Blocks**: None

---

## Story

> As a user, I want a clean settings page with Ollama connection and API credential sections so that I can configure external service integrations.

---

## Scope

### In Scope
- Rewrite Settings.tsx with two Card sections
- Ollama: URL Input, Ping button, connection status, model selectors
- Credentials: OpenRouter key Input, Validate/Save/Delete buttons

### Out of Scope
- New settings categories
- Loading states (US-FRF1)

---

## Implementation Details

### 1. `frontend/src/pages/Settings.tsx` (rewritten)

Layout:
```
┌─────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────┐ │
│ │ Ollama Connection                            │ │
│ │                                              │ │
│ │ URL:  [http://localhost:11434]  [Ping]       │ │
│ │ Status: ● Connected                          │ │
│ │                                              │ │
│ │ Default Vision Model: [Select ▾]             │ │
│ │ Default LLM Model:    [Select ▾]             │ │
│ │                                              │ │
│ │ [Save]                                       │ │
│ └─────────────────────────────────────────────┘ │
│                                                  │
│ ┌─────────────────────────────────────────────┐ │
│ │ API Credentials                              │ │
│ │                                              │ │
│ │ OpenRouter API Key                           │ │
│ │ [••••••••••••••••]  [Validate] [Save] [Del] │ │
│ │                                              │ │
│ │ Last validated: 2 hours ago                  │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

**Ollama section:**
```tsx
<Card>
  <Card.Header title="Ollama Connection" />
  <div className="space-y-4">
    <div className="flex gap-3">
      <Input
        label="URL"
        value={ollamaUrl}
        onChange={(e) => setOllamaUrl(e.target.value)}
        className="flex-1"
      />
      <div className="pt-6">
        <Button variant="secondary" onClick={handlePing}>Ping</Button>
      </div>
    </div>
    <div className="flex items-center gap-2">
      <span className={`w-2 h-2 rounded-full ${pingResult?.success ? "bg-success" : "bg-error"}`} />
      <span className="text-sm font-body text-charcoal">
        {pingResult?.success ? "Connected" : "Disconnected"}
      </span>
    </div>
    <Select
      label="Default Vision Model"
      options={visionModels.map(m => ({ value: m.name, label: m.name }))}
      value={selectedVisionModel}
      onChange={...}
    />
    <Select
      label="Default LLM Model"
      options={llmModels.map(m => ({ value: m.name, label: m.name }))}
      value={selectedLlmModel}
      onChange={...}
    />
    <Button variant="primary" onClick={handleSaveOllama}>Save</Button>
  </div>
</Card>
```

**Credentials section:**
```tsx
<Card>
  <Card.Header title="API Credentials" />
  <div className="space-y-4">
    <Input
      label="OpenRouter API Key"
      type="password"
      value={apiKey}
      onChange={(e) => setApiKey(e.target.value)}
    />
    <div className="flex gap-2">
      <Button variant="secondary" onClick={handleValidate}>Validate</Button>
      <Button variant="primary" onClick={handleSaveKey}>Save</Button>
      <Button variant="danger" size="sm" onClick={handleDeleteKey}>Delete</Button>
    </div>
    {validationMessage && (
      <p className="text-sm font-body text-success">{validationMessage}</p>
    )}
  </div>
</Card>
```

---

## Acceptance Criteria

- [ ] Two Card sections stacked: "Ollama Connection" and "API Credentials"
- [ ] Ollama: URL Input, "Ping" Button secondary, connection status dot
- [ ] Ollama: vision and LLM model Select dropdowns
- [ ] Ollama: "Save" Button primary
- [ ] Credentials: OpenRouter key Input with type=password
- [ ] Credentials: "Validate", "Save", "Delete" Buttons
- [ ] All inputs use new Input component with label and error states
- [ ] Ping shows success (green dot) or failure (red dot)
- [ ] Validate shows success/error feedback text
- [ ] Settings persist and load from API on mount

---

## Validation

1. Screenshot Settings — verify two card sections
2. Click "Ping" — verify status dot updates
3. Enter API key + click "Validate" — verify feedback message
4. Click "Save" — verify persistence
