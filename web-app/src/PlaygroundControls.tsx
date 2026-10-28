import {Check, ChevronRight, CircleAlert, ListRestart} from 'lucide-react';
import {nextPlaygroundEvent, playgroundScenarios, type PlaygroundEvent, type PlaygroundState} from './playground';
import {tokenColor} from './surfaceModel';

export function PlaygroundAgentPicker({state, dispatch, grid = true}: {state: PlaygroundState; dispatch: (event: PlaygroundEvent) => void; grid?: boolean}) {
  const selected = state.sessions.find((item) => item.selected);
  return <section className="playgroundAgentPicker" aria-label="View agent">
    <div className="sectionTitle"><span>VIEW AGENT</span><span>{grid ? 'GRID' : 'SELECTED'}: {selected?.label ?? 'NO SELECTION'}</span></div>
    <div className="agentChoices">
      {state.sessions.map((item) => <button key={item.slot} className={`agentChoice ${item.selected ? 'selected' : ''}`}
        aria-label={`View ${item.label}`} aria-pressed={item.selected}
        onClick={() => dispatch({type: 'select', slot: item.slot, expectedRevision: state.revision})}>
        <span className="sessionAccent" aria-hidden="true" style={{background: tokenColor(`accent:${item.accent}:selected`)}} />
        <span>{item.label}</span>
      </button>)}
    </div>
  </section>;
}

export function PlaygroundControls({state, dispatch}: {state: PlaygroundState; dispatch: (event: PlaygroundEvent) => void}) {
  const next = nextPlaygroundEvent(state);
  return <section className="playgroundControls" aria-label="Scenario controls">
    <label htmlFor="playground-scenario">Scenario</label>
    <div className="scenarioPicker">
      <select id="playground-scenario" value={state.scenario}
        onChange={(event) => dispatch({type: 'scenario', id: event.target.value})}>
        {playgroundScenarios.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}
      </select>
      <button className="textButton" title="Restart scenario" aria-label="Restart scenario"
        onClick={() => dispatch({type: 'reset'})}><ListRestart aria-hidden="true" /></button>
    </div>
    {next ? <button className="textButton scenarioEvent" onClick={() => dispatch({type: 'advance'})}>
      <ChevronRight aria-hidden="true" /><span>{next.label}</span>
    </button> : null}
  </section>;
}

export function PlaygroundHistory({state}: {state: PlaygroundState}) {
  const latest = state.history.at(-1);
  return <details className="playgroundHistory">
    <summary>Activity <span>{latest?.text}</span></summary>
    <ol aria-label="Simulated activity">
      {state.history.map((entry) => <li key={entry.id}>
        {entry.blocked ? <CircleAlert aria-hidden="true" /> : <Check aria-hidden="true" />}
        <span>{entry.text}</span>
      </li>)}
    </ol>
  </details>;
}
