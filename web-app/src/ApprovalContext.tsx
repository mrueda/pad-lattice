import {useEffect, useState} from 'react';
import {ShieldAlert} from 'lucide-react';
import {desktopRequest} from './desktop';

interface Approval {
  kind: 'command' | 'file_change';
  command?: string;
  reason?: string;
  cwd?: string;
  grantRoot?: string;
  truncated: boolean;
  additional_permissions: boolean;
  agent_label?: string;
}
interface ApprovalStatus {approval: Approval | null; slot: number | null; revision: number | null; pending_count?: number; child_attention_count?: number}

export function ApprovalContext({slot, revision, enabled}: {slot: number | null; revision: number | null; enabled: boolean}) {
  const [status, setStatus] = useState<ApprovalStatus | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  useEffect(() => {
    setStatus(null);
    setUnavailable(false);
    if (!enabled || slot === null || revision === null) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const next = await desktopRequest<ApprovalStatus>('approval_status');
        if (!stopped) {setStatus(next); setUnavailable(false);}
      } catch {if (!stopped) {setStatus(null); setUnavailable(true);}}
      if (!stopped) timer = setTimeout(poll, 700);
    };
    void poll();
    return () => {stopped = true; clearTimeout(timer);};
  }, [enabled, slot, revision]);
  if (!enabled) return null;
  if (status?.slot === slot && status.revision === revision && (status.pending_count ?? 0) > 1) {
    return <p className="desktopNotice approvalFallback" role="status">{status.pending_count} requests need attention
      {(status.child_attention_count ?? 0) > 0 ? ', including child agents' : ''}. Review them in Codex; Approve and Reject stay unavailable until only one request remains.</p>;
  }
  if (unavailable || status && status.slot === slot && status.revision === revision && !status.approval) {
    return <p className="desktopNotice approvalFallback" role="status">Approval details are unavailable. Review the request in Codex before deciding.</p>;
  }
  if (!status?.approval || status.slot !== slot || status.revision !== revision) return null;
  const approval = status.approval;
  const incomplete = approval.kind === 'file_change' || !approval.command || approval.truncated || approval.additional_permissions;
  return <section className="approvalContext" aria-label="Approval request">
    <div className="sectionTitle"><span><ShieldAlert aria-hidden="true" /> APPROVAL REQUEST</span></div>
    <strong>{approval.kind === 'command' ? 'Run a command' : 'File changes'}</strong>
    {approval.agent_label ? <p><small>Child agent</small> {approval.agent_label}</p> : null}
    {approval.command ? <pre><code>{approval.command}</code></pre> : null}
    {approval.reason ? <p>{approval.reason}</p> : null}
    {approval.cwd ? <p><small>Working folder</small><code>{approval.cwd}</code></p> : null}
    {approval.grantRoot ? <p><small>Requested write access</small><code>{approval.grantRoot}</code></p> : null}
    {incomplete ? <p className="approvalWarning">Full details are not shown here. Review the request in Codex before deciding.</p>
      : <p className="desktopNotice">Review in Codex if you need more context.</p>}
  </section>;
}
