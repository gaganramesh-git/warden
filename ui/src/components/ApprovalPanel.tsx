import type { ScenarioData } from "../types";
import { cx } from "../lib/cx";

interface Props {
  scenario: ScenarioData;
  approved: boolean;
}

// The operator's review surface: cause + counterfactual + rehearsal + the
// guardrail diff + blast radius. The approve action lives in the StepGuide; this
// panel shows what you're approving and the result.
export function ApprovalPanel({ scenario, approved }: Props) {
  const c = scenario.case;
  return (
    <div className="rounded-card border border-line bg-panel p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="font-mono text-[0.7rem] uppercase tracking-wider text-muted">Human review</span>
        {approved ? (
          <span className="rounded-full border border-verified/40 bg-verified/10 px-2 py-0.5 font-mono text-micro text-verified">
            fix approved
          </span>
        ) : (
          <span className="rounded-full border border-pending/40 bg-pending/10 px-2 py-0.5 font-mono text-micro text-pending">
            awaiting approval
          </span>
        )}
      </div>

      <dl className="space-y-2 font-mono text-micro">
        <Row label="cause" ok>
          {c.verdict.rootCauseText}
        </Row>
        <Row label="counterfactual" ok={c.verdict.counterfactual.confirmed}>
          {c.verdict.counterfactual.confirmed ? "confirmed by replay" : "unconfirmed"}
        </Row>
        <Row label="rehearsal" ok={c.rehearsal.misbehaviorCleared && c.rehearsal.taskStillCompletes}>
          attack cleared · legit task still completes
        </Row>
        <Row label="blast radius" neutral>
          {c.approval.blastRadius}
        </Row>
      </dl>

      {/* the guardrail diff, as the Cedar rule the actuator will write */}
      <div className="mt-3 overflow-x-auto rounded-[6px] border border-line bg-ink/60 p-3">
        <pre className="whitespace-pre font-mono text-[0.72rem] leading-relaxed text-fg/90">
          <span className="text-verified">+ </span>
          {c.guardrail.cedar.replace(/\n/g, "\n  ")}
        </pre>
      </div>

      {!approved ? (
        <p className="mt-3 rounded-[6px] border border-pending/30 bg-pending/[0.06] px-3 py-2 font-mono text-micro text-pending">
          review the above, then use <span className="text-fg">Approve fix → sign KEY_B</span> in the step panel
        </p>
      ) : (
        <p className="mt-3 font-mono text-micro text-muted">
          signed by <span className="text-fg">{c.approval.approver}</span> · human seal stamped over the same
          plan &amp; rehearsal
        </p>
      )}
    </div>
  );
}

function Row({
  label,
  children,
  ok,
  neutral,
}: {
  label: string;
  children: React.ReactNode;
  ok?: boolean;
  neutral?: boolean;
}) {
  return (
    <div className="flex items-start gap-2">
      <span
        className={cx(
          "mt-[3px] h-1.5 w-1.5 shrink-0 rounded-full",
          neutral ? "bg-muted" : ok ? "bg-verified" : "bg-threat"
        )}
      />
      <dt className="w-24 shrink-0 text-muted">{label}</dt>
      <dd className="flex-1 text-fg/90">{children}</dd>
    </div>
  );
}
