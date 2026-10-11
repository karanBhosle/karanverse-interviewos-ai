const SHORT_FORMS: Record<string, string> = {
  "retrieval augmented generation": "RAG",
  "large language models": "LLMs",
  "generative ai": "GenAI",
  "natural language processing": "NLP",
  langgraph: "LangGraph",
  langchain: "LangChain",
  fastapi: "FastAPI",
  pytorch: "PyTorch",
  tensorflow: "TensorFlow",
  numpy: "NumPy",
  "scikit-learn": "scikit-learn",
  "hugging face": "Hugging Face",
  openai: "OpenAI",
  pinecone: "Pinecone",
  bm25: "BM25",
};

const STT_ALIASES: Record<string, string> = {
  rak: "RAG",
  ragg: "RAG",
  wrag: "RAG",
  "are ag": "RAG",
  "ar ag": "RAG",
  rag: "RAG",
  "lang graph": "LangGraph",
  langraft: "LangGraph",
  "land graph": "LangGraph",
  "lang grap": "LangGraph",
  "lang chain": "LangChain",
  "long chain": "LangChain",
  "pine cone": "Pinecone",
  "bm 25": "BM25",
  "bm twenty five": "BM25",
  "pie torch": "PyTorch",
  "py torch": "PyTorch",
  "tensor flow": "TensorFlow",
  "fast api": "FastAPI",
  "open ai": "OpenAI",
  "hugging face": "Hugging Face",
  "num pie": "NumPy",
  "num py": "NumPy",
  numpi: "NumPy",
  "pan does": "pandas",
  "sci kit learn": "scikit-learn",
  "skill learn": "scikit-learn",
  "jen ai": "GenAI",
  "gen ai": "GenAI",
  "l l m": "LLM",
  "el el em": "LLM",
};

const DOMAIN_CUES = new Set([
  "retrieval",
  "retriever",
  "search",
  "generation",
  "embedding",
  "embeddings",
  "vector",
  "pipeline",
  "index",
  "chunk",
  "chunks",
  "prompt",
  "token",
  "tokens",
  "context",
  "augmented",
  "hybrid",
  "semantic",
  "similarity",
  "transformer",
  "inference",
  "dataset",
  "accuracy",
  "recall",
  "precision",
  "latency",
  "api",
  "model",
  "models",
]);

const ENGLISH_FIXES: Record<string, string> = {
  retrival: "retrieval",
  retrievel: "retrieval",
  retreival: "retrieval",
  embedings: "embeddings",
  embeding: "embedding",
  pipelne: "pipeline",
  databse: "database",
  langauge: "language",
  algoritm: "algorithm",
  algorithim: "algorithm",
  accuray: "accuracy",
  precison: "precision",
  inferance: "inference",
  deployement: "deployment",
  architecure: "architecture",
  knowlege: "knowledge",
  experiance: "experience",
  performace: "performance",
  evalution: "evaluation",
};

const COMMON = new Set([
  "the",
  "and",
  "for",
  "was",
  "with",
  "that",
  "this",
  "from",
  "have",
  "been",
  "they",
  "them",
  "then",
  "when",
  "what",
  "your",
  "our",
  "can",
  "will",
  "just",
  "like",
  "also",
  "used",
  "use",
  "using",
  "built",
  "build",
  "work",
  "worked",
  "project",
  "system",
  "data",
  "model",
  "models",
  "did",
  "had",
  "has",
  "are",
  "you",
  "not",
  "but",
  "all",
  "any",
  "out",
  "how",
  "why",
  "who",
  "i",
  "me",
  "my",
  "we",
  "it",
  "in",
  "on",
  "to",
  "of",
  "as",
  "if",
  "or",
  "so",
  "at",
  "by",
  "an",
  "be",
  "is",
  "do",
  "about",
  "because",
  "before",
  "could",
  "into",
  "more",
  "other",
  "some",
  "their",
  "there",
  "these",
  "those",
  "through",
  "would",
  "experience",
  "implemented",
  "improved",
  "problem",
  "result",
  "should",
  "something",
  "retrieval",
  "pipeline",
  "database",
  "language",
  "algorithm",
  "accuracy",
  "precision",
  "inference",
  "deployment",
  "architecture",
  "knowledge",
  "performance",
  "evaluation",
  "embedding",
  "embeddings",
  "vector",
  "search",
  "generation",
  "service",
  "rock",
  "rack",
  "table",
  "sat",
]);

const WORD = /[A-Za-z][A-Za-z0-9+.#/-]*/g;

export const CORE_SPEECH_TERMS = [
  "RAG",
  "LangGraph",
  "LangChain",
  "FastAPI",
  "PyTorch",
  "TensorFlow",
  "NumPy",
  "pandas",
  "LLM",
  "LLMs",
  "GenAI",
  "Python",
  "SQL",
  "BM25",
  "OpenAI",
  "Hugging Face",
];

function fold(value: string) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9+.#/\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function levenshtein(left: string, right: string) {
  if (left === right) return 0;
  if (!left) return right.length;
  if (!right) return left.length;
  const previous = Array.from({ length: right.length + 1 }, (_, index) => index);
  for (let i = 0; i < left.length; i += 1) {
    const current = [i + 1];
    for (let j = 0; j < right.length; j += 1) {
      current[j + 1] = Math.min(
        previous[j + 1] + 1,
        current[j] + 1,
        previous[j] + (left[i] === right[j] ? 0 : 1),
      );
    }
    previous.splice(0, previous.length, ...current);
  }
  return previous[right.length];
}

function catalogFor(terms: string[]) {
  const catalog = new Map<string, string>();
  const allowed = new Set(terms.map((term) => fold(term)));
  for (const term of terms) catalog.set(fold(term), SHORT_FORMS[fold(term)] || term);
  for (const [alias, display] of Object.entries(STT_ALIASES)) {
    if (allowed.has(fold(display)) || terms.includes(display)) catalog.set(alias, display);
  }
  return catalog;
}

function soundex(value: string) {
  const letters = value.toLowerCase().replace(/[^a-z]/g, "");
  if (!letters) return "";
  const groups: Record<string, string> = {
    bfpv: "1",
    cgjkqsxz: "2",
    dt: "3",
    l: "4",
    mn: "5",
    r: "6",
  };
  const code = (char: string) => {
    for (const [group, digit] of Object.entries(groups)) {
      if (group.includes(char)) return digit;
    }
    return "";
  };
  let key = letters[0].toUpperCase();
  let previous = code(letters[0]);
  for (const char of letters.slice(1)) {
    const digit = code(char);
    if (digit && digit !== previous) key += digit;
    previous = digit;
    if (key.length === 4) break;
  }
  return key.padEnd(4, "0");
}

function isWord(token: string, catalog: Map<string, string>) {
  const key = fold(token);
  if (COMMON.has(key) || catalog.has(key)) return true;
  if (key.endsWith("s") && COMMON.has(key.slice(0, -1))) return true;
  return false;
}

function uniqueClose(heard: string, options: string[], limit: number) {
  const key = fold(heard);
  const hits = [...new Set(options.filter((item) => {
    const distance = levenshtein(key, fold(item));
    return distance > 0 && distance <= limit;
  }))];
  return hits.length === 1 ? hits[0] : null;
}

function nlpGuess(phrase: string, catalog: Map<string, string>, nearby: string[]) {
  const key = fold(phrase);
  if (ENGLISH_FIXES[key]) return ENGLISH_FIXES[key];
  const exact = catalog.get(key);
  if (exact) return exact;
  const known = isWord(phrase, catalog);
  const domain = nearby.some((item) => DOMAIN_CUES.has(item));
  if (known && !domain && COMMON.has(key)) return null;
  const sound = soundex(key);
  const soundHits = [
    ...new Set(
      [...catalog.entries()]
        .filter(([term, display]) => !term.includes(" ") && soundex(term) === sound && fold(display) !== key)
        .map(([, display]) => display),
    ),
  ];
  if (soundHits.length === 1 && (!known || domain)) return soundHits[0];
  if (!known) {
    const closeTerm = uniqueClose(phrase, [...catalog.values()], key.length <= 6 ? 1 : 2);
    if (closeTerm) return closeTerm;
    if (key.length >= 6) {
      const englishHit = uniqueClose(phrase, [...COMMON, ...Object.values(ENGLISH_FIXES)], 1);
      if (englishHit) return englishHit;
    }
  }
  if (domain) {
    const closeTerm = uniqueClose(phrase, [...catalog.values()], key.length <= 5 ? 1 : 2);
    if (closeTerm) return closeTerm;
    return fuzzy(phrase, catalog);
  }
  if (!known) return fuzzy(phrase, catalog);
  return null;
}

function fuzzy(heard: string, catalog: Map<string, string>) {
  const key = fold(heard);
  const exact = catalog.get(key);
  if (exact) return exact;
  if (COMMON.has(key) || key.length < 3) return null;
  let best: { distance: number; display: string } | null = null;
  for (const [term, display] of catalog) {
    if (term.includes(" ") || term.length < 3 || COMMON.has(term)) continue;
    const distance = levenshtein(key, term);
    const limit = Math.min(key.length, term.length) <= 5 ? 1 : 2;
    if (distance > 0 && distance <= limit && (!best || distance < best.distance)) {
      best = { distance, display };
    }
  }
  return best?.display ?? null;
}

export function correctTranscript(text: string, terms: string[] = CORE_SPEECH_TERMS) {
  const source = text || "";
  if (!source.trim()) return source;
  const lexicon = terms.length ? terms : CORE_SPEECH_TERMS;
  const catalog = catalogFor(lexicon);
  const matches = [...source.matchAll(WORD)];
  if (!matches.length) return source;
  const used = new Set<number>();
  const swaps: Array<{ start: number; end: number; display: string }> = [];
  for (const width of [3, 2, 1]) {
    for (let index = 0; index <= matches.length - width; index += 1) {
      if ([...Array(width)].some((_, offset) => used.has(index + offset))) continue;
      const phrase = matches
        .slice(index, index + width)
        .map((item) => item[0])
        .join(" ");
      let display = catalog.get(fold(phrase)) ?? null;
      if (!display && width === 1) {
        const nearby = [-2, -1, 1, 2]
          .map((offset) => matches[index + offset]?.[0])
          .filter(Boolean)
          .map((item) => fold(item));
        display = nlpGuess(phrase, catalog, nearby);
      } else if (!display) {
        display = STT_ALIASES[fold(phrase)] ?? null;
      }
      if (!display || display === phrase) continue;
      const first = matches[index];
      const last = matches[index + width - 1];
      swaps.push({ start: first.index ?? 0, end: (last.index ?? 0) + last[0].length, display });
      for (let offset = 0; offset < width; offset += 1) used.add(index + offset);
    }
  }
  if (!swaps.length) return source;
  let cursor = 0;
  let output = "";
  for (const swap of swaps.sort((left, right) => left.start - right.start)) {
    output += source.slice(cursor, swap.start) + swap.display;
    cursor = swap.end;
  }
  return output + source.slice(cursor);
}
