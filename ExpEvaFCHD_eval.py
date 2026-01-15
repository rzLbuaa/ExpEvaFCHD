
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ExpEvaFCHD Text Evaluation

This script computes five automated metrics between a generated report and an expert report:
  1) Semantic cosine similarity (sentence-embedding cosine)
  2) TF–IDF cosine similarity
  3) Relevance (cross-encoder / embedding fallback) in [0, 1]
  4) Informativeness (LM surprisal proxy) in [0, 1]
  5) Validity (NLI entailment probability) in [0, 1]

Example:
  python expeva_text_eval_review.py --gold_file gold.txt --gen_file gen.txt

Batch:
  python expeva_text_eval_review.py --input results.xlsx --output scored.xlsx
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
from sklearn.feature_extraction.text import TfidfVectorizer
from transformers import AutoModelForCausalLM, AutoModelForSequenceClassification, AutoTokenizer

try:
    from sentence_transformers import SentenceTransformer, CrossEncoder
except Exception:  # pragma: no cover
    SentenceTransformer = None  # type: ignore
    CrossEncoder = None  # type: ignore


# -----------------------------
# Utils
# -----------------------------

_SENT_SPLIT_RE = re.compile(r"(?<=[。！？.!?])\s+")


def set_determinism(seed: int = 42) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def read_text(maybe_path: str) -> str:
    p = Path(maybe_path)
    if p.exists() and p.is_file():
        return p.read_text(encoding="utf-8", errors="ignore").strip()
    return str(maybe_path).strip()


def split_sentences(text: str) -> List[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    parts = _SENT_SPLIT_RE.split(text)
    parts = [p.strip() for p in parts if p and p.strip()]
    return parts if parts else [text]


def cosine(u: np.ndarray, v: np.ndarray, eps: float = 1e-12) -> float:
    nu = float(np.linalg.norm(u))
    nv = float(np.linalg.norm(v))
    if nu < eps or nv < eps:
        return 0.0
    return float(np.dot(u, v) / (nu * nv))


# -----------------------------
# Models
# -----------------------------

@dataclass
class ModelConfig:
    device: str
    embed_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    cross_encoder: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    nli_model: str = "roberta-large-mnli"
    lm_model: str = "gpt2"  # proxy for informativeness


class Embedder:
    def __init__(self, cfg: ModelConfig):
        if SentenceTransformer is None:
            raise ImportError("sentence-transformers is required for semantic similarity.")
        self.model = SentenceTransformer(cfg.embed_model, device=cfg.device)

    def encode_doc(self, text: str) -> np.ndarray:
        sents = split_sentences(text)
        if not sents:
            return np.zeros((384,), dtype=np.float32)
        emb = self.model.encode(sents, convert_to_numpy=True, normalize_embeddings=True)
        return emb.mean(axis=0)


class RelevanceScorer:
    """
    Prefer a cross-encoder relevance model; fall back to embedding cosine mapped to [0,1].
    """
    def __init__(self, cfg: ModelConfig, embedder: Optional[Embedder] = None):
        self.cfg = cfg
        self.embedder = embedder
        self.ce = None
        if CrossEncoder is not None:
            try:
                self.ce = CrossEncoder(cfg.cross_encoder, device=cfg.device)
            except Exception:
                self.ce = None

    def score(self, gold: str, gen: str) -> float:
        if self.ce is not None:
            # Cross-encoders usually output unbounded scores; map via sigmoid.
            raw = float(self.ce.predict([(gold, gen)])[0])
            return float(1.0 / (1.0 + math.exp(-raw)))
        # Fallback: cosine in [-1,1] -> [0,1]
        if self.embedder is None:
            return 0.0
        c = cosine(self.embedder.encode_doc(gold), self.embedder.encode_doc(gen))
        return float(max(0.0, min(1.0, (c + 1.0) / 2.0)))


class NLIScorer:
    """
    Validity = entailment probability P(E) from an NLI model,
    using gold as premise and generated as hypothesis.
    """
    def __init__(self, cfg: ModelConfig):
        self.tokenizer = AutoTokenizer.from_pretrained(cfg.nli_model)
        self.model = AutoModelForSequenceClassification.from_pretrained(cfg.nli_model)
        self.model.to(cfg.device)
        self.model.eval()
        self.device = cfg.device
        # Try to infer entailment label id robustly
        self.entail_id = None
        if hasattr(self.model.config, "label2id") and self.model.config.label2id:
            for k, v in self.model.config.label2id.items():
                if k.lower().startswith("entail"):
                    self.entail_id = int(v)
        if self.entail_id is None:
            # Common MNLI ordering: contradiction, neutral, entailment
            self.entail_id = 2

    @torch.no_grad()
    def entailment_prob(self, premise: str, hypothesis: str) -> float:
        inputs = self.tokenizer(
            premise, hypothesis, truncation=True, padding=True,
            max_length=512, return_tensors="pt"
        ).to(self.device)
        logits = self.model(**inputs).logits
        probs = torch.softmax(logits, dim=-1).detach().cpu().numpy()[0]
        return float(probs[self.entail_id])


class InformativenessScorer:
    """
    Proxy informativeness via average negative log-likelihood (surprisal) under a small LM.

    Intuition: extremely templated/generic text tends to have lower surprisal under a general LM.
    We map surprisal to [0,1] via a bounded transform:
        info = 1 - exp(-surprisal / c)
    where c is a scaling constant (default 5.0).
    """
    def __init__(self, cfg: ModelConfig, scale: float = 5.0):
        self.tokenizer = AutoTokenizer.from_pretrained(cfg.lm_model)
        self.model = AutoModelForCausalLM.from_pretrained(cfg.lm_model)
        self.model.to(cfg.device)
        self.model.eval()
        self.device = cfg.device
        self.scale = float(scale)

    @torch.no_grad()
    def score(self, text: str) -> float:
        text = (text or "").strip()
        if not text:
            return 0.0
        enc = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512).to(self.device)
        out = self.model(**enc, labels=enc["input_ids"])
        # loss is mean cross-entropy over tokens
        loss = float(out.loss.detach().cpu().item())
        surprisal = max(0.0, loss)
        val = 1.0 - math.exp(-surprisal / max(self.scale, 1e-6))
        return float(max(0.0, min(1.0, val)))


# -----------------------------
# Metrics
# -----------------------------

def semantic_cosine_similarity(embedder: Embedder, gold: str, gen: str) -> float:
    return cosine(embedder.encode_doc(gold), embedder.encode_doc(gen))


def tfidf_cosine_similarity(gold: str, gen: str) -> float:
    gold = gold or ""
    gen = gen or ""
    vect = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    X = vect.fit_transform([gold, gen]).toarray()
    return cosine(X[0], X[1])


# -----------------------------
# Evaluation
# -----------------------------

@dataclass
class EvalResult:
    cosine: float
    cosine_tfidf: float
    relevance: float
    informativeness: float
    validity: float

    def as_dict(self) -> Dict[str, float]:
        return {
            "Cosine": self.cosine,
            "CosineTI": self.cosine_tfidf,
            "Relevance": self.relevance,
            "Informativeness": self.informativeness,
            "Validity": self.validity,
        }


class Evaluator:
    def __init__(self, cfg: ModelConfig):
        self.embedder = Embedder(cfg)
        self.relevance = RelevanceScorer(cfg, embedder=self.embedder)
        self.nli = NLIScorer(cfg)
        self.info = InformativenessScorer(cfg)

    def evaluate_pair(self, gold: str, gen: str) -> EvalResult:
        c = semantic_cosine_similarity(self.embedder, gold, gen)
        cti = tfidf_cosine_similarity(gold, gen)
        rel = self.relevance.score(gold, gen)
        info = self.info.score(gen)
        val = self.nli.entailment_prob(gold, gen)
        return EvalResult(c, cti, rel, info, val)


# -----------------------------
# IO: batch mode
# -----------------------------

def load_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in [".xlsx", ".xls"]:
        return pd.read_excel(path)
    if path.suffix.lower() in [".csv"]:
        return pd.read_csv(path)
    raise ValueError(f"Unsupported input type: {path.suffix}")


def save_table(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() in [".xlsx", ".xls"]:
        df.to_excel(path, index=False)
    elif path.suffix.lower() in [".csv"]:
        df.to_csv(path, index=False)
    else:
        raise ValueError(f"Unsupported output type: {path.suffix}")


def infer_text_columns(df: pd.DataFrame) -> Tuple[str, str]:
    cols = [c.lower() for c in df.columns]
    # Prefer explicit names if present
    for g in ["gold", "t_gold", "expert", "expert_text"]:
        if g in cols:
            gold_col = df.columns[cols.index(g)]
            break
    else:
        gold_col = df.columns[0]

    for g in ["gen", "t_gen", "generated", "model_text"]:
        if g in cols:
            gen_col = df.columns[cols.index(g)]
            break
    else:
        # fall back to second column if available
        gen_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
    return gold_col, gen_col


# -----------------------------
# CLI
# -----------------------------

def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="ExpEvaFCHD Text Evaluation (Review Version)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")

    p.add_argument("--gold", type=str, default=None, help="Gold text (or a path).")
    p.add_argument("--gen", type=str, default=None, help="Generated text (or a path).")
    p.add_argument("--gold_file", type=str, default=None, help="Path to gold text file.")
    p.add_argument("--gen_file", type=str, default=None, help="Path to generated text file.")

    p.add_argument("--input", type=str, default=None, help="Batch input .xlsx/.csv containing gold/gen columns.")
    p.add_argument("--output", type=str, default=None, help="Batch output .xlsx/.csv with metric columns added.")
    p.add_argument("--gold_col", type=str, default=None, help="Gold column name for batch.")
    p.add_argument("--gen_col", type=str, default=None, help="Generated column name for batch.")

    p.add_argument("--json", action="store_true", help="Print single-pair results as JSON.")
    return p


def main() -> None:
    args = build_argparser().parse_args()
    set_determinism(args.seed)

    cfg = ModelConfig(device=args.device)
    evaluator = Evaluator(cfg)

    # Batch mode
    if args.input:
        in_path = Path(args.input)
        df = load_table(in_path)

        gold_col, gen_col = infer_text_columns(df)
        if args.gold_col:
            gold_col = args.gold_col
        if args.gen_col:
            gen_col = args.gen_col

        # Ensure columns exist
        if gold_col not in df.columns or gen_col not in df.columns:
            raise KeyError(f"Missing columns: gold_col={gold_col}, gen_col={gen_col}")

        metrics = []
        for _, row in df.iterrows():
            gold = "" if pd.isna(row[gold_col]) else str(row[gold_col])
            gen = "" if pd.isna(row[gen_col]) else str(row[gen_col])
            res = evaluator.evaluate_pair(gold, gen).as_dict()
            metrics.append(res)

        met_df = pd.DataFrame(metrics)
        out_df = pd.concat([df.reset_index(drop=True), met_df], axis=1)

        out_path = Path(args.output) if args.output else in_path.with_name(in_path.stem + "_scored" + in_path.suffix)
        save_table(out_df, out_path)
        print(str(out_path))
        return

    # Single-pair mode
    gold_text = args.gold if args.gold is not None else (args.gold_file or "")
    gen_text = args.gen if args.gen is not None else (args.gen_file or "")
    gold = read_text(gold_text) if gold_text else ""
    gen = read_text(gen_text) if gen_text else ""

    if not gold and not gen:
        raise ValueError("Provide --gold/--gen (or --gold_file/--gen_file), or --input for batch mode.")

    res = evaluator.evaluate_pair(gold, gen).as_dict()
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        for k, v in res.items():
            print(f"{k}: {v:.6f}")


if __name__ == "__main__":
    main()
