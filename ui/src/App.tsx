import { useState } from "react";
import { TopBar } from "./components/TopBar";
import { LeftNav, type Screen } from "./components/LeftNav";
import { CaseScreen } from "./screens/CaseScreen";
import { FleetScreen } from "./screens/FleetScreen";
import { ReportsScreen } from "./screens/ReportsScreen";
import { useDemoMachine } from "./lib/useDemoMachine";
import type { StatusKind } from "./components/ui/StatusBadge";
import { data } from "./data/loadData";
import type { Machine } from "./lib/useDemoMachine";

function topStatus(m: Machine): StatusKind {
  if (m.isRefusal) return "attack";
  if (m.reached("deployed")) return "resolved";
  if (m.reached("rehearsal")) return "sealed";
  if (m.reached("catch")) return "attack";
  return "healthy";
}

export default function App() {
  const [screen, setScreen] = useState<Screen>("case");
  const m = useDemoMachine();

  return (
    <div className="flex h-screen flex-col bg-ink text-fg">
      <TopBar status={topStatus(m)} alerts={m.reached("catch") && !m.reached("deployed") ? 1 : 0} />
      <div className="flex min-h-0 flex-1">
        <LeftNav screen={screen} onSelect={setScreen} />
        <main className="min-w-0 flex-1 overflow-hidden">
          {screen === "case" && <CaseScreen data={data} m={m} />}
          {screen === "fleet" && <FleetScreen data={data} m={m} onOpenCase={() => setScreen("case")} />}
          {screen === "reports" && <ReportsScreen data={data} />}
        </main>
      </div>
    </div>
  );
}
