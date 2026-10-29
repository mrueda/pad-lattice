import {useCallback, useEffect, useRef, useState} from 'react';
import {CircleHelp, Send} from 'lucide-react';
import {desktopRequest} from './desktop';

interface Question {
  id: string;
  header: string;
  question: string;
  options: {label: string; description: string}[];
}
interface PendingQuestion {token: string; questions: Question[]}
interface QuestionStatus {question: PendingQuestion | null; slot: number | null; revision: number | null}
type QuestionRequest = (operation: 'status' | 'answer', params?: object) => Promise<unknown>;
const desktopQuestionRequest: QuestionRequest = (operation, params) => desktopRequest(operation === 'status' ? 'question_status' : 'answer_question', params);

export function LiveCodexQuestion({slot, revision, enabled, sessionName, request = desktopQuestionRequest}: {slot: number | null; revision: number | null; enabled: boolean; sessionName?: string; request?: QuestionRequest}) {
  const [status, setStatus] = useState<QuestionStatus | null>(null);
  const [tooLarge, setTooLarge] = useState(false);
  useEffect(() => {
    setStatus(null);
    setTooLarge(false);
    if (!enabled || slot === null || revision === null) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const next = await request('status') as QuestionStatus;
        if (!stopped) {setStatus(next); setTooLarge(false);}
      } catch (reason) {if (!stopped) {setStatus(null); setTooLarge(String(reason).includes('message exceeds size limit'));}}
      if (!stopped) timer = setTimeout(poll, 700);
    };
    void poll();
    return () => {stopped = true; clearTimeout(timer);};
  }, [enabled, slot, revision, request]);
  if (enabled && tooLarge) return <p className="desktopNotice" role="status">This question is too long for this surface. Answer it in Codex.</p>;
  if (!enabled || !status?.question || status.slot !== slot || status.revision !== revision) return null;
  const current = status;
  return <QuestionForm key={current.question!.token} question={current.question!} sessionName={sessionName} slot={slot} onSubmit={async answers => {
    await request('answer', {slot: current.slot, revision: current.revision,
      token: current.question!.token, answers});
    setStatus(null);
  }} />;
}

export function DemoCodexQuestion() {
  const [open, setOpen] = useState(false);
  const [done, setDone] = useState(false);
  const sample: PendingQuestion = {token: 'sample', questions: [{id: 'tests', header: 'Example',
    question: 'Which tests should I run?', options: [
      {label: 'Focused tests', description: 'Test the affected feature.'},
      {label: 'Full suite', description: 'Run all tests.'},
    ]}]};
  if (!open) return <section className="sampleQuestion"><button className="textButton" onClick={() => setOpen(true)}>
    <CircleHelp aria-hidden="true" />Try a sample Codex question</button></section>;
  return done ? <section className="sampleQuestion" role="status">Sample answer sent. No Codex session was changed.</section>
    : <QuestionForm question={sample} simulation onSubmit={async () => setDone(true)} />;
}

function QuestionForm({question, simulation = false, sessionName, slot, onSubmit}: {question: PendingQuestion; simulation?: boolean; sessionName?: string; slot?: number | null;
  onSubmit: (answers: Record<string, number>) => Promise<void>}) {
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const submitting = useRef(false);
  const single = question.questions.length === 1;
  const complete = question.questions.every(item => answers[item.id] !== undefined);
  const submit = useCallback(async (selected: Record<string, number>) => {
    if (submitting.current || !question.questions.every(item => selected[item.id] !== undefined)) return;
    submitting.current = true;
    setBusy(true); setError('');
    try {await onSubmit(selected);} catch (reason) {
      submitting.current = false;
      setBusy(false);
      setError(String(reason));
    }
  }, [onSubmit, question.questions]);
  const choose = useCallback((item: Question, index: number) => {
    if (submitting.current) return;
    if (single) {
      setAnswers({[item.id]: index});
      void submit({[item.id]: index});
    } else {
      setAnswers(previous => ({...previous, [item.id]: index}));
    }
  }, [single, submit]);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target;
      if (event.repeat || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey
        || target instanceof HTMLElement && (target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName))
        || document.querySelector('dialog[open], [role="dialog"]')) return;
      const index = Number(event.key) - 1;
      const current = question.questions.find(item => answers[item.id] === undefined) ?? question.questions[question.questions.length - 1];
      if (/^[1-9]$/.test(event.key) && index < current.options.length) {
        event.preventDefault();
        choose(current, index);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [question, answers, choose]);
  return <section className="codexQuestion" aria-label={simulation ? 'Sample Codex question' : 'Codex question'}>
    <div className="sectionTitle"><span><CircleHelp aria-hidden="true" /> {simulation ? 'SAMPLE QUESTION' : 'CODEX QUESTION'}</span>
      {simulation ? <span>SIMULATION</span> : null}</div>
    {sessionName && slot != null ? <p className="questionSession"><strong>{sessionName}</strong> · Scene {slot + 1}</p> : null}
    {question.questions.map(item => <fieldset key={item.id}>
      <legend>{item.question}</legend>
      {item.options.map((option, index) => <button type="button" className="questionOption" key={option.label}
        aria-pressed={answers[item.id] === index} disabled={busy} onClick={() => choose(item, index)}>
        <span className="questionNumber">{index + 1}</span><span><strong>{option.label}</strong>
          {option.description ? <small>{option.description}</small> : null}</span>
      </button>)}
    </fieldset>)}
    {!single ? <button className="textButton questionSubmit" disabled={!complete || busy} onClick={() => void submit(answers)}>
      <Send aria-hidden="true" />Send answer</button> : null}
    {error ? <p className="desktopError" role="alert">{error}</p> : null}
  </section>;
}
