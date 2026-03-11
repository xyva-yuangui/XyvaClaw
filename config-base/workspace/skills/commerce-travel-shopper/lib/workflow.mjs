export const STATES = {
  COLLECTING: "COLLECTING",
  ANALYZING: "ANALYZING",
  RANKED: "RANKED",
  DRAFT_READY: "DRAFT_READY",
  WAIT_CONFIRM_SUBMIT: "WAIT_CONFIRM_SUBMIT",
  WAIT_CONFIRM_PAY: "WAIT_CONFIRM_PAY",
  DONE: "DONE",
  ABORTED: "ABORTED",
};

export const TERMINAL_STATES = new Set([STATES.DONE, STATES.ABORTED]);

const SEQUENCE = [
  STATES.COLLECTING,
  STATES.ANALYZING,
  STATES.RANKED,
  STATES.DRAFT_READY,
  STATES.WAIT_CONFIRM_SUBMIT,
  STATES.WAIT_CONFIRM_PAY,
  STATES.DONE,
];

export function canMoveTo(from, to) {
  if (to === STATES.ABORTED) return true;
  if (from === to) return true;
  const fi = SEQUENCE.indexOf(from);
  const ti = SEQUENCE.indexOf(to);
  return fi >= 0 && ti >= 0 && ti === fi + 1;
}

export function assertTransition(from, to) {
  if (!canMoveTo(from, to)) {
    throw new Error(`invalid transition: ${from} -> ${to}`);
  }
}

export function nextState(from) {
  if (from === STATES.WAIT_CONFIRM_SUBMIT || from === STATES.WAIT_CONFIRM_PAY || TERMINAL_STATES.has(from)) {
    return from;
  }
  const idx = SEQUENCE.indexOf(from);
  if (idx < 0 || idx >= SEQUENCE.length - 1) return from;
  return SEQUENCE[idx + 1];
}
