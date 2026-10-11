import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { growHeard, isFinishedUtterance, joinHeard, readElsaaResult, type SpeechEvent } from "../features/speech/browser-stt.ts";
import { correctTranscript } from "../features/speech/transcript-correct.ts";

function event(parts: Array<{ text: string; isFinal: boolean }>): SpeechEvent {
  const results = parts.map((part) => ({
    isFinal: part.isFinal,
    0: { transcript: part.text },
  }));
  return { resultIndex: 0, results: Object.assign(results, { length: results.length }) };
}

describe("ELSAA speech result reader", () => {
  it("keeps Chrome words as-is from every result", () => {
    const heard = readElsaaResult(
      event([
        { text: "I built a retrieval system", isFinal: true },
        { text: " for the research lab", isFinal: false },
      ]),
    );
    assert.equal(heard.finals, "I built a retrieval system");
    assert.equal(heard.interim, "for the research lab");
    assert.equal(heard.heard, "I built a retrieval system for the research lab");
  });

  it("uses interim only before anything is final, like ELSAA", () => {
    const heard = readElsaaResult(event([{ text: "machine learning models", isFinal: false }]));
    assert.equal(heard.shown, "machine learning models");
    assert.equal(heard.finals, "");
  });

  it("joins finished utterances without dropping words", () => {
    assert.equal(
      joinHeard("I built a retrieval system", "for the research lab"),
      "I built a retrieval system for the research lab",
    );
    assert.equal(joinHeard("I used Python", "I used Python"), "I used Python");
    assert.equal(joinHeard("I used Python pandas", "pandas"), "I used Python pandas");
  });

  it("merges overlapping Chrome restarts instead of repeating words", () => {
    assert.equal(
      joinHeard("I have experience with python", "with python and SQL"),
      "I have experience with python and SQL",
    );
    assert.equal(
      joinHeard("I used Python", "I used Python and pandas"),
      "I used Python and pandas",
    );
    assert.equal(growHeard("I used Python and pandas", ""), "I used Python and pandas");
    assert.equal(growHeard("I used Python", "and pandas"), "I used Python and pandas");
  });
});

describe("finished-utterance skip phrases", () => {
  it("only auto-advances a short skip phrase, not a longer answer", () => {
    assert.equal(isFinishedUtterance("I don't know"), true);
    assert.equal(isFinishedUtterance("Can you skip that question"), true);
    assert.equal(isFinishedUtterance("next question"), true);
    assert.equal(isFinishedUtterance("I am not sure about the retrieval details so I used BM25"), false);
    assert.equal(isFinishedUtterance("I pass the output to the next layer"), false);
  });
});

describe("resume and JD transcript correction", () => {
  it("turns Rak into RAG without rewriting the rest", () => {
    assert.equal(
      correctTranscript("I used Rak for retrieval", ["RAG", "Python"]),
      "I used RAG for retrieval",
    );
  });

  it("fixes lang graph when LangGraph is on the resume", () => {
    assert.equal(
      correctTranscript("I built this with lang graph", ["LangGraph", "FastAPI"]),
      "I built this with LangGraph",
    );
  });

  it("leaves ordinary words alone", () => {
    assert.equal(correctTranscript("I can use Python when they ask", ["Python", "SQL"]), "I can use Python when they ask");
  });

  it("fixes a word NLP is sure is wrong in context", () => {
    assert.equal(correctTranscript("I used rack for retrieval", ["RAG", "Python"]), "I used RAG for retrieval");
    assert.equal(
      correctTranscript("The retrival pipeline improved recall", ["RAG"]),
      "The retrieval pipeline improved recall",
    );
  });

  it("does not rewrite a plausible English word", () => {
    assert.equal(correctTranscript("I sat on a rock by the table", ["RAG"]), "I sat on a rock by the table");
    assert.equal(correctTranscript("I bought a rack yesterday", ["RAG"]), "I bought a rack yesterday");
  });
});
