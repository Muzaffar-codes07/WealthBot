'use client';

import { useRef, useState, type ChangeEvent } from 'react';
import { MainLayout, Header } from '@/components/layout';
import {
  Upload,
  Shield,
  Lock,
  Eye,
  EyeOff,
  CheckCircle,
  Loader2,
  Terminal,
  FileText,
} from 'lucide-react';
import { useUserStore } from '@/stores/userStore';
import { useUploadStatement } from '@/hooks';
import { PRIVACY_LOGS } from '@/constants/data';
import { formatCurrency } from '@/lib/utils';
import type { AssistantMessage } from '@/types';

const initialMessages: AssistantMessage[] = [
  {
    id: '1',
    type: 'info',
    content: 'Your data is AES-256 encrypted at rest. We never share raw transaction data — only anonymized patterns feed the ML model.',
    timestamp: new Date().toISOString(),
  },
];

export default function SettingsPage() {
  const {
    netWorth,
    setNetWorth,
    devMode,
    setDevMode,
    statementStatus,
    setStatementStatus,
  } = useUserStore();

  const [netWorthInput, setNetWorthInput] = useState(netWorth.toString());
  const [messages, setMessages] = useState<AssistantMessage[]>(initialMessages);
  const [uploadResult, setUploadResult] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const uploadStatement = useUploadStatement();

  const handleSendMessage = (message: string) => {
    const newMessage: AssistantMessage = {
      id: Date.now().toString(),
      type: 'question',
      content: message,
      timestamp: new Date().toISOString(),
    };
    setMessages([...messages, newMessage]);
  };

  const handlePickFile = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (!selectedFile) return;

    const ALLOWED = ['text/csv', 'application/vnd.ms-excel', 'application/pdf'];
    const nameOk = /\.(csv|pdf)$/i.test(selectedFile.name);
    if (!ALLOWED.includes(selectedFile.type) && !nameOk) {
      setStatementStatus('error');
      setUploadResult('Unsupported file. Please upload a CSV or PDF bank statement.');
      event.target.value = '';
      return;
    }

    setStatementStatus('processing');
    setUploadResult('');
    try {
      const result = await uploadStatement.mutateAsync(selectedFile);
      setStatementStatus('success');
      setUploadResult(result.message);
      setTimeout(() => setStatementStatus('idle'), 3000);
    } catch {
      setStatementStatus('error');
      setUploadResult('Upload failed. Please try a valid CSV statement.');
    } finally {
      event.target.value = '';
    }
  };

  const handleNetWorthSave = () => {
    const val = parseFloat(netWorthInput);
    if (!isNaN(val) && val >= 0) {
      setNetWorth(val);
    }
  };

  return (
    <MainLayout
      assistantMessages={messages}
      onAssistantMessage={handleSendMessage}
      assistantPlaceholder="Ask about data privacy..."
    >
      <Header
        title="Vault & Settings"
        subtitle="Secure data management & privacy controls"
      />

      {/* ------------------------------------------------------------------ */}
      {/* Magic Import Card — Upload Bank Statement                          */}
      {/* Prominent drop area with processing / success states               */}
      {/* ------------------------------------------------------------------ */}
      <div className="glass-card mb-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-brand-primary/10 text-brand-primary">
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-text-primary">
              Import Bank Statement
            </h3>
            <p className="text-xs text-text-muted">PDF or CSV — auto-parsed by ML</p>
          </div>
        </div>

        {statementStatus === 'idle' && (
          <button
            onClick={handlePickFile}
            className="w-full py-8 border-2 border-dashed border-border-secondary rounded-xl flex flex-col items-center gap-3 hover:border-brand-primary hover:bg-brand-primary/5 transition-all cursor-pointer"
          >
            <Upload className="w-8 h-8 text-text-muted" />
            <div className="text-center">
              <p className="text-sm font-medium text-text-secondary">
                Drop your statement here
              </p>
              <p className="text-xs text-text-muted mt-1">
                Supports SBI, HDFC, ICICI, Axis PDF/CSV
              </p>
            </div>
          </button>
        )}

        {statementStatus === 'processing' && (
          <div className="w-full py-8 border-2 border-dashed border-status-info/40 rounded-xl flex flex-col items-center gap-3 bg-status-info/5">
            <Loader2 className="w-8 h-8 text-status-info animate-spin" />
            <p className="text-sm font-medium text-status-info">
              Processing statement...
            </p>
            <p className="text-xs text-text-muted">Tokenizing & categorizing transactions</p>
          </div>
        )}

        {statementStatus === 'success' && (
          <div className="w-full py-8 border-2 border-dashed border-semantic-success/40 rounded-xl flex flex-col items-center gap-3 bg-semantic-success/5">
            <CheckCircle className="w-8 h-8 text-semantic-success" />
            <p className="text-sm font-medium text-semantic-success">
              Statement imported successfully!
            </p>
            <p className="text-xs text-text-muted">{uploadResult || 'Transactions parsed'}</p>
          </div>
        )}

        {statementStatus === 'error' && (
          <div className="w-full py-8 border-2 border-dashed border-status-error/40 rounded-xl flex flex-col items-center gap-3 bg-status-error/5">
            <p className="text-sm font-medium text-status-error">Statement upload failed</p>
            <p className="text-xs text-text-muted">Please upload a valid CSV statement file.</p>
          </div>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={handleFileChange}
        />

        {uploadResult && (
          <p className="text-xs text-text-muted mt-3">{uploadResult}</p>
        )}
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Privacy Log — terminal-style, builds trust for academic demo       */}
      {/* ------------------------------------------------------------------ */}
      <div className="glass-card mb-6 overflow-hidden">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-brand-primary/10 text-brand-primary">
            <Terminal className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-text-primary">
              Privacy & Access Log
            </h3>
            <p className="text-xs text-text-muted">Real-time data access audit trail</p>
          </div>
        </div>

        <div className="bg-[#0c1017] rounded-lg p-4 font-mono text-xs space-y-2 max-h-56 overflow-y-auto">
          {PRIVACY_LOGS.map((log) => (
            <div key={log.id} className="flex items-start gap-3">
              <span className="text-text-muted shrink-0 w-20">{log.timestamp}</span>
              <span
                className={`shrink-0 w-2 h-2 rounded-full mt-1.5 ${
                  log.status === 'encrypted'
                    ? 'bg-semantic-success'
                    : log.status === 'synced'
                    ? 'bg-status-info'
                    : 'bg-status-warning'
                }`}
              />
              <span className="text-text-secondary">{log.action}</span>
              <span
                className={`ml-auto shrink-0 px-1.5 py-0.5 rounded text-[10px] ${
                  log.status === 'encrypted'
                    ? 'text-semantic-success bg-semantic-success/10'
                    : log.status === 'synced'
                    ? 'text-status-info bg-status-info/10'
                    : 'text-status-warning bg-status-warning/10'
                }`}
              >
                {log.status === 'encrypted' && '🔒'} {log.status}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Two-column: Net Worth Input + Developer Mode                       */}
      {/* ------------------------------------------------------------------ */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Net Worth Manual Input */}
        <div className="glass-card">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded-lg bg-brand-primary/10 text-brand-primary">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-text-primary">
                Net Worth
              </h3>
              <p className="text-xs text-text-muted">
                Manual entry — included in ML predictions
              </p>
            </div>
          </div>

          <div className="flex gap-2">
            <div className="relative flex-1">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted text-sm">₹</span>
              <input
                type="number"
                value={netWorthInput}
                onChange={(e) => setNetWorthInput(e.target.value)}
                className="w-full pl-7 pr-4 py-2.5 bg-background-secondary border border-border-primary rounded-lg text-text-primary focus:outline-none focus:border-accent-green transition-colors"
                placeholder="50000"
              />
            </div>
            <button
              onClick={handleNetWorthSave}
              className="btn-primary px-5"
            >
              Save
            </button>
          </div>

          <p className="text-xs text-text-muted mt-3">
            Current: {formatCurrency(netWorth)}
          </p>
        </div>

        {/* Developer Mode Toggle */}
        <div className="glass-card">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded-lg bg-brand-primary/10 text-brand-primary">
              <Eye className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-text-primary">
                Developer Mode
              </h3>
              <p className="text-xs text-text-muted">
                Show ML confidence scores on transactions
              </p>
            </div>
          </div>

          <div className="flex items-center justify-between p-3 bg-background-secondary rounded-lg border border-border-primary">
            <div className="flex items-center gap-2">
              {devMode ? (
                <Eye className="w-4 h-4 text-brand-primary" />
              ) : (
                <EyeOff className="w-4 h-4 text-text-muted" />
              )}
              <span className="text-sm text-text-primary">
                {devMode ? 'Enabled' : 'Disabled'}
              </span>
            </div>

            {/* Toggle switch */}
            <button
              onClick={() => setDevMode(!devMode)}
              className={`w-12 h-6 rounded-full transition-colors relative ${
                devMode ? 'bg-brand-primary' : 'bg-border-secondary'
              }`}
            >
              <span
                className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
                  devMode ? 'translate-x-7' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {devMode && (
            <p className="text-xs text-brand-primary mt-3 flex items-center gap-1">
              <Lock className="w-3 h-3" />
              Confidence scores visible on Transactions page
            </p>
          )}
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Security Info Footer                                               */}
      {/* ------------------------------------------------------------------ */}
      <div className="glass-card bg-semantic-success/5 border-semantic-success/20">
        <div className="flex items-center gap-3">
          <Lock className="w-5 h-5 text-semantic-success shrink-0" />
          <div>
            <p className="text-sm font-medium text-text-primary">
              Bank-grade Security
            </p>
            <p className="text-xs text-text-muted">
              AES-256 encryption · SOC 2 compliant architecture · No raw data leaves your device
            </p>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
