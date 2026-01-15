# -*- coding: utf-8 -*-
"""
ExpEvaFCHD (review release)
Note: No patient data or private credentials are included. Set environment variables or a YAML config to run.
"""

from __future__ import annotations

import csv
import json
import math
import os
import re
import time
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import yaml

# -----------------------------------------------------------------------------
# Paths and dataset registry (tabular configuration)
# -----------------------------------------------------------------------------
# Root directory for data files. Reviewers can point this to their local copy.
DATA_ROOT = Path(os.getenv("FETALCARDIO_DATA_ROOT", "./data")).resolve()

# A single tabular registry for all retrospective monthly shards that form FetalCardioDB.
# Each row describes one file; the pipeline will load and concatenate them.
DATA_SOURCES: List[Dict[str, str]] = [
    # source_id, file, cohort, site, period, note
    {"source_id": "anzhen_2016_01", "file": "ANZHEN16year01month.xlsx", "cohort": "FetalCardioDB", "site": "XXXX Hospital", "period": "2016-01", "note": "Retrospective expert database shard."},
    {"source_id": "anzhen_2016_02", "file": "ANZHEN16year02month.xlsx", "cohort": "FetalCardioDB", "site": "XXXX Hospital", "period": "2016-02", "note": "Retrospective expert database shard."},
    {"source_id": "anzhen_2016_03", "file": "ANZHEN16year03month.xlsx", "cohort": "FetalCardioDB", "site": "XXXX Hospital", "period": "2016-03", "note": "Retrospective expert database shard."},
    {"source_id": "anzhen_2016_04", "file": "ANZHEN16year04month.xlsx", "cohort": "FetalCardioDB", "site": "XXXX Hospital", "period": "2016-04", "note": "Retrospective expert database shard."},
    {"source_id": "anzhen_2016_05", "file": "ANZHEN16year05month.xlsx", "cohort": "FetalCardioDB", "site": "XXXX Hospital", "period": "2016-05", "note": "Retrospective expert database shard."},
    {"source_id": "anzhen_2016_06", "file": "ANZHEN16year06month.xlsx", "cohort": "FetalCardioDB", "site": "XXXX Hospital", "period": "2016-06", "note": "Retrospective expert database shard."},
    {"source_id": "anzhen_2016_07", "file": "ANZHEN16year07month.xlsx", "cohort": "FetalCardioDB", "site": "XXXX Hospital", "period": "2016-07", "note": "Retrospective expert database shard."},
    {"source_id": "anzhen_2016_08", "file": "ANZHEN16year08month.xlsx", "cohort": "FetalCardioDB", "site": "XXXX Hospital", "period": "2016-08", "note": "Retrospective expert database shard."},
    {"source_id": "anzhen_2016_09", "file": "ANZHEN16year09month.xlsx", "cohort": "FetalCardioDB", "site": "XXXX Hospital", "period": "2016-09", "note": "Retrospective expert database shard."},
    {"source_id": "anzhen_2016_10", "file": "ANZHEN16year10month.xlsx", "cohort": "FetalCardioDB", "site": "XXXX Hospital", "period": "2016-10", "note": "Retrospective expert database shard."},
]

# Materialize the table as a DataFrame for readability and for potential exporting.
DATA_SOURCES_TABLE = pd.DataFrame(DATA_SOURCES)

# File paths used by the loader.
DATA_PATHS = [DATA_ROOT / row["file"] for row in DATA_SOURCES]


# ---------------- Feature Schema ----------------
NUMERIC_FEATURES = [
    "胸廓横径(mm)", "左室(mm)", "左房(mm)", "主动脉(mm)", "主动脉峡部(mm)",
    "左肺动脉(mm)", "动脉导管(mm)", "心胸面积比(%)", "心脏横径(mm)", "右室(mm)",
    "右房(mm)", "肺动脉(mm)", "降主动脉(mm)", "右肺动脉(mm)", "卵圆孔(mm)",
    "心轴(°)",
    "二尖瓣-E(cm/s)", "二尖瓣-A(cm/s)", "三尖瓣-E(cm/s)", "三尖瓣-A(cm/s)",
    "主动脉流速(cm/s)", "肺动脉流速(cm/s)", "主动脉弓-收缩(cm/s)", "主动脉弓-舒张(cm/s)",
    "动脉导管弓-收缩(cm/s)", "动脉导管弓-舒张(cm/s)", "胎心率(次/分)",
    "肺静脉-S", "肺静脉-D", "肺静脉-A", "肺静脉-PI",
    "静脉导管-S", "静脉导管-D", "静脉导管-A", "静脉导管-PI"
]
CATEGORICAL_FEATURES = ["律齐"]
ALL_POSSIBLE_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES

FEATURE_ALIASES = {
    "左室": "左室(mm)", "右室": "右室(mm)", "左房": "左房(mm)", "右房": "右房(mm)",
    "主动脉": "主动脉峡部(mm)",  "胸廓横径": "胸廓横径(mm)",
    "肺动脉": "肺动脉环径(mm)", "主动脉流速": "主动脉流速(cm/s)", "肺动脉流速": "肺动脉流速(cm/s)",
    "心脏横径": "心脏横径(mm)", "心胸比": "心胸面积比(%)", "心胸面积比": "心胸面积比(%)",
    "卵圆孔": "卵圆孔(mm)", "心轴": "心轴(°)",
    "胎心率": "胎心率(次/分)",
    "二尖瓣E": "二尖瓣-E(cm/s)", "二尖瓣A": "二尖瓣-A(cm/s)",
    "三尖瓣E": "三尖瓣-E(cm/s)", "三尖瓣A": "三尖瓣-A(cm/s)",
    "二尖瓣-E": "二尖瓣-E(cm/s)", "二尖瓣-A": "二尖瓣-A(cm/s)",
    "三尖瓣-E": "三尖瓣-E(cm/s)", "三尖瓣-A": "三尖瓣-A(cm/s)",
    "心率": "胎心率(次/分)","心律": "律",
    "肺静脉S": "肺静脉-S", "肺静脉D": "肺静脉-D", "肺静脉A": "肺静脉-A", "肺静脉PI": "肺静脉-PI",
    "静脉导管S": "静脉导管-S", "静脉导管D": "静脉导管-D", "静脉导管A": "静脉导管-A", "静脉导管PI": "静脉导管-PI",
    "主动脉弓收缩": "主动脉弓-收缩(cm/s)", "主动脉弓舒张": "主动脉弓-舒张(cm/s)"
}

# 相似度核心特征（顺序化，心轴放末尾仅为可读性）
CORE_FEATURES = [c for c in NUMERIC_FEATURES if c != "心轴(°)"] + ["心轴(°)"]

# ---------------- Utils: Config Loader ----------------
def load_config(config_path: Optional[str]) -> Dict:
    if not config_path:
        return {}
    p = Path(config_path)
    if not p.exists():
        raise FileNotFoundError(f"配置文件不存在：{config_path}")
    if p.suffix.lower() in [".yml", ".yaml"]:
        try:
            import yaml  # type: ignore
        except ImportError as e:
            raise RuntimeError("需要安装 PyYAML") from e
        with p.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    else:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f) or {}

# ---------------- Xhang Client ----------------
class XhangModelClient:
    """
    "Generic OpenAI-compatible chat-completions HTTP client (streaming supported).

    The original implementation used a site-specific gateway. For blind review and reproducibility,
    this client exposes the same interface but is provider-agnostic as long as the endpoint follows
    the OpenAI Chat Completions schema: POST {base_url}/chat/completions.

    Configure via environment variables:
      - EXPEVA_API_BASE_URL (e.g., https://<host>/v1)
      - EXPEVA_API_KEY
      - EXPEVA_DEFAULT_MODEL (optional)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 60,
        default_model: str = "xhang",
    ):
        self.api_key = api_key or os.getenv("EXPEVA_API_KEY", "")
        self.base_url = (base_url or os.getenv("EXPEVA_API_BASE_URL", "")).rstrip("/")
        if not self.base_url:
            # Keep the default used in the original codebase, but allow overriding.
            self.base_url = "https://xhang.buaa.edu.cn/xhang/v1"
        self.default_model = default_model or os.getenv("EXPEVA_DEFAULT_MODEL", "xhang")
        self.session = requests.Session()
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        hdr = {"Content-Type": "application/json"}
        if self.api_key:
            hdr["Authorization"] = f"Bearer {self.api_key}"
        return hdr

    @staticmethod
    def _iter_sse_content(resp: requests.Response) -> Iterator[str]:
        """Yield incremental content tokens from an OpenAI-style SSE stream."""
        for raw in resp.iter_lines(decode_unicode=True):
            if not raw:
                continue
            if raw.startswith("data:"):
                raw = raw[len("data:") :].strip()
            if raw == "[DONE]":
                return
            try:
                payload = json.loads(raw)
            except Exception:
                continue
            try:
                delta = payload["choices"][0]["delta"]
                piece = delta.get("content")
                if piece:
                    yield piece
            except Exception:
                continue

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        stream: bool = False,
        **kwargs: Any,
    ) -> str | Iterator[str]:
        """Chat completion. Returns full text or an iterator of streamed tokens."""
        url = f"{self.base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        payload.update(kwargs)

        resp = self.session.post(
            url, headers=self._headers(), json=payload, stream=stream, timeout=self.timeout
        )
        resp.raise_for_status()

        if stream:
            return self._iter_sse_content(resp)

        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def call_stream(self, prompt: str, **kwargs: Any) -> Iterator[str]:
        messages = kwargs.pop("messages", None) or [{"role": "user", "content": prompt}]
        it = self.chat(messages=messages, stream=True, **kwargs)
        assert not isinstance(it, str)
        return it

class FetalCHDAnalyzer:
    def _truncate_after_cues(self, s: str) -> str:
        """在文本中遇到“录入医生”或“建议”、“录入者”、“提示：”时即截断，后续内容不再读取/输出。"""
        if not s:
            return s
        cues = ["录入医生", "建议","录入者","提示："]
        cut = len(s)
        for c in cues:
            idx = s.find(c)
            if idx != -1:
                cut = min(cut, idx)
        return s[:cut]


def _llm_structured_extract(self, raw_text: str) -> Dict[str, Any]:
    """Extract structured measurements from free-form ultrasound text via an LLM.

    This is a best-effort parser used when direct structured inputs are unavailable.
    The model is instructed to output strict JSON only; we then validate and normalize
    the extracted fields before downstream retrieval.
    """

    sys = (
        "You are a medical information extraction assistant. "
        "Extract fetal echocardiography measurements from the given text. "
        "Return STRICT JSON only (no markdown)."
    )
    user = f"TEXT:\n{raw_text}\n\nReturn JSON."
    messages = [{"role": "system", "content": sys}, {"role": "user", "content": user}]

    try:
        content = self.model_client.chat(
            messages=messages,
            model=self.model_name,
            temperature=0.0,
            max_tokens=2048,
            stream=False,
        )
        if not isinstance(content, str):
            content = "".join(list(content))
    except Exception:
        return {}

    # Robust JSON extraction (handles occasional leading/trailing text).
    try:
        obj = json.loads(content)
    except Exception:
        m = re.search(r"\{.*\}", content, flags=re.S)
        if not m:
            return {}
        try:
            obj = json.loads(m.group(0))
        except Exception:
            return {}

    if not isinstance(obj, dict):
        return {}

    # Normalize keys and values into the expected schema where possible.
    norm: Dict[str, Any] = {}
    for k, v in obj.items():
        if isinstance(k, str):
            key = k.strip()
        else:
            continue
        norm[key] = v
    return norm

    def _normalize_and_map_keys(self, kv: dict) -> dict:
        """
        把 LLM 或规则抽到的键名映射到数据集中“标准列名”，并做单位一致化。
        """
        if not kv: return {}
        # 常见别名/空格/破折号差异
        alias = {
            "心轴": "心轴(°)", "心轴(度)": "心轴(°)", "心轴(mm)": "心轴(°)",
            "心胸面积比": "心胸面积比(%)",
            "PA": "肺动脉(mm)", "AO": "主动脉(mm)", "降AO":"降主动脉(mm)",
            "左房": "左房(mm)", "右房":"右房(mm)", "左室":"左室(mm)", "右室":"右室(mm)",
            "主动脉": "主动脉(mm)",  
            "AO(cm/s)":"主动脉(cm/s)", "PA(cm/s)":"肺动脉(cm/s)",
            "三尖瓣E":"三尖瓣-E(cm/s)", "三尖瓣-A":"三尖瓣-A(cm/s)",
            "二尖瓣E":"二尖瓣-E(cm/s)", "二尖瓣-A":"二尖瓣-A(cm/s)",
            "肺静脉S":"肺静脉-S", "肺静脉D":"肺静脉-D", "肺静脉A":"肺静脉-A",
            "静脉导管S":"静脉导管-S", "静脉导管D":"静脉导管-D", "静脉导管A":"静脉导管-A",
            "DG-PI":"静脉导管-PI", "DV-PI":"静脉导管-PI",
        }
        import re
        norm = {}
        for k, v in kv.items():
            kk = str(k)
            kk = kk.replace('（','(').replace('）',')').replace('：',':')
            kk = re.sub(r'\s+', '', kk) 
            kk = alias.get(kk, kk)
            norm[kk] = v

        if "主动脉" in kv and "主动脉(cm/s)" not in norm:
            v = norm.get("主动脉", None)
            if isinstance(v, (int,float)) and v >= 60:
                norm["主动脉(cm/s)"] = float(v); norm.pop("主动脉", None)
            else:
                norm["主动脉(mm)"] = float(v); norm.pop("主动脉", None)

        if "心轴" in norm and "心轴(°)" not in norm:
            norm["心轴(°)"] = float(norm.pop("心轴"))

        return norm



    """胎儿先心病诊断分析系统（语义阳性匹配版：兼容非标准表述）"""

    def __init__(
        self,
        model_api_key: Optional[str] = None,
        config_path: Optional[str] = None,
        use_cache: Optional[bool] = None,
        cache_path: Optional[str] = None,
        refresh_cache: bool = False,
        boot_empty: bool = False,
    ):
        self.api_key = model_api_key
        self.text_cols = ["超声描述", "超声提示"]
        self.model_client = XhangModelClient(model_api_key) if model_api_key else None

        # 配置
        self.config = load_config(config_path) if config_path else {}
        cfg_cache = self.config.get("cache", {})
        self.cache_enabled = (use_cache if use_cache is not None else bool(cfg_cache.get("enabled", False)))
        self.cache_path = str(cache_path or cfg_cache.get("path", "data/cache.parquet"))
        self.refresh_cache = refresh_cache

        # 权重（可从外部配置读取）
        self.feature_weights: Dict[str, float] = {}
        if "numeric_features" in self.config:
            for k, v in self.config["numeric_features"].items():
                if isinstance(v, dict) and "weight" in v:
                    self.feature_weights[k] = float(v["weight"])

        # 相似度配置
        sim_cfg = self.config.get("similarity", {})
        self.sim_kernel = sim_cfg.get("kernel", "rbf")
        self.sim_sigma_cfg = sim_cfg.get("sigma", "median")
        self.sim_norm_w = bool(sim_cfg.get("normalize_weights", True))
        self.sim_min_score = float(sim_cfg.get("min_score", 0.85))  # 仅保留≥阈值的病例

        # ---------- Positive/Negative supervision（语义匹配） ----------
        self.negation_cues = self.config.get("risk", {}).get(
            "negation_cues",
            ["未见", "未发现", "无", "否", "未提示", "排除", "未明确", "未见到", "未提示到", "未提示有"]
        )
        # 语义匹配阈值（可配置）
        self.semantic_ratio = float(self.config.get("risk", {}).get("semantic_ratio", 0.78))
        self.neg_scope = int(self.config.get("risk", {}).get("negation_scope_chars", 8))

        # ---- Composite groups & thresholds (联合指标组与阈值，优先使用数据集分布 ±kσ) ----
        self.composite_cfg = self.config.get("composite", {
            "use_dataset_band": True,
            "k_sigma": 2.0,
            "zdiff_threshold": 2.0,
            "axis_default": [23.0, 58.0],       # 417例实测约23–58°
            "fhr_default": [110, 160],
            "pa_ao_default": [0.91, 1.45],      # PA/AAO
            "ctr_diam_default": [0.45, 0.55],   # 心/胸横径比≈0.50±0.05
            "area_ratio_default": [19.0, 42.0], # 心胸面积比(%)
            # ★ 新增：MV 与 TV 的 E/A 各有默认带
            "ea_default_mv": [0.46, 1.16],
            "ea_default_tv": [0.50, 0.93],
            "fo_ao_default": [0.60, 1.40]
        })
        self._comp_mean_std: Dict[str, Tuple[float, float]] = {}  # 派生/联合列的均值/方差缓存


        # 概念 -> 别名（字符串） 与 正则（pattern）
        # 规则：若【超声提示】包含任一概念的「别名 or 正则 or 语义近似」，即判定为阳性
        self.pos_alias_map: Dict[str, List[str]] = {}
        self.pos_regex_map: Dict[str, List[re.Pattern]] = {}

        def reg(p): return re.compile(p, flags=re.IGNORECASE)

        def add_concept(canon: str, aliases: List[str], regexes: List[str] = None):
            self.pos_alias_map[canon] = aliases[:]
            self.pos_regex_map[canon] = [reg(p) for p in (regexes or [])]

        # 清单 + 常见口语/别称/缩写补充
        add_concept("房间隔缺损（ASD）",
                    ["房间隔缺损", "房缺", "房间隔缺如", "ASD"],
                    [r"\bASD\b"])
        add_concept("室间隔缺损（VSD）",
                    ["室间隔缺损", "室缺", "室间隔缺如", "VSD"],
                    [r"\bVSD\b"])
        add_concept("动脉导管未闭（PDA）",
                    ["动脉导管未闭", "开放性动脉导管", "导管未闭", "PDA"],
                    [r"\bPDA\b"])
        add_concept("房室隔缺损（ECD/AVSD）",
                    ["房室隔缺损", "房室间隔缺损", "房室管畸形", "房室通道畸形", "AVSD", "ECD"],
                    [r"\bAVSD\b", r"\bECD\b"])
        add_concept("部分型肺静脉异位引流（PAPVR/PAPVC）",
                    ["部分型肺静脉异位引流", "部分型肺静脉回流异常", "部分性肺静脉异位回流", "PAPVR", "PAPVC"],
                    [r"\bPAPVR\b", r"\bPAPVC\b"])
        add_concept("法洛四联症（TOF）",
                    ["法洛四联症", "四联症", "TOF","法四"],
                    [r"\bTOF\b"])
        add_concept("大动脉转位（TGA）",
                    ["大动脉转位", "完全型大动脉转位", "DTGA", "LTGA", "D-TGA", "L-TGA", "TGA"],
                    [r"\bD-?TGA\b", r"\bL-?TGA\b", r"\bTGA\b"])
        add_concept("三尖瓣闭锁（TA）",
                    ["三尖瓣闭锁", "TA"],
                    [r"\bTA\b"])
        add_concept("肺动脉闭锁伴完整室间隔（PA/IVS）",
                    ["肺动脉闭锁伴完整室间隔", "肺动脉闭锁（室间隔完整）", "PA/IVS", "PAIVS"],
                    [r"\bPA/?IVS\b", r"\bPAIVS\b"])
        add_concept("完全型肺静脉异位引流（TAPVC）",
                    ["完全型肺静脉异位引流", "完全性肺静脉异位回流", "总肺静脉异位连接", "TAPVC"],
                    [r"\bTAPVC\b"])
        add_concept("单心室/HLHS/HRHS",
                    ["单心室", "左心发育不良", "右心发育不良", "HLHS", "HRHS"],
                    [r"\bHLHS\b", r"\bHRHS\b", r"\bSV\b"])
        add_concept("肺动脉瓣狭窄（PS）",
                    ["肺动脉瓣狭窄", "肺动脉狭窄", "PS"],
                    [r"\bPS\b"])
        add_concept("主动脉瓣狭窄（AS）",
                    ["主动脉瓣狭窄", "AS"],
                    [r"\bAS\b"])
        add_concept("二叶主动脉瓣（BAV）",
                    ["二叶主动脉瓣", "双叶主动脉瓣", "BAV"],
                    [r"\bBAV\b"])
        add_concept("主动脉缩窄（CoA）",
                    ["主动脉缩窄", "主动脉峡部狭窄", "CoA"],
                    [r"\bCoA\b"])
        add_concept("主动脉弓离断（IAA）",
                    ["主动脉弓离断", "大动脉弓离断", "IAA"],
                    [r"\bIAA\b"])
        add_concept("永存动脉干（Truncus）",
                    ["永存动脉干", "共同动脉干", "Truncus"],
                    [r"\bTruncus\b"])
        add_concept("Ebstein畸形",
                    ["Ebstein", "埃布斯坦", "三尖瓣下移", "埃布斯坦畸形"],
                    [r"\bEbstein\b"])
        add_concept("静脉-心房连接异常/体静脉异位",
                    ["静脉心房连接异常", "静脉-心房连接异常", "体静脉异位", "体静脉连接异常"])
        add_concept("房-室连接异常（含闭锁、ECD）",
                    ["房室连接异常", "房-室连接异常", "三尖瓣闭锁", "二尖瓣闭锁", "房室隔缺损", "AVSD", "ECD"],
                    [r"\bAVSD\b", r"\bECD\b"])
        add_concept("心室-大动脉连接异常（DORV/TGA/TOF/Truncus）",
                    ["心室大动脉连接异常", "心室-大动脉连接异常", "DORV", "TGA", "TOF", "永存动脉干"],
                    [r"\bDORV\b", r"\bTGA\b", r"\bTOF\b", r"\bTruncus\b"])
        add_concept("心室或室间隔异常（VSD/SV/HLHS/HRHS）",
                    ["心室异常", "室间隔异常", "室缺", "室间隔缺损", "单心室", "HLHS", "HRHS"])
        add_concept("大动脉异常（CoA/IAA/PDA/肺动脉环）",
                    ["大动脉异常", "主动脉缩窄", "CoA", "IAA", "PDA", "肺动脉环"],
                    [r"\bCoA\b", r"\bIAA\b", r"\bPDA\b"])
        add_concept("瓣膜异常（PS/AS/PA/IVS/Ebstein）",
                    ["瓣膜异常", "肺动脉瓣狭窄", "主动脉瓣狭窄", "PA/IVS", "Ebstein", "埃布斯坦"],
                    [r"\bPS\b", r"\bAS\b", r"\bPA/?IVS\b", r"\bEbstein\b"])
        add_concept("心肌与占位（心肌病/肿瘤/横纹肌瘤）",
                    ["胎儿心肌病", "心肌病", "心脏肿瘤", "横纹肌瘤", "rhabdomyoma"],
                    [r"\brhabdomyoma\b"])
        add_concept("心律失常（房室传导阻滞/室上速等）",
                    ["心律失常", "房室传导阻滞", "房室阻滞", "室上性心动过速", "室上速", "SVT", "心动过速"],
                    [r"\bSVT\b"])
 
        add_concept("永存左上腔静脉（PLSVC）",
                    ["永存左上腔静脉", "左上腔静脉永存", "PLSVC",
                    "persistent left superior vena cava", "左上腔静脉引流冠状静脉窦"],
                    [r"\bPLSVC\b"])

        add_concept("冠状静脉窦增宽/扩张",
                    ["冠状静脉窦增宽", "冠状静脉窦扩大", "冠状静脉窦扩张",
                    "dilated coronary sinus", "coronary sinus dilation"])

        # 复合术语，便于直接命中整句（也配合后面的合成规则）
        add_concept("永存左上腔静脉",
                    ["永存左上腔静脉", "PLSVC伴冠状静脉窦扩张",
                    "persistent left superior vena cava with dilated coronary sinus"])

        add_concept("右上腔静脉缺如",
                    ["右上腔静脉缺如", "RSVC缺如", "缺如右上腔静脉", "absent right SVC"])

        add_concept("下腔静脉离断",
                    ["下腔静脉离断", "IVC离断", "腔静脉离断", "interruption of IVC"])

        add_concept("双下腔静脉",
                    ["双下腔静脉", "重复下腔静脉", "double IVC"])

        add_concept("左位下腔静脉",
                    ["左位下腔静脉", "左位IVC", "left-sided IVC", "left IVC"])

        add_concept("左房异构",
                    ["左房异构", "左异构综合征", "左心房异构", "left atrial isomerism"])
        add_concept("右房异构",
                    ["右房异构", "右异构综合征", "右心房异构", "right atrial isomerism"])

        add_concept("右房憩室/室壁瘤", ["右房憩室", "右房室壁瘤", "右心房憩室", "RA diverticulum", "atrial aneurysm (right)"])
        add_concept("右室憩室/室壁瘤", ["右室憩室", "右室室壁瘤", "RV diverticulum", "ventricular aneurysm (right)"])
        add_concept("左房憩室/室壁瘤", ["左房憩室", "左房室壁瘤", "LA diverticulum", "atrial aneurysm (left)"])
        add_concept("左室憩室/室壁瘤", ["左室憩室", "左室室壁瘤", "LV diverticulum", "ventricular aneurysm (left)"])

        add_concept("血管环", ["血管环", "vascular ring"], ["vascular ring"])


        add_concept("迷走左锁骨下动脉（ALSA）",
                    ["迷走左锁骨下动脉", "ALSA", "aberrant left subclavian artery","左锁骨下动脉迷走"],
                    [r"\bALSA\b"])
        add_concept("迷走右锁骨下动脉（ARSA）",
                    ["迷走右锁骨下动脉", "ARSA", "aberrant right subclavian artery","右锁骨下动脉迷走"],
                    [r"\bARSA\b"])
        add_concept("迷走左无名动脉",
                    ["迷走左无名动脉", "aberrant left brachiocephalic artery","左无名动脉迷走"])
        add_concept("迷走右无名动脉",
                    ["迷走右无名动脉", "aberrant right brachiocephalic artery","右无名动脉迷走"])
        add_concept("双主动脉弓",
                    ["双主动脉弓", "double aortic arch"], ["double aortic arch"])
        add_concept("冠状动脉瘘（CAF）",
                    ["冠状动脉瘘", "冠脉瘘", "冠状动脉-心腔瘘", "冠状动脉-肺动脉瘘", "CAF",
                    "coronary artery fistula"],
                    [r"\bCAF\b"])
        add_concept("右冠状动脉瘘",
                    ["右冠状动脉瘘", "RCA瘘", "右冠脉瘘", "RCAF"])
        add_concept("左冠状动脉瘘",
                    ["左冠状动脉瘘", "LCA瘘", "左冠脉瘘", "LCAF"])
        add_concept("右心室双出口",
                    ["右心室双出口", "DORV"], [r"\bDORV\b"])

        cfg_terms = self.config.get("risk", {}).get("positive_terms", [])
        for term in cfg_terms:
            canon = f"自定义阳性：{term}"
            self.pos_alias_map[canon] = [term]
            self.pos_regex_map.setdefault(canon, [])


        self.risk_threshold = float(self.config.get("risk", {}).get("positive_ratio_threshold", 0.30))
        self.topn_terms = int(self.config.get("risk", {}).get("topn_terms", 10))
        self.max_examples = int(self.config.get("risk", {}).get("max_examples", 3))

        if boot_empty:
            self.df = pd.DataFrame()
            self.available_features = []
            self._col_mean, self._col_std = {}, {}
            self._z_core = pd.DataFrame()
        else:
            self._load_and_preprocess_data()

            # 数值列降精度 & 一次性保存全量 Z 分数表
            numeric_exist = [c for c in NUMERIC_FEATURES if c in self.df.columns]
            if numeric_exist:
                self.df[numeric_exist] = self.df[numeric_exist].astype(np.float32)
                mu = pd.Series(self._col_mean, dtype=np.float32)
                sd = pd.Series(self._col_std, dtype=np.float32).replace(0, 1.0)
                self._Z_all = ((self.df[numeric_exist] - mu) / sd).astype(np.float32)
            else:
                self._Z_all = pd.DataFrame()

            # 预先缓存规范化文本，避免重复规范化 & 提速匹配
            norm_map = {f"{col}_norm": self.df[col].map(self._normalize_text) for col in self.text_cols}
            self.df = self.df.assign(**norm_map)


    # —— 基础抽取正则预编译（只编译一次） ——
        self._basic_extract_patterns = []
        def _basic_pattern_map():
            return {
                r'卵圆孔[是为:=：\s]*(-?\d+\.?\d*)': '卵圆孔(mm)',
                r'心轴[是为:=：\s]*(-?\d+\.?\d*)[°度]?': '心轴(°)',
                r'二尖瓣[-\s]*E(?:和|与)?(?:三尖瓣[-\s]*E)?[都是为:=：\s]*(-?\d+\.?\d*)': '二尖瓣-E(cm/s)',
                r'三尖瓣[-\s]*E[是为:=：\s]*(-?\d+\.?\d*)': '三尖瓣-E(cm/s)',
                r'二尖瓣[-\s]*A(?:和|与)?(?:三尖瓣[-\s]*A)?[都是为:=：\s]*(-?\d+\.?\d*)': '二尖瓣-A(cm/s)',
                r'三尖瓣[-\s]*A[是为:=：\s]*(-?\d+\.?\d*)': '三尖瓣-A(cm/s)',
                r'主动脉弓[-—]?[收缩][：: ]*(-?\d+\.?\d*)': '主动脉弓-收缩(cm/s)',
                r'主动脉弓[-—]?[舒张][：: ]*(-?\d+\.?\d*)': '主动脉弓-舒张(cm/s)',
                r'动脉导管弓[-—]?[收缩][：: ]*(-?\d+\.?\d*)': '动脉导管弓-收缩(cm/s)',
                r'动脉导管弓[-—]?[舒张][：: ]*(-?\d+\.?\d*)': '动脉导管弓-舒张(cm/s)',
                r'(?:肺动脉(?:速度|峰值|Vmax|流速)?)[是为:=：\s]*(-?\d+\.?\d*)\s*(?:cm/?s|cm\s*/\s*s)?': '肺动脉(cm/s)',
                r'左室[是为:=：\s]*(-?\d+\.?\d*)': '左室(mm)',
                r'右室[是为:=：\s]*(-?\d+\.?\d*)': '右室(mm)',
                r'左房[是为:=：\s]*(-?\d+\.?\d*)': '左房(mm)',
                r'右房[是为:=：\s]*(-?\d+\.?\d*)': '右房(mm)',
                r'胸廓横径[是为:=：\s]*(-?\d+\.?\d*)': '胸廓横径(mm)',
                r'心脏横径[是为:=：\s]*(-?\d+\.?\d*)': '心脏横径(mm)',
                r'胎心率(?:\(次/分\))?[是为:=：\s]*(-?\d+\.?\d*)': '胎心率(次/分)',
            }
        self._basic_extract_patterns = [(re.compile(p), t) for p, t in _basic_pattern_map().items()]

        self._literal_col_patterns = []
        for col in NUMERIC_FEATURES:
            pat = re.compile(rf"{re.escape(col)}\s*[:=：]?\s*(-?\d+(?:\.\d+)?)")
            self._literal_col_patterns.append((pat, col))

        self._axis_fallback_pat = re.compile(r"心轴(?:\([^)]*\))?\s*[:=：]?\s*(-?\d+(?:\.\d+)?)")

        # 类别项“律齐”简单提取
        self._rhythm_pat = re.compile(r"律齐\s*[:=：]?\s*(\d+|齐|不齐|正常|异常|是|否)")

        # —— 提速：是否启用快速文本匹配（关闭滑窗相似度） ——
        self.fast_text_match = True
    # ---------- Helpers: normalization & fuzzy ----------
    @staticmethod
    def _normalize_text(s: str) -> str:
        if s is None:
            return ""
        s = str(s).lower()
        s = s.replace("－", "-").replace("—", "-").replace("–", "-")
        s = s.replace("（", "(").replace("）", ")").replace("：", ":").replace("，", ",").replace("。", ".").replace("、", ",").replace("；", ";")
        s = re.sub(r'\s+', '', s)
        s = s.replace("-", "").replace("/", "")
        s = re.sub(r'[,:;.\(\)【】\[\]{}!?！？]', '', s)
        return s

    def _fuzzy_contains(self, text: str, phrase: str, min_ratio: float = None) -> bool:
        """
        语义近似匹配：
        1) 归一化后直接包含
        2) token AND（将短词拆为若干中文/英文token，全部出现即通过）
        3) 滑窗 + difflib.SequenceMatcher 子串相似度
        4) 简易“子序列”匹配
        """
        if not text or not phrase:
            return False
        nt = self._normalize_text(text)
        np_ = self._normalize_text(phrase)
        if not np_:
            return False
        if np_ in nt:
            return True

        # token AND（对包含空格/合成词的别名有用）
        tokens = re.findall(r'[\u4e00-\u9fa5a-z0-9]+', phrase.lower())
        tok_need = [self._normalize_text(t) for t in tokens if len(t) >= 2]
        if tok_need and all(t in nt for t in tok_need):
            return True

        # 滑窗 + 相似度
        ratio = self.semantic_ratio if min_ratio is None else min_ratio
        L = len(np_)
        if L >= 4:
            w_min = max(4, int(L * 0.6))
            w_max = int(L * 1.4)
            n = len(nt)
            for wlen in range(w_min, min(w_max, n) + 1):
                for i in range(0, n - wlen + 1):
                    win = nt[i:i + wlen]
                    if SequenceMatcher(None, win, np_).ratio() >= ratio:
                        return True

        # 子序列（保持字符顺序）
        pattern = '.*?'.join(map(re.escape, list(np_)))
        if re.search(pattern, nt):
            return True

        return False

    # ---------- Data IO & Cache ----------
    def _latest_source_signature(self) -> float:
        sig = 0.0
        for p in DATA_PATHS:
            try:
                st = p.stat()
                sig += float(st.st_mtime) + float(st.st_size)  # 聚合修改时间 + 大小
            except Exception:
                pass
        sig += sum(1 for p in DATA_PATHS if p.exists())
        return sig

    def _should_use_cache(self) -> bool:
        if not self.cache_enabled:
            return False
        cp = Path(self.cache_path)
        if not cp.exists() or self.refresh_cache:
            return False
        try:
            cache_mtime = cp.stat().st_mtime
            src_mtime = self._latest_source_signature()
            return cache_mtime >= src_mtime
        except Exception:
            return False

    def _write_cache(self, df: pd.DataFrame):
        if not self.cache_enabled:
            return
        cp = Path(self.cache_path)
        cp.parent.mkdir(parents=True, exist_ok=True)
        try:
            df.to_parquet(cp, index=False)
            logger.info(f"已写入缓存：{cp}")
        except Exception as e:
            logger.warning(f"写入Parquet缓存失败（可安装pyarrow或fastparquet）：{e}")

    def _read_cache(self) -> Optional[pd.DataFrame]:
        if not self.cache_enabled:
            return None
        cp = Path(self.cache_path)
        if not cp.exists():
            return None
        try:
            logger.info(f"从缓存加载数据：{cp}")
            return pd.read_parquet(cp)
        except Exception as e:
            logger.warning(f"读取Parquet缓存失败：{e}")
            return None

    def _load_raw_df(self) -> pd.DataFrame:
        if self._should_use_cache():
            cached = self._read_cache()
            if cached is not None:
                return cached

        all_dfs = []
        for path in DATA_PATHS:
            try:
                df = pd.read_excel(path)
                month_name = path.stem.split('year')[-1]
                df['数据来源'] = f"安贞医院{month_name}"
                all_dfs.append(df)
                logger.info(f"成功加载 {path.name}：{len(df)} 条")
            except Exception as e:
                logger.warning(f"加载失败 {path}: {e}")

        if all_dfs:
            df = pd.concat(all_dfs, ignore_index=True)
            self._write_cache(df)
            return df
        else:
            logger.warning("未能加载任何数据集")
            return pd.DataFrame()

    def _apply_feature_bounds(self, numdf: pd.DataFrame) -> pd.DataFrame:
        cfg = self.config.get("numeric_features", {})
        if not cfg:
            if "心轴(°)" in numdf.columns:
                numdf["心轴(°)"] = numdf["心轴(°)"].clip(lower=0, upper=120)
            if "胎心率(次/分)" in numdf.columns:
                numdf["胎心率(次/分)"] = numdf["胎心率(次/分)"].clip(lower=60, upper=220)
            if "心胸面积比(%)" in numdf.columns:
                numdf["心胸面积比(%)"] = numdf["心胸面积比(%)"].clip(lower=0, upper=100)
            return numdf

        for col, rule in cfg.items():
            if col in numdf.columns and isinstance(rule, dict):
                lo = rule.get("min", None)
                hi = rule.get("max", None)
                if lo is not None or hi is not None:
                    numdf[col] = numdf[col].clip(lower=lo, upper=hi)
        return numdf

    def _load_and_preprocess_data(self):
        self.df = self._load_raw_df()
        self.clinical_data = self.df.copy()

        for col in self.text_cols:
            if col not in self.df.columns:
                self.df[col] = ""

        self.available_features = [c for c in ALL_POSSIBLE_FEATURES if c in self.df.columns]
        logger.info(f"存在的特征列：{len(self.available_features)}")

        if "律齐" in self.df.columns:
            cat_cfg = self.config.get("categorical_features", {}).get("律齐", {})
            mapping = cat_cfg.get("mapping", {"齐": 1, "是": 1, "正常": 1, "不齐": 0, "否": 0, "异常": 0})
            default = cat_cfg.get("default", 0)
            self.df["律齐"] = (
                self.df["律齐"].astype(str)
                .str.strip()
                .map(mapping)
                .fillna(default)
                .astype(int)
            )

        numeric_exist = [c for c in NUMERIC_FEATURES if c in self.df.columns]
        if numeric_exist:
            numdf = self.df[numeric_exist].astype(str)
            extracted = numdf.apply(lambda s: s.str.extract(r'(-?\d+(?:\.\d+)?)', expand=False))
            numdf = extracted.apply(pd.to_numeric, errors='coerce')
            numdf = self._apply_feature_bounds(numdf)
            numdf = numdf.fillna(numdf.median(numeric_only=True))
            self.df[numeric_exist] = numdf

        # 统一转字符串并填空
        self.df[self.text_cols] = self.df[self.text_cols].astype(str).fillna("")
        # 批量截断（DataFrame 级别 applymap，不反复插列）
        # 先做缺失处理与类型统一
        self.df[self.text_cols] = self.df[self.text_cols].fillna("").astype(str)

        # 新版 pandas：DataFrame.map 逐元素
        if hasattr(self.df[self.text_cols], "map"):
            self.df[self.text_cols] = self.df[self.text_cols].map(self._truncate_after_cues)
        else:
            # 老版本兜底：对每列（Series）做 map（同样是逐元素）
            self.df[self.text_cols] = self.df[self.text_cols].apply(lambda s: s.map(self._truncate_after_cues))


        self._col_mean = self.df[numeric_exist].mean(numeric_only=True).to_dict() if numeric_exist else {}
        self._col_std = (
            self.df[numeric_exist].std(ddof=0, numeric_only=True).replace(0, 1).to_dict()
            if numeric_exist else {}
        )

        exist_core = [c for c in CORE_FEATURES if c in self.df.columns]
        if exist_core:
            self._z_core = (self.df[exist_core] - pd.Series(self._col_mean)).div(pd.Series(self._col_std))
        else:
            self._z_core = pd.DataFrame()   
        self._build_composite_stats()
        self._build_status_cache()


    def recompute_stats(self):
        self.available_features = [c for c in ALL_POSSIBLE_FEATURES if c in self.df.columns]
        numeric_exist = [c for c in NUMERIC_FEATURES if c in self.df.columns]
        self._col_mean = self.df[numeric_exist].mean(numeric_only=True).to_dict() if numeric_exist else {}
        self._col_std = (
            self.df[numeric_exist].std(ddof=0, numeric_only=True).replace(0, 1).to_dict()
            if numeric_exist else {}
        )
        exist_core = [c for c in CORE_FEATURES if c in self.df.columns]
        if exist_core:
            self._z_core = (self.df[exist_core] - pd.Series(self._col_mean)).div(pd.Series(self._col_std))
        else:
            self._z_core = pd.DataFrame()
        self._build_composite_stats()
        self._build_status_cache()

    # ---------- Composite & Joint Metrics (derived columns + grouped rules) ----------
    def _safe_div(self, a, b):
        try:
            a = float(a); b = float(b)
            if b == 0 or not np.isfinite(a) or not np.isfinite(b):
                return np.nan
            return a / b
        except Exception:
            return np.nan

    def _compute_dataset_band(self, col: str, default_lo=None, default_hi=None):
        """返回 (lo, hi)，优先使用数据集均值±kσ，缺失时回退到默认带"""
        k = float(self.composite_cfg.get("k_sigma", 2.0))
        use = bool(self.composite_cfg.get("use_dataset_band", True))
        if use and (col in self._comp_mean_std or col in self._col_mean):
            if col in self._comp_mean_std:
                m, s = self._comp_mean_std[col]
            else:
                m = float(self._col_mean.get(col, 0.0)); s = float(self._col_std.get(col, 1.0) or 1.0)
            s = s or 1.0
            return (m - k * s, m + k * s)
        return (default_lo, default_hi)


    def _build_composite_stats(self):
        if self.df is None or self.df.empty:
            return

        df = self.df  # 简写
        derived = {}  # 收集要新增/覆盖的所有派生列

        with np.errstate(divide='ignore', invalid='ignore'):
            if {"二尖瓣-E(cm/s)","二尖瓣-A(cm/s)"}.issubset(df.columns):
                derived["MV_EA"] = np.divide(df["二尖瓣-E(cm/s)"], df["二尖瓣-A(cm/s)"])
            if {"三尖瓣-E(cm/s)","三尖瓣-A(cm/s)"}.issubset(df.columns):
                derived["TV_EA"] = np.divide(df["三尖瓣-E(cm/s)"], df["三尖瓣-A(cm/s)"])
            if {"右室(mm)","左室(mm)"}.issubset(df.columns):
                derived["RV_LV_RATIO"] = np.divide(df["右室(mm)"], df["左室(mm)"])
            if {"肺动脉(mm)","主动脉(mm)"}.issubset(df.columns):
                derived["PA_AO_RATIO"] = np.divide(df["肺动脉(mm)"], df["主动脉(mm)"])
            if {"心脏横径(mm)","胸廓横径(mm)"}.issubset(df.columns):
                derived["CTR_DIAM_RATIO"] = np.divide(df["心脏横径(mm)"], df["胸廓横径(mm)"])
            if {"卵圆孔(mm)","主动脉(mm)"}.issubset(df.columns):
                derived["FO_AO_RATIO"] = np.divide(df["卵圆孔(mm)"], df["主动脉(mm)"])

        # z-score 辅助
        def _z(series_name: str):
            if series_name not in df.columns:
                return None
            mu = self._col_mean.get(series_name, 0.0)
            sd = self._col_std.get(series_name, 1.0) or 1.0
            return (df[series_name] - mu) / sd

        # 一次性把 zdiff 结果也放进 derived
        if {"左房(mm)","右房(mm)"}.issubset(df.columns):
            z_la, z_ra = _z("左房(mm)"), _z("右房(mm)")
            if z_la is not None and z_ra is not None:
                derived["ATRIAL_ZDIFF"] = (z_la - z_ra).abs()

        if {"左室(mm)","右室(mm)"}.issubset(df.columns):
            z_lv, z_rv = _z("左室(mm)"), _z("右室(mm)")
            if z_lv is not None and z_rv is not None:
                derived["VENT_ZDIFF"] = (z_lv - z_rv).abs()

        # —— 关键：一次性合并所有派生列，顺便降精度减少内存 —— #
        if derived:
            for k, v in derived.items():
                # 改为 float32，和你前面 numeric 降精度保持一致
                derived[k] = pd.to_numeric(v, errors='coerce').astype(np.float32)

            self.df = df.assign(**derived)  # 返回新 DataFrame，避免块碎片
            df = self.df  # 后续缓存统计都用最新的 df

        # 之后保持你的均值/方差缓存逻辑不变
        self._comp_mean_std = {}
        for col in ["MV_EA","TV_EA","PA_AO_RATIO","RV_LV_RATIO",
                    "CTR_DIAM_RATIO","FO_AO_RATIO","ATRIAL_ZDIFF","VENT_ZDIFF"]:
            if col in df.columns:
                s = pd.to_numeric(df[col], errors='coerce').replace([np.inf,-np.inf], np.nan)
                m = float(np.nanmean(s)) if s.notna().any() else 0.0
                v = float(np.nanstd(s)) if s.notna().any() else 1.0
                self._comp_mean_std[col] = (m, v or 1.0)

    # === 数据内部关系挖掘（全局异常度 + 邻域阳性 + 关系残差） ===
    def _build_status_cache(self):
        """缓存每行的 normal/diseased/suspect 标签，以便筛选“正常”子集建模"""
        if self.df is None or self.df.empty:
            self._normal_mask = np.array([], dtype=bool)
            return
        try:
            sts = self.df.apply(self._is_diseased_case, axis=1)
            self._normal_mask = (sts.values == "normal")
        except Exception:
            self._normal_mask = np.array([True] * len(self.df), dtype=bool)  # 兜底：全当正常

    def _global_mahalanobis(self, q: Dict[str, float]) -> float:
        if not hasattr(self, "_normal_mask"):
            self._build_status_cache()

        """基于‘正常’子集估计均值/协方差，计算马氏距离；若失败退化为欧式z范数"""
        feats = [f for f in q.keys() if f in self.df.columns and f in NUMERIC_FEATURES]
        if not feats:
            return float('nan')
        Xn = self.df.loc[self._normal_mask, feats]
        Xn = pd.to_numeric(Xn.stack(), errors='coerce').unstack()
        Xn = Xn.dropna(axis=0, how='any')
        zq = np.array([(q[f] - self._col_mean.get(f, 0.0)) / (self._col_std.get(f, 1.0) or 1.0) for f in feats], dtype=float)
        if len(Xn) >= len(feats) + 5:
            Zn = ((Xn - pd.Series(self._col_mean)).div(pd.Series(self._col_std).replace(0,1)))[feats].to_numpy(dtype=float)
            cov = np.cov(Zn, rowvar=False)
            try:
                inv = np.linalg.pinv(cov)
                md2 = float(zq @ inv @ zq.T)
                return float(np.sqrt(md2))
            except Exception:
                pass
        # 兜底：欧式z范数
        return float(np.linalg.norm(zq))

    def _mine_internal_relations(self, query: Dict[str, float], k: int = 10) -> Dict[str, object]:

        """返回：
        {
            "mdist": float,              # 全局异常度（马氏距离）
            "knn_pos_ratio": float,      # 邻域(相似度)阳性/可疑比例
            "relation_anoms": List[Tuple[str,float]],  # 关系残差Top-N（名称, |z|）
            "text": str                  # 可直接拼到超声描述的文本
        }
        """
        if not hasattr(self, "_normal_mask"):
            self._build_status_cache()

        # 1) 全局异常度
        md = self._global_mahalanobis(query)

        # 2) 邻域阳性占比（kNN，沿用已有相似度空间与权重）
        sim_rows = self.find_similar_cases(query, k=max(10, k))
        if sim_rows:
            sims = np.array([float(r.get("similarity_score", 0.0) or 0.0) for r in sim_rows], dtype=float)
            labs = np.array([1.0 if self._is_diseased_case(r) in ("diseased","suspect") else 0.0 for r in sim_rows], dtype=float)
            w = sims / (sims.sum() + 1e-8)
            knn_pos = float((w * labs).sum())
        else:
            knn_pos = float('nan')

        # 3) 关系残差：在“正常”子集上拟合一次线性关系，返回当前样本的标准化残差
        pairs = [
            ("肺动脉(mm)", "主动脉(mm)", "PA~AO"),
            ("右室(mm)", "左室(mm)", "RV~LV"),
            ("心脏横径(mm)", "胸廓横径(mm)", "心横径~胸廓径"),
            ("卵圆孔(mm)", "主动脉(mm)", "FO~AO"),
        ]
        rel_anoms = []
        for y, x, name in pairs:
            if y in self.df.columns and x in self.df.columns and (y in query and x in query):
                sub = self.df.loc[self._normal_mask, [x, y]].dropna()
                if len(sub) >= 30:
                    try:
                        X = sub[x].to_numpy(dtype=float); Y = sub[y].to_numpy(dtype=float)
                        # 简单线性拟合
                        b1, b0 = np.polyfit(X, Y, deg=1)  # y ≈ b1*x + b0
                        yhat = b1 * float(query[x]) + b0
                        resid = float(query[y]) - float(yhat)
                        # 残差标准化（用正常子集残差的std）
                        rstd = float(np.std(Y - (b1 * X + b0))) or 1.0
                        z = float(resid / rstd)
                        rel_anoms.append((name, abs(z)))
                    except Exception:
                        pass

        # 文本拼装
        lines = []
        if np.isfinite(md):
            lines.append(f"- 全局异常度（马氏距离）：{md:.2f}（>2.0 值得重点关注）")
        if np.isfinite(knn_pos):
            lines.append(f"- 邻域阳性/可疑加权占比：{knn_pos:.2f}")
        if rel_anoms:
            rel_anoms.sort(key=lambda t: t[1], reverse=True)
            tops = "；".join([f"{n}|z|≈{v:.2f}" for n, v in rel_anoms[:5]])
            lines.append(f"- 关系残差Top：{tops}")
        return {
            "mdist": md,
            "knn_pos_ratio": knn_pos,
            "relation_anoms": rel_anoms,
            "text": ("\n".join(lines) if lines else "")
        }







    def analyze_composite_groups(self, query: Dict[str, float]) -> Dict[str, object]:
        """五个组合的规则化判读，返回 {'text': str, 'flags': int}"""
        q = self._validate_query(query)
        out_lines: List[str] = []
        flags = 0

        # 预取默认带（无数据分布时使用）
        axis_lo, axis_hi = self.composite_cfg.get("axis_default", [25.0, 65.0])
        fhr_lo, fhr_hi = self.composite_cfg.get("fhr_default", [110, 160])
        pa_lo, pa_hi = self.composite_cfg.get("pa_ao_default", [0.75, 1.45])
        ctr_lo, ctr_hi = self.composite_cfg.get("ctr_diam_default", [0.40, 0.55])
        area_lo, area_hi = self.composite_cfg.get("area_ratio_default", [25.0, 35.0])

        ea_mv_lo, ea_mv_hi = self.composite_cfg.get("ea_default_mv", [0.46, 1.16])
        ea_tv_lo, ea_tv_hi = self.composite_cfg.get("ea_default_tv", [0.50, 0.93])

        foao_lo, foao_hi = self.composite_cfg.get("fo_ao_default", [0.60, 1.40])
        zd_thr = float(self.composite_cfg.get("zdiff_threshold", 2.0))

        # —— 工具：从数据集 ±kσ 取带，缺失则回退默认 —— 
        def band(col, default):
            return self._compute_dataset_band(col, default[0], default[1])

        # ===== 组合1：左房+右房+左室+右室+卵圆孔 =====
        g1 = []
        # 房/室不对称（z-diff）
        if {"左房(mm)", "右房(mm)"}.issubset(q.keys()) and "ATRIAL_ZDIFF" in self._comp_mean_std:
            mu, sd = self._comp_mean_std["ATRIAL_ZDIFF"]; thr = max(zd_thr, mu + 2*sd)
            z_la = (float(q["左房(mm)"]) - self._col_mean.get("左房(mm)",0))/ (self._col_std.get("左房(mm)",1) or 1)
            z_ra = (float(q["右房(mm)"]) - self._col_mean.get("右房(mm)",0))/ (self._col_std.get("右房(mm)",1) or 1)
            zd = abs(z_la - z_ra)
            if zd >= thr:
                g1.append(f"左右房不对称：|z(左房)-z(右房)|={zd:.2f} ≥ {thr:.2f}")
                flags += 1
        if {"左室(mm)", "右室(mm)"}.issubset(q.keys()) and "VENT_ZDIFF" in self._comp_mean_std:
            mu, sd = self._comp_mean_std["VENT_ZDIFF"]; thr = max(zd_thr, mu + 2*sd)
            z_lv = (float(q.get("左室(mm)",0)) - self._col_mean.get("左室(mm)",0))/ (self._col_std.get("左室(mm)",1) or 1)
            z_rv = (float(q.get("右室(mm)",0)) - self._col_mean.get("右室(mm)",0))/ (self._col_std.get("右室(mm)",1) or 1)
            zd = abs(z_lv - z_rv)
            if zd >= thr:
                g1.append(f"左右室不对称：|z(左室)-z(右室)|={zd:.2f} ≥ {thr:.2f}")
                flags += 1
        # 卵圆孔：优先用数据集带；缺失则回退到 FO/Ao 比例
        if "卵圆孔(mm)" in q:
            fo = float(q["卵圆孔(mm)"])
            lo, hi = band("卵圆孔(mm)", [None, None])
            if lo is None or hi is None:
                if "主动脉(mm)" in q:
                    foao = self._safe_div(fo, q["主动脉(mm)"])
                    lo, hi = band("FO_AO_RATIO", [foao_lo, foao_hi])
                    if (lo is not None and foao < lo) or (hi is not None and foao > hi):
                        g1.append(f"卵圆孔/主动脉比值异常：{foao:.2f} 不在[{lo:.2f}, {hi:.2f}]")
                        flags += 1
            else:
                if fo < lo or fo > hi:
                    g1.append(f"卵圆孔直径异常：{fo:.2f} 不在[{lo:.2f}, {hi:.2f}]")
                    flags += 1
        if g1:
            out_lines.append("**组合1｜左右腔室 + 卵圆孔（结构对称与分流通道）**\n- " + "\n- ".join(g1))

        # ===== 组合2：主动脉+肺动脉+左室+右室+心轴 =====
        g2 = []
        if {"肺动脉(mm)", "主动脉(mm)"}.issubset(q.keys()):
            paao = self._safe_div(q["肺动脉(mm)"], q["主动脉(mm)"])
            lo, hi = band("PA_AO_RATIO", [pa_lo, pa_hi])
            if (lo is not None and paao < lo) or (hi is not None and paao > hi):
                g2.append(f"肺动脉/主动脉比值异常：{paao:.2f} 不在[{lo:.2f}, {hi:.2f}]")
                flags += 1
        if {"右室(mm)", "左室(mm)"}.issubset(q.keys()):
            rvlv = self._safe_div(q["右室(mm)"], q["左室(mm)"])
            lo, hi = band("RV_LV_RATIO", [0.60, 1.60])
            if (lo is not None and rvlv < lo) or (hi is not None and rvlv > hi):
                g2.append(f"右室/左室比值异常：{rvlv:.2f} 不在[{lo:.2f}, {hi:.2f}]")
                flags += 1
        if "心轴(°)" in q:
            axis = float(q["心轴(°)"])
            lo, hi = band("心轴(°)", [axis_lo, axis_hi])
            if (lo is not None and axis < lo) or (hi is not None and axis > hi):
                g2.append(f"心轴偏离：{axis:.1f}° 不在[{lo:.1f}°, {hi:.1f}°]")
                flags += 1
        if g2:
            out_lines.append("**组合2｜大动脉口径 + 心室负荷 + 心轴**\n- " + "\n- ".join(g2))

        # ===== 组合3：二尖瓣E/A + 三尖瓣E/A + 胎心率 =====
        g3 = []
        def _ea_from(q, e_key, a_key):
            return self._safe_div(q.get(e_key), q.get(a_key)) if e_key in q and a_key in q else np.nan
        mv_ea = _ea_from(q, "二尖瓣-E(cm/s)", "二尖瓣-A(cm/s)")
        tv_ea = _ea_from(q, "三尖瓣-E(cm/s)", "三尖瓣-A(cm/s)")
        if np.isfinite(mv_ea):
            lo, hi = band("MV_EA", [ea_mv_lo, ea_mv_hi])
            if (lo is not None and mv_ea < lo) or (hi is not None and mv_ea > hi):
                g3.append(f"二尖瓣 E/A 异常：{mv_ea:.2f} 不在[{lo:.2f}, {hi:.2f}]"); flags += 1
        if np.isfinite(tv_ea):
            lo, hi = band("TV_EA", [ea_tv_lo, ea_tv_hi])
            if (lo is not None and tv_ea < lo) or (hi is not None and tv_ea > hi):
                g3.append(f"三尖瓣 E/A 异常：{tv_ea:.2f} 不在[{lo:.2f}, {hi:.2f}]"); flags += 1
        if "胎心率(次/分)" in q:
            hr = float(q["胎心率(次/分)"])
            lo, hi = band("胎心率(次/分)", [fhr_lo, fhr_hi])
            if (lo is not None and hr < lo) or (hi is not None and hr > hi):
                g3.append(f"胎心率异常：{hr:.0f} 不在[{lo:.0f}, {hi:.0f}] bpm"); flags += 1
        if g3:
            out_lines.append("**组合3｜舒张充盈（E/A） + 节律**\n- " + "\n- ".join(g3))

        # ===== 组合4：心脏横径 + 胸廓横径 + 心胸面积比(%) + 心胸比(%) =====
        g4 = []
        if {"心脏横径(mm)", "胸廓横径(mm)"}.issubset(q.keys()):
            ctr = self._safe_div(q["心脏横径(mm)"], q["胸廓横径(mm)"])
            lo, hi = band("CTR_DIAM_RATIO", [ctr_lo, ctr_hi])
            if (lo is not None and ctr < lo) or (hi is not None and ctr > hi):
                g4.append(f"心/胸横径比异常：{ctr:.2f} 不在[{lo:.2f}, {hi:.2f}]"); flags += 1
        if "心胸面积比(%)" in q:
            ca = float(q["心胸面积比(%)"])
            lo, hi = band("心胸面积比(%)", [area_lo, area_hi])
            if (lo is not None and ca < lo) or (hi is not None and ca > hi):
                g4.append(f"心胸面积比异常：{ca:.1f}% 不在[{lo:.1f}%, {hi:.1f}%]"); flags += 1
        if "心胸比(%)" in q:
            ctp = float(q["心胸比(%)"])
            lo, hi = band("心胸比(%)", [ctr_lo*100.0, ctr_hi*100.0])
            if (lo is not None and ctp < lo) or (hi is not None and ctp > hi):
                g4.append(f"心胸比(%) 异常：{ctp:.1f}% 不在[{lo:.1f}%, {hi:.1f}%]"); flags += 1
        if g4:
            out_lines.append("**组合4｜心胸大小与比例（形态学）**\n- " + "\n- ".join(g4))

        # ===== 组合5：卵圆孔 + 主动脉 + 肺动脉 + 心轴 + 胎心率 =====
        g5 = []
        if {"卵圆孔(mm)", "主动脉(mm)"}.issubset(q.keys()):
            foao = self._safe_div(q["卵圆孔(mm)"], q["主动脉(mm)"])
            lo, hi = band("FO_AO_RATIO", [foao_lo, foao_hi])
            if (lo is not None and foao < lo) or (hi is not None and foao > hi):
                g5.append(f"卵圆孔/主动脉比值异常：{foao:.2f} 不在[{lo:.2f}, {hi:.2f}]"); flags += 1
        if {"肺动脉(mm)", "主动脉(mm)"}.issubset(q.keys()):
            paao = self._safe_div(q["肺动脉(mm)"], q["主动脉(mm)"])
            lo, hi = band("PA_AO_RATIO", [pa_lo, pa_hi])
            if (lo is not None and paao < lo) or (hi is not None and paao > hi):
                g5.append(f"肺动脉/主动脉比值异常：{paao:.2f} 不在[{lo:.2f}, {hi:.2f}]"); flags += 1
        if "心轴(°)" in q:
            axis = float(q["心轴(°)"])
            lo, hi = band("心轴(°)", [axis_lo, axis_hi])
            if (lo is not None and axis < lo) or (hi is not None and axis > hi):
                g5.append(f"心轴偏离：{axis:.1f}° 不在[{lo:.1f}°, {hi:.1f}°]"); flags += 1
        if "胎心率(次/分)" in q:
            hr = float(q["胎心率(次/分)"])
            lo, hi = band("胎心率(次/分)", [fhr_lo, fhr_hi])
            if (lo is not None and hr < lo) or (hi is not None and hr > hi):
                g5.append(f"胎心率异常：{hr:.0f} 不在[{lo:.0f}, {hi:.0f}] bpm"); flags += 1
        if g5:
            out_lines.append("**组合5｜分流口径 + 大动脉比例 + 轴与节律（整合）**\n- " + "\n- ".join(g5))

        text = "\n\n".join(out_lines) if out_lines else ""
        return {"text": text, "flags": flags}
      
    # ---------- Text Extraction ----------
    def extract_measurements_from_text_with_ai(self, text: str) -> Dict[str, float]:
        if not self.model_client:
            return self.extract_measurements_from_text_basic(text)

        # 重要修复：避免在f-string中直接包含未转义的大括号，改为拼接构造
        parts: List[str] = []
        parts.append("作为医学数据提取专家，请从以下文本中提取胎儿心脏超声测量数据。\n\n")
        parts.append("输入文本：\n")
        parts.append(str(text))
        parts.append("\n\n请提取以下可能的测量指标数据（只提取文本中明确提到的数据，不要推测或添加未提及的数据）：\n")
        parts.append("- 胸廓横径(mm)\n- 左室(mm)\n- 左房(mm)\n- 主动脉(mm)\n- 主动脉峡部(mm)\n- 左肺动脉(mm)\n- 动脉导管(mm)\n- 心胸面积比(%)\n- 心脏横径(mm)\n- 右室(mm)\n- 右房(mm)\n- 肺动脉(mm)\n- 降主动脉(mm)\n- 右肺动脉(mm)\n- 卵圆孔(mm)\n- 心轴(°)\n- 二尖瓣-E(cm/s)\n- 二尖瓣-A(cm/s)\n- 三尖瓣-E(cm/s)\n- 三尖瓣-A(cm/s)\n- 主动脉(cm/s)\n- 肺动脉(cm/s)\n- 主动脉弓-收缩(cm/s)\n- 主动脉弓-舒张(cm/s)\n- 动脉导管弓-收缩(cm/s)\n- 动脉导管弓-舒张(cm/s)\n- 胎心率(次/分)\n- 肺静脉-S\n- 肺静脉-D\n- 肺静脉-A\n- 肺静脉-PI\n- 静脉导管-S\n- 静脉导管-D\n- 静脉导管-A\n- 静脉导管-PI\n")
        parts.append("\n请以JSON格式返回结果，只包含文本中明确提到的测量数据。格式如下：\n")
        parts.append("{\n")
        parts.append('  "卵圆孔(mm)": 3.7,\n')
        parts.append('  "心轴(°)": 39,\n')
        parts.append('  "二尖瓣-E(cm/s)": 37,\n')
        parts.append('  "三尖瓣-E(cm/s)": 37,\n')
        parts.append('  "二尖瓣-A(cm/s)": 53,\n')
        parts.append('  "三尖瓣-A(cm/s)": 58,\n')
        parts.append('  "主动脉(cm/s)": 88\n')
        parts.append("}\n\n")
        parts.append("注意事项：\n")
        parts.append("1. 只提取文本中明确提到的数值\n")
        parts.append("2. 数值要准确，包括小数点\n")
        parts.append("3. 单位要匹配正确的特征名称\n")
        parts.append("4. 如果某个指标在文本中提到但没有具体数值，不要包含在结果中\n")
        parts.append("5. 只返回JSON，不要有其他解释文字\n\n")
        parts.append("JSON结果：\n")
        extraction_prompt = "".join(parts)

        try:
            response_chunks = []
            for chunk in self.model_client.call_stream(extraction_prompt, temperature=0.1):
                response_chunks.append(chunk)
            full_response = "".join(response_chunks)
            json_match = re.search(r'\{[\s\S]*\}', full_response)
            if json_match:
                json_str = json_match.group(0)
                try:
                    extracted_data = json.loads(json_str)
                    validated_data = {}
                    for key, value in extracted_data.items():
                        std_key = FEATURE_ALIASES.get(key, key)
                        if std_key in ALL_POSSIBLE_FEATURES:
                            try:
                                validated_data[std_key] = float(value)
                            except (ValueError, TypeError):
                                continue
                    return validated_data
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON解析错误: {e}")
                    return self.extract_measurements_from_text_basic(text)
            else:
                logger.warning("未找到有效的JSON响应")
                return self.extract_measurements_from_text_basic(text)
        except Exception as e:
            logger.error(f"AI数据提取出错: {e}")
            return self.extract_measurements_from_text_basic(text)

    def extract_measurements_from_text_basic(self, text: str) -> Dict[str, float]:
        t = str(text)

        # 轻量清洗：全角转半角；去掉中文词内部多余空格（防止“三 尖瓣”“肺 静脉”）
        t = (t.replace('（', '(').replace('）', ')')
            .replace('：', ':').replace('，', ','))
        t = re.sub(r'(?<=[\u4e00-\u9fa5A-Za-z])\s+(?=[\u4e00-\u9fa5A-Za-z])', '', t)

        results: Dict[str, float] = {}

        # 1) 先用“字面量列名”一把梭（覆盖“指标(单位)数值”的场景）
        for pat, target in getattr(self, "_literal_col_patterns", []):
            m = pat.search(t)
            if m and target not in results:
                try:
                    results[target] = float(m.group(1))
                except Exception:
                    pass

        # 1.1) 心轴单位兜底（心轴(mm)35° 也能吃）
        if "心轴(°)" not in results:
            m = getattr(self, "_axis_fallback_pat", None).search(t) if hasattr(self, "_axis_fallback_pat") else None
            if m:
                try:
                    results["心轴(°)"] = float(m.group(1))
                except Exception:
                    pass

        # 1.2) 律齐提取并标准化到 {0,1}
        m = getattr(self, "_rhythm_pat", None).search(t) if hasattr(self, "_rhythm_pat") else None
        if m:
            v = str(m.group(1)).strip()
            if v.isdigit():
                results["律齐"] = 1 if int(v) != 0 else 0
            else:
                results["律齐"] = 1 if v in ("齐", "正常", "是") else 0

        # 2) 再跑原有的“宽松基础规则”，但避免覆盖已抽到的键
        for pat, target in getattr(self, "_basic_extract_patterns", []):
            if target in results:
                continue
            m = pat.search(t)
            if m:
                try:
                    results[target] = float(m.group(1))
                except Exception:
                    pass

        # 3) 原有组合项（保持不变）
        combo = [
            (re.compile(r'二尖瓣[-\s]*E[和与]三尖瓣[-\s]*E[都是为:=：\s]*(-?\d+\.?\d*)'),
            ['二尖瓣-E(cm/s)', '三尖瓣-E(cm/s)']),
            (re.compile(r'二尖瓣[-\s]*A[和与]三尖瓣[-\s]*A[都是为:=：\s]*(-?\d+\.?\d*)'),
            ['二尖瓣-A(cm/s)', '三尖瓣-A(cm/s)']),
        ]
        for pat, targets in combo:
            m = pat.search(t)
            if m:
                try:
                    v = float(m.group(1))
                    for tg in targets:
                        results.setdefault(tg, v)
                except Exception:
                    pass

        return results


    def extract_measurements_from_text(self, text: str) -> dict:
        # 1) LLM 先抽
        llm_kv = self._normalize_and_map_keys(self._llm_structured_extract(text))
        # 2) 规则兜底
        rule_kv = self._normalize_and_map_keys(self.extract_measurements_from_text_basic(text))

        # 3) 合并：LLM 优先；若两者差异 <10%，记均值以降噪
        out = dict(rule_kv)
        for k, v in llm_kv.items():
            if k not in out:
                out[k] = v
            else:
                rv = out[k]
                try:
                    if rv == 0 and v == 0:
                        out[k] = 0.0
                    elif rv == 0:
                        out[k] = v
                    else:
                        rel = abs(v - rv) / (abs(rv) + 1e-6)
                        out[k] = (v + rv) / 2.0 if rel <= 0.10 else v  # 10% 内取均值，否则信 LLM
                except Exception:
                    out[k] = v

        return out

    # ---------- Validation & Prompts ----------
    def _validate_query(self, query: Dict[str, float]) -> Dict[str, float]:
        validated_query = {}
        for col, value in query.items():
            if value is not None:
                try:
                    validated_query[col] = float(value)
                except (TypeError, ValueError):
                    continue
        return validated_query

    def _build_prompt(self, measurements: Dict[str, float]) -> str:
        prompt = f"""作为胎儿心脏病学专家，请分析以下超声测量数据：
{json.dumps(measurements, indent=2, ensure_ascii=False)}

关联临床数据库中的{len(self.df)}例相似病例，请：
1. 评估各指标异常程度
2. 给出可能的诊断建议
3. 建议后续检查方案

重要：只分析用户提供的数据，不要假设或添加用户未提供的信息。如果某些关键数据缺失，请在回答中指出并建议用户补充这些数据。"""
        return prompt
    def get_positive_case_types_from_bullets(self, bullets: List[str]) -> List[str]:
        """
        从“患病/可疑相似病例的超声提示”bullets中抽取规范病名清单（全量泛化），按优先级排序返回
        - 复用 _extract_positive_terms（已含否定消解/同义词映射/术语规范化）
        """
        if not bullets:
            return []
        text = "；".join([str(b) for b in bullets if b])
        term_map = self._extract_positive_terms(text) or {}
        names = set(term_map.keys())

        # 若词表未命中，使用启发式在自由文本中抓取疑似病名短语（避免局限于某一病种）
        if not names:
            # 否定词过滤
            neg_pat = re.compile(r"(未见|无明显|否认|未发现|除外|阴性)")
            # 末尾为疾病关键词的短语（中文）
            cand = re.findall(
                r"([\u4e00-\u9fa5A-Za-z0-9／/\-]{2,30}"
                 r"(?:缺如|离断|闭锁|未闭|反流|返流|增宽|扩大|扩张|憩室|室壁瘤|双出口|动脉弓离断|动脉弓中断|血管环|动脉干|共同动脉干|异位|异构|偏位|错位|畸形))",
                text
            )            
            
            for c in cand:
                if not neg_pat.search(c):
                    names.add(str(c).strip())


        # 排序：按优先级boost（若未配置则为1.0），并稳定化
        boost = getattr(self, "term_priority_boost", {}) or {}
        scored = [(n, float(boost.get(n, 1.0))) for n in names]
        scored.sort(key=lambda x: (-x[1], x[0]))
        return [n for n, _ in scored]  




    def _build_rag_prompt(
        self,
        query: Dict[str, float],
        similar_cases: List[Dict],
        user_question: str = "",
        disease_hint_bullets: Optional[List[str]] = None,
        pos_examples: Optional[List[str]] = None,
        top_case_hint: str = "",
        top_terms: Optional[List[Tuple[str, float]]] = None,
        positive_case_types: Optional[List[str]] = None,
        strong_evidences: Optional[List[str]] = None,  # ★ 新增
    ) -> Tuple[str, str]:




        system_prompt = """你是一位经验丰富的胎儿心脏超声专家，擅长分析胎儿心脏超声数据并提供专业诊断建议。
请根据提供的测量数据和相似病例参考，生成专业、准确的超声描述和超声提示。
【生成规则—务必遵守】：
- 必须把《重点参考》《代表性阳性提示示例》《优先参考病例》中的内容融入“超声提示”，
  在“超声提示”的开头输出《证据映射》小节，逐条写出【证据→结论要点】的对应关系；
- 若引用示例不足2条，仍需展示已识别到的全部示例；不得忽略给定证据；
- 超声提示开头必须包含【强证据（原文摘录）】与【证据映射】两个小节：
  1) 强证据（原文摘录）：逐条原样粘贴我给出的强证据，不得遗漏、不改写；
  2) 证据映射：逐条写出【证据 → 结论要点】；
  3) 大模型根据上述“强证据”和“证据映射”的推理。
你的回答应当且必须包含但不限于下述两部分：
    1. 超声描述：详细描述当前测量数据的异常程度和可能的解剖结构异常；
    2. 超声提示：提供具体的诊断建议和后续检查方案。

重要：只分析用户实际提供的数据，不要假设或添加用户未提供的信息；请尽量结合【重点参考——患病/可疑相似病例的超声提示】中的关键信息，优先输出潜在患病风险。请保持专业且可读。"""
        user_prompt = f"""## 用户问题
{user_question if user_question else "请分析以下胎儿超声数据，并提供诊断建议。"}

## 胎儿超声测量数据（用户提供的数据）
{json.dumps(query, indent=2, ensure_ascii=False)}

## 相似病例参考（基于{len(similar_cases)}例真实数据）
"""
        for i, case in enumerate(similar_cases):
            user_prompt += f"\n### 病例 {i+1} (相似度 {case['similarity_score']:.2f}):"
            if '数据来源' in case:
                user_prompt += f"\n- 数据来源: {case['数据来源']}"
            ultrasound_desc = self._truncate_after_cues(case.get('超声描述', 'N/A'))
            clinical_sugg   = self._truncate_after_cues(case.get('超声提示', 'N/A'))
            user_prompt += f"\n- 超声描述: {ultrasound_desc}"
            user_prompt += f"\n- 超声提示: {clinical_sugg}"
            user_prompt += "\n- 测量数据: "
            measurement_parts = []
            for col in query.keys():
                if col in case:
                    measurement_parts.append(f"{col}={case.get(col, 'N/A')}")
            user_prompt += ", ".join(measurement_parts)

        if disease_hint_bullets:
            user_prompt += "\n\n## 重点参考——患病/可疑相似病例的超声提示（加权摘要）\n"
            for b in disease_hint_bullets:
                user_prompt += f"- {b}\n"


        if strong_evidences:
            user_prompt += "\n\n## 强证据（原文摘录，不得遗漏，不改写）\n"
            for e in strong_evidences:
                user_prompt += f"- {e}\n"

        if pos_examples:
            user_prompt += "\n\n## 代表性阳性提示示例（高权重优先）\n"
            for s in pos_examples: user_prompt += f"- {s}\n"

        if top_case_hint:
            user_prompt += "\n\n## 优先参考病例（相似度≈100%）\n"
            user_prompt += top_case_hint + "\n"

        if top_terms:
            user_prompt += "\n\n## 可能的阳性术语（Top）\n"
            for term, w in top_terms: user_prompt += f"- {term}（权重{w:.2f}）\n"
        if positive_case_types:
            user_prompt += "\n\n## 阳性病例类型（直接用于生成‘超声提示’的病名清单）\n"
            for n in positive_case_types:
                user_prompt += f"- {n}\n"
            user_prompt += (
                "\n**务必要求**：在后续的“超声提示”中，不得遗漏以上病名；"
                "若与当前数据或影像矛盾，请在提示中给出不采纳/存疑的理由。"
    )


        user_prompt += """

请分析上述数据，并提供以下内容：

1. 超声描述：
   - 评估用户提供的心脏腔室和大血管的大小是否正常
   - 分析是否存在结构异常
   - 与正常参考值比较，指出异常程度
   - 只分析用户实际提供的数据，不要假设或添加未提供的信息

2. 超声提示：
   - 根据用户提供的测量数据和相似病例，优先输出可能的患病风险与诊断方向
   - 提供具体的后续检查建议（例如随访频率、遗传学检查、必要的胎儿心超/胎儿MRI等）
   - 如果用户提供的数据不足以做出完整诊断，请明确指出需要补充哪些检查

请确保你的回答专业、准确，并与相似病例的风格保持一致。"""
        return system_prompt, user_prompt

    
    # ---------- Summarization for positive similar cases (NEW) ----------
    def _strip_normal_phrase(self, s: str) -> str:
        """
        Remove 'normal' boilerplate phrases when we have abnormal/positive evidence.
        """
        if not s:
            return s
        # Common Chinese normal-conclusion variants
        pats = [
            r"目前胎儿心脏结构未见明显重大畸形[。；;,\n]*",
            r"胎儿心脏结构未见明显重大畸形[。；;,\n]*",
            r"未见明显重大畸形[。；;,\n]*",
            r"未见明显异常[。；;,\n]*",
        ]
        out = str(s)
        for p in pats:
            out = re.sub(p, "", out)
        return out.strip()

    def _split_clauses(self, text: str) -> List[str]:
        if not text:
            return []
        t = str(text).strip()
        # Normalize separators
        t = t.replace("\r", "\n")
        # First split by strong boundaries
        parts = re.split(r"[。\n；;！？!]+", t)
        clauses: List[str] = []
        for p in parts:
            p = p.strip()
            if not p:
                continue
            # Then split by weak boundaries
            subs = re.split(r"[，,、]+", p)
            for s in subs:
                s = s.strip()
                if 4 <= len(s) <= 60:
                    clauses.append(s)
        return clauses

    def _weighted_clause_summary(
        self,
        weighted_texts: List[Tuple[float, str]],
        max_items: int = 8,
        drop_if_contains: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Rule-based summary: pick top clauses by (weighted) frequency, then deduplicate by similarity.
        """
        if not weighted_texts:
            return []
        drop_if_contains = drop_if_contains or []
        pool: Dict[str, Dict[str, float]] = {}
        for w, txt in weighted_texts:
            for c in self._split_clauses(txt):
                if any(bad in c for bad in drop_if_contains):
                    continue
                key = self._normalize_text(c)
                if not key:
                    continue
                rec = pool.get(key)
                if rec is None:
                    pool[key] = {"w": float(w), "n": 1.0, "text": c}
                else:
                    rec["w"] += float(w)
                    rec["n"] += 1.0

        # rank by weight then count
        ranked = sorted(pool.values(), key=lambda r: (r["w"], r["n"], len(r["text"])), reverse=True)

        # dedup by normalized similarity
        selected: List[str] = []
        selected_norm: List[str] = []
        for r in ranked:
            cand = str(r["text"]).strip()
            cn = self._normalize_text(cand)
            if not cn:
                continue
            too_similar = False
            for sn in selected_norm:
                try:
                    if SequenceMatcher(None, cn, sn).ratio() >= 0.92:
                        too_similar = True
                        break
                except Exception:
                    pass
            if too_similar:
                continue
            selected.append(cand)
            selected_norm.append(cn)
            if len(selected) >= max_items:
                break
        return selected

    def summarize_positive_cases(
        self,
        similar_cases: List[Dict],
        max_items: int = 8,
        max_examples: int = 3,
        abnormal: bool = False,
    ) -> Dict[str, Any]:
        """
        Summarize *positive* (diseased/suspect) similar cases into:
        - hint_summary_bullets
        - desc_summary_bullets
        - representative raw examples (hint/desc)
        - positive_case_types (disease names)
        """
        pos = [c for c in (similar_cases or []) if self._is_diseased_case(c) in ("diseased", "suspect")]
        if not pos:
            return {
                "hint_summary_bullets": [],
                "desc_summary_bullets": [],
                "hint_examples": [],
                "desc_examples": [],
                "positive_case_types": [],
                "pos_count": 0
            }

        drop_phrases = ["未见明显重大畸形", "未见明显异常"] if abnormal else []
        weighted_hints = []
        weighted_descs = []
        hint_examples: List[str] = []
        desc_examples: List[str] = []

        for c in sorted(pos, key=lambda x: float(x.get("similarity_score", 0.0) or 0.0), reverse=True):
            w = float(c.get("similarity_score", 0.0) or 0.0)
            h = self._truncate_after_cues(str(c.get("超声提示", "") or "")).strip()
            d = self._truncate_after_cues(str(c.get("超声描述", "") or "")).strip()
            if h:
                weighted_hints.append((w, h))
            if d:
                weighted_descs.append((w, d))
            if h and len(hint_examples) < max_examples:
                hint_examples.append(h)
            if d and len(desc_examples) < max_examples:
                desc_examples.append(d)

        hint_bullets = self._weighted_clause_summary(weighted_hints, max_items=max_items, drop_if_contains=drop_phrases)
        desc_bullets = self._weighted_clause_summary(weighted_descs, max_items=max_items, drop_if_contains=drop_phrases)

        # disease names inferred from aggregated hints
        all_hint_text = "；".join([t for _, t in weighted_hints])
        positive_case_types = self.get_positive_case_types_from_bullets([all_hint_text]) if all_hint_text else []

        return {
            "hint_summary_bullets": hint_bullets,
            "desc_summary_bullets": desc_bullets,
            "hint_examples": hint_examples,
            "desc_examples": desc_examples,
            "positive_case_types": positive_case_types,
            "pos_count": len(pos)
        }

    def _build_rag_prompt_v2(
        self,
        query: Dict[str, float],
        user_question: str,
        positive_hint_summary: List[str],
        positive_desc_summary: List[str],
        positive_case_types: List[str],
        hint_examples: List[str],
        desc_examples: List[str],
        abnormal: bool,
        weighted_positive_ratio: float,
        diseased_count: int,
        suspect_count: int,
    ) -> Tuple[str, str]:
        """
        v2.1：让模型直接输出严格 JSON，避免 split(\"超声提示\") 造成“建议为空/只剩标题”。
        clinical_suggestion 必须：
        - 写成一个整体（单段，不要小标题/列表）
        - 在段首原样包含结构化数据引用字符串
        """

        def _fmt_num(v: Any) -> str:
            try:
                fv = float(v)
                if abs(fv - round(fv)) < 1e-9:
                    return str(int(round(fv)))
                return f"{fv:.3f}".rstrip("0").rstrip(".")
            except Exception:
                return str(v)

        structured_inline = "；".join([f"{k}={_fmt_num(v)}" for k, v in (query or {}).items()])

        system_prompt = """你是一位经验丰富的胎儿心脏超声专家。你必须只输出**严格 JSON**，不得输出任何额外文字或 Markdown。
JSON 必须包含两个键：
1) ultrasound_description：一段文字（不分点），说明当前需要重点关注的结构/血流方向，并明确哪些关键信息是用户未提供的（不得编造）。
2) clinical_suggestion：一段**连续文本**（不分小标题/列表），给出下一步检查与随访建议，必须融合：
   - 用户结构化数据引用（原样包含我给出的 structured_inline 字符串）
   - 相似阳性病例证据总结（提示+描述）
   - 阳性病例类型（若给出）
【证据约束】只能基于我提供的证据与数据，不得虚构测量值或影像结论。
【正常语句限制】若存在异常/阳性证据，禁止输出“目前胎儿心脏结构未见明显重大畸形”或同义表述。"""

        user_prompt = f"""用户问题：{user_question if user_question else '请结合数据与相似阳性病例证据，给出超声描述与建议。'}

用户结构化数据片段（JSON）：
{json.dumps(query, indent=2, ensure_ascii=False)}

请在 clinical_suggestion 段首**原样包含**以下结构化数据引用字符串（一个整体，不要拆成列表）：
{structured_inline}

相似病例聚合概览：
- 加权阳性占比：{weighted_positive_ratio:.2f}（阈值 {self.risk_threshold:.2f}）
- 患病/可疑病例数：{diseased_count}/{suspect_count}

相似阳性病例超声提示总结（多病例聚合）：
{chr(10).join(['- ' + s for s in (positive_hint_summary or [])]) if positive_hint_summary else '（未检索到可用于总结的阳性提示要点）'}

相似阳性病例超声描述总结（多病例聚合）：
{chr(10).join(['- ' + s for s in (positive_desc_summary or [])]) if positive_desc_summary else '（未检索到可用于总结的阳性描述要点）'}

阳性病例类型（病名/方向清单）：
{chr(10).join(['- ' + s for s in (positive_case_types or [])]) if positive_case_types else '（未能从提示总结中抽取到稳定的病名清单）'}

代表性原文示例（不改写，可在输出中用引号引用任意 1 条即可）：
- 超声提示示例：{(hint_examples[0] if hint_examples else '（无）')}
- 超声描述示例：{(desc_examples[0] if desc_examples else '（无）')}

请只输出严格 JSON，例如：
{{"ultrasound_description":"...","clinical_suggestion":"..."}}"""
        return system_prompt, user_prompt

# ---------- Polarity & aggregation utilities ----------
    def _negated(self, text: str, start_idx: int, window: int = None) -> bool:
        """简易否定消解：检查阳性术语前 window 个字符内是否有否定词"""
        if not text:
            return False
        w = self.neg_scope if window is None else window
        left = max(0, start_idx - w)
        ctx = text[left:start_idx]
        return any(n in ctx for n in self.negation_cues)

    def _concept_hit_in_text(self, canon: str, text: str) -> bool:
        if not text:
            return False
        s = str(text)
        nt = self._normalize_text(s)  # 已经很快；若传入的是 *_norm 列，可直接复用

        # 1) 正则直击，带否定窗口
        for pat in self.pos_regex_map.get(canon, []):
            for m in pat.finditer(s):
                if not self._negated(s, m.start()):
                    return True

        # 2) 别名：先原文直接包含（可做否定窗口判断）
        for alias in self.pos_alias_map.get(canon, []):
            pos = s.find(alias)
            if pos != -1:
                if not self._negated(s, pos):
                    return True

            # 3) 规范化后包含（不跑滑窗；极少数边界可略过）
            alias_n = self._normalize_text(alias)
            if alias_n and alias_n in nt:
                return True

            # 4) 仅在需要且未命中时，才考虑“相似度滑窗”（可通过 fast_text_match 开关）
            if not self.fast_text_match and self._fuzzy_contains(s, alias, self.semantic_ratio):
                return True

        return False


    def _extract_positive_terms(self, text: str) -> Dict[str, int]:
        """
        抽取未被否定的“规范标签”阳性术语计数（正则 or 语义近似）
        返回：{规范标签: 次数(命中记1)}
        """
        if not text:
            return {}
        counts: Dict[str, int] = {}
        for canon in self.pos_alias_map.keys():
            if self._concept_hit_in_text(canon, text):
                counts[canon] = 1
        return counts

    def _has_any_condition_in_hint(self, case_row: Dict) -> bool:
        """
        仅基于【超声提示】判断是否包含任一指定病名/缩写或其相似表述（未被否定）。
        满足则视为“阳性（diseased）” —— 对应用户新规则（语义近似）。
        """
        hint = str(case_row.get("超声提示_norm", "") or "") or str(case_row.get("超声提示", "") or "")
        if not hint.strip():
            return False
        pos_map = self._extract_positive_terms(hint)
        return sum(pos_map.values()) > 0

    def _case_polarity_score(self, case_row: Dict) -> float:
        """用于聚合权重：若任一阳性概念（提示/描述，含语义近似）出现则计为1，否则0"""
        text = (str(case_row.get("超声提示", "")) + " " + str(case_row.get("超声描述", ""))).strip()
        pos_map = self._extract_positive_terms(text)
        return 1.0 if sum(pos_map.values()) > 0 else 0.0

    def _is_diseased_case(self, case_row: Dict) -> str:
        """
        状态判断顺序：
        1) 显式标签列（若有）
        2) 仅看【超声提示】：若含任一阳性概念或相似表述（未被否定） => 'diseased'
        3) 否则：若（提示或描述）含阳性概念或相似表述 => 'suspect'
        4) 否则 => 'normal'
        """
        yes_like = {"1", "是", "阳性", "患病", "true", "True", "确诊", "有"}
        label_cols = ["是否患病", "是否阳性", "阳性", "患病", "诊断标签", "最终结论", "最终诊断", "诊断结果"]
        for col in label_cols:
            if col in case_row and str(case_row[col]).strip():
                val = str(case_row[col]).strip()
                if val in yes_like:
                    return "diseased"
                # 诊断文本也可能承载阳性信息
                if col in ["诊断", "最终诊断", "诊断结果", "最终结论", "诊断标签"]:
                    txt = str(val)
                    pm = self._extract_positive_terms(txt)
                    if sum(pm.values()) > 0:
                        return "diseased"

        # 新规：仅看【超声提示】（语义近似）
        if self._has_any_condition_in_hint(case_row):
            return "diseased"

        # 次级：提示/描述任一包含阳性（语义近似）则记为可疑
        text = (str(case_row.get("超声提示", "")) + " " + str(case_row.get("超声描述", ""))).strip()
        pos_map = self._extract_positive_terms(text)
        if sum(pos_map.values()) > 0:
            return "suspect"
        return "normal"

    def _aggregate_positive_signals(self, similar_cases: List[Dict]) -> Dict[str, object]:
        if not similar_cases:
            return {
                "weighted_positive_ratio": 0.0,
                "top_terms": [],
                "positive_examples": [],
                "top_case_positive_hint": "",
                "diseased_count": 0,
                "suspect_count": 0
            }

        wsum = 0.0
        psum = 0.0
        term_weight: Dict[str, float] = {}
        examples: List[Tuple[float, str]] = []
        diseased_count = 0
        suspect_count = 0

        for c in similar_cases:
            w = float(c.get("similarity_score", 0.0) or 0.0)
            wsum += w
            hint_text = str(c.get("超声提示", "") or "")
            all_text = (hint_text + " " + str(c.get("超声描述", "") or "")).strip()

            status = self._is_diseased_case(c)
            if status == "diseased":
                diseased_count += 1
            elif status == "suspect":
                suspect_count += 1

            # 仅基于“超声提示”字段抽取阳性术语，贴合临床书写
            term_map = self._extract_positive_terms(hint_text)
            if sum(term_map.values()) > 0:
                psum += w
                for canon, cnt in term_map.items():
                    term_weight[canon] = term_weight.get(canon, 0.0) + w * float(cnt)
                if hint_text:
                    examples.append((w, hint_text))

        weighted_positive_ratio = (psum / (wsum + 1e-8)) if wsum > 0 else 0.0
        top_terms = sorted(term_weight.items(), key=lambda x: x[1], reverse=True)[: self.topn_terms]

        examples_sorted = sorted(examples, key=lambda x: x[0], reverse=True)
        uniq = []
        seen = set()
        for _, t in examples_sorted:
            if t not in seen:
                uniq.append(t)
                seen.add(t)
            if len(uniq) >= self.max_examples:
                break

        top_case_positive_hint = ""
        if similar_cases:
            topc = similar_cases[0]
            if float(topc.get("similarity_score", 0.0)) >= 0.999:
                ttext = (str(topc.get("超声提示", "")) + " " + str(topc.get("超声描述", ""))).strip()
                if sum(self._extract_positive_terms(ttext).values()) > 0:
                    top_case_positive_hint = ttext

        return {
            "weighted_positive_ratio": float(weighted_positive_ratio),
            "top_terms": top_terms,
            "positive_examples": uniq,
            "top_case_positive_hint": top_case_positive_hint,
            "diseased_count": diseased_count,
            "suspect_count": suspect_count,
            "concept_weights": term_weight
        }



    # ---------- Similarity Search (weights + RBF) ----------
    def _zscore_cols(self, df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
        out = df[cols].copy()
        for c in cols:
            mu = self._col_mean.get(c, 0.0)
            sd = self._col_std.get(c, 1.0) or 1.0
            out[c] = (out[c] - mu) / sd
        return out

    def _get_weights(self, cols: List[str]) -> np.ndarray:
        w = np.array([self.feature_weights.get(c, 1.0) for c in cols], dtype=float)
        if self.sim_norm_w and np.isfinite(w).all() and w.mean() > 0:
            w = w / w.mean()
        return w


    def find_similar_cases(self, query: Dict[str, float], k: int = 10) -> List[Dict]:
        query = self._validate_query(query)
        if self.df.empty or not query:
            logger.warning("数据集为空或查询为空，无法查找相似病例")
            return []

        feats = [f for f in query.keys() if f in self.df.columns and f in NUMERIC_FEATURES]
        if not feats:
            logger.warning("无可用数值特征用于相似度计算")
            return []

        k = min(max(k, 1), len(self.df))

        # —— 使用一次性归一化的缓存，查询时只切片 ——
        if hasattr(self, "_Z_all") and not self._Z_all.empty:
            Z = self._Z_all[feats].to_numpy()
        else:
            # 极端兜底（基本不会走到）
            Z = self._zscore_cols(self.df, feats).to_numpy().astype(np.float32)

        qv = np.array([
            (query[f] - self._col_mean.get(f, 0.0)) / (self._col_std.get(f, 1.0) or 1.0)
            for f in feats
        ], dtype=np.float32).reshape(1, -1)

        w = self._get_weights(feats).astype(np.float32)  # 权重
        diff = (Z - qv) * w
        d = np.linalg.norm(diff, axis=1)

        sigma = (float(self.sim_sigma_cfg)
                if isinstance(self.sim_sigma_cfg, (int, float)) and float(self.sim_sigma_cfg) > 0
                else (np.median(d[d > 0]) if np.any(d > 0) else 1.0))
        sim = np.exp(-(d ** 2) / (2.0 * (sigma ** 2))).astype(np.float32)

        # —— 快速预选 Top-N（argpartition > argsort） ——
        pre_n = min(len(self.df), max(k * 3, 50))
        top_idx = np.argpartition(-sim, pre_n - 1)[:pre_n]
        pre_idx = top_idx[np.argsort(-sim[top_idx])]

        # —— 构建候选（先不在循环里过滤，避免 O(n²)） ——
        cands = []
        for i in pre_idx:
            row = self.df.iloc[int(i)].to_dict()
            row["similarity_score"] = float(sim[int(i)])
            cands.append(row)

        # 一次性过滤分数阈值

        min_score = getattr(self, "sim_min_score", 0.85)
        filtered = [row for row in cands if row["similarity_score"] >= min_score]
        if not filtered:
            # Fallback：没有达标的也给出相似度最高的一批，确保不为空
            cands.sort(key=lambda r: r["similarity_score"], reverse=True)
            filtered = cands[:max(5, k)]
        cands = filtered

        # 按来源分桶：患病优先（2）> 可疑（1）> 阴性（0），桶内按相似度
        def _status_weight(row: Dict) -> int:
            st = self._is_diseased_case(row)
            return 2 if st == "diseased" else (1 if st == "suspect" else 0)

        buckets = defaultdict(list)
        for row in cands:
            buckets[row.get("数据来源", "未知来源")].append((
                _status_weight(row), float(row["similarity_score"]), row
            ))
        for src in buckets:
            buckets[src].sort(key=lambda x: (x[0], x[1]), reverse=True)
            limit = max(1, (k + 2) // 3)
            buckets[src] = deque(buckets[src][:limit])

        # 轮询各来源，尽量覆盖更多来源
        out = []
        while len(out) < k and any(buckets.values()):
            progressed = False
            for src in list(buckets.keys()):
                if not buckets[src]:
                    continue
                status_w, sim_score, row = buckets[src].popleft()
                out.append(row)
                progressed = True
                if len(out) >= k:
                    break
            if not progressed:
                break

        return out[:k]


    # ---------- Similar report set rendering (ENHANCED) ----------
    def _status_tag(self, case_row: Dict) -> str:
        status = self._is_diseased_case(case_row)
        if status == "diseased":
            return "🔴患病"
        if status == "suspect":
            return "🟠可疑"
        return "🟢未见阳性"

    def render_similar_report_set(self, similar_cases: List[Dict], query: Dict[str, float], top_k: int = 10) -> str:
        if not similar_cases:
            return "### 最相似病例超声报告集合\n（未找到可参考的相似病例）"
        lines = ["### 最相似病例超声报告集合"]
        top_k = max(1, min(top_k, len(similar_cases)))
        for i, c in enumerate(similar_cases[:top_k], start=1):
            sim = float(c.get("similarity_score", 0.0) or 0.0)
            src = str(c.get("数据来源", "未知来源"))
            desc = (str(c.get("超声描述", "")).strip() or "（无记录）")
            hint = (str(c.get("超声提示", "")).strip() or "（无记录）")
            status = self._status_tag(c)
            measures = []
            for col in query.keys():
                if col in c:
                    val = c.get(col)
                    if isinstance(val, (int, float, np.integer, np.floating)) or (isinstance(val, str) and val.strip()):
                        measures.append(f"{col}={val}")
            measure_line = "，".join(measures) if measures else "（无可比对测量值）"
            lines.append(f"#### 病例{i} · 相似度 {sim:.2f} · {status} · {src}")
            lines.append(f"- 关键测量对比：{measure_line}")
            lines.append(f"- 超声描述：{desc}")
            lines.append(f"- 超声提示：{hint}")
        return "\n".join(lines)

    def get_disease_hint_bullets(self, similar_cases: List[Dict], max_items: int = 10) -> List[str]:
        if not similar_cases:
            return []
        candidates: List[Tuple[float, str]] = []
        for c in similar_cases:
            status = self._is_diseased_case(c)
            if status in ("diseased", "suspect"):
                w = float(c.get("similarity_score", 0.0) or 0.0)
                hint = (str(c.get("超声提示", "")) or "").strip()
                if not hint:
                    continue
                if status == "diseased":
                    w = w * 2  # 患病样本加权更高
                candidates.append((w, hint))
        if not candidates:
            return []
        uniq = []
        seen = set()
        for w, txt in sorted(candidates, key=lambda x: x[0], reverse=True):
            if txt not in seen:
                uniq.append(txt)
                seen.add(txt)
            if len(uniq) >= max_items:
                break
        return uniq





    def _fallback_reasoning_from_data(self, q: Dict[str, float]) -> Tuple[str, str]:
        """
        No similar-case evidence found.

        Per user requirement, avoid per-indicator abnormality judgement here; instead provide
        conservative, data-aware guidance and request missing key information.
        """
        head = "### 结构化信息概览（未检索到足够相似病例）"
        snippet = json.dumps(self._validate_query(q), indent=2, ensure_ascii=False)
        desc = f"{head}\n用户提供结构化数据片段：\n{snippet}"

        sugg = (
            "未能在当前数据库中检索到达到相似度阈值的可参考病例，因此无法基于相似病例给出稳健的风险聚合结论。\n"
            "建议结合超声形态学观察与临床背景综合判断，并在条件允许时补充/完善：\n"
            "1) 标准胎儿超声心动图（四腔心、三血管-气管、左右室流出道、大动脉弓、静脉回流）；\n"
            "2) 若存在家族史、合并畸形或产前筛查异常，可考虑遗传学咨询与染色体/基因检测；\n"
            "3) 随访复查频率按临床风险分层确定。\n"
            "如需更精确建议，请补充超声提示/描述原文以及关键测量值。"
        )
        return desc, sugg



    # ---------- Report ----------



    def generate_report(self, query: Dict[str, float], user_question: str = "") -> Dict[str, str]:
        """
        Report generation (v2):
        - Remove per-indicator abnormality judgement in the displayed analysis.
        - Focus on summarising ultrasound hints/descriptions from diseased/suspect similar cases.
        - Feed the summarised evidence + user structured snippet to the LLM for recommendations.
        """
        query = self._validate_query(query)
        if not query:
            return {
                "ultrasound_description": "未提供任何有效的超声测量数据。",
                "clinical_suggestion": "请提供至少一项超声测量数据以进行分析。",
                "full_response": "",
                "weighted_positive_ratio": 0.0,
                "top_positive_terms": [],
                "positive_examples": []
            }

        similar_cases = self.find_similar_cases(query, k=10)
        if not similar_cases:
            desc, sugg = self._fallback_reasoning_from_data(query)
            return {
                "ultrasound_description": desc,
                "clinical_suggestion": sugg,
                "full_response": "",
                "weighted_positive_ratio": 0.0,
                "top_positive_terms": [],
                "positive_examples": []
            }

        agg = self._aggregate_positive_signals(similar_cases)
        wpos = float(agg.get("weighted_positive_ratio", 0.0) or 0.0)
        diseased_count = int(agg.get("diseased_count", 0) or 0)
        suspect_count = int(agg.get("suspect_count", 0) or 0)

        abnormal_trigger = (
            (wpos >= float(self.risk_threshold))
            or (diseased_count > 0)
            or (suspect_count > 0)
            or bool(agg.get("top_case_positive_hint"))
        )

        pos_sum = self.summarize_positive_cases(
            similar_cases,
            max_items=min(10, int(getattr(self, "topn_terms", 10) or 10)),
            max_examples=min(3, int(getattr(self, "max_examples", 3) or 3)),
            abnormal=abnormal_trigger
        )

        hint_summary_bullets = pos_sum.get("hint_summary_bullets", []) or []
        desc_summary_bullets = pos_sum.get("desc_summary_bullets", []) or []
        hint_examples = pos_sum.get("hint_examples", []) or []
        desc_examples = pos_sum.get("desc_examples", []) or []
        positive_case_types = pos_sum.get("positive_case_types", []) or []

        if not positive_case_types:
            disease_hint_bullets = self.get_disease_hint_bullets(similar_cases, max_items=30)
            positive_case_types = self.get_positive_case_types_from_bullets(disease_hint_bullets)

        # inline structured snippet (used for prompting + fallback display)
        def _fmt_inline(q: Dict[str, float], max_items: int = 12) -> str:
            items = []
            for kk, vv in list((q or {}).items())[:max_items]:
                try:
                    fv = float(vv)
                    if abs(fv - round(fv)) < 1e-9:
                        sv = str(int(round(fv)))
                    else:
                        sv = f"{fv:.3f}".rstrip("0").rstrip(".")
                except Exception:
                    sv = str(vv)
                items.append(f"{kk}={sv}")
            return "；".join(items)

        structured_inline = _fmt_inline(query)

        # === LLM generation ===
        full_response = ""
        ultrasound_desc_llm = ""
        clinical_sugg_llm = ""

        if self.model_client:
            system_prompt, user_prompt = self._build_rag_prompt_v2(
                query=query,
                user_question=user_question,
                positive_hint_summary=hint_summary_bullets,
                positive_desc_summary=desc_summary_bullets,
                positive_case_types=positive_case_types,
                hint_examples=hint_examples,
                desc_examples=desc_examples,
                abnormal=abnormal_trigger,
                weighted_positive_ratio=wpos,
                diseased_count=diseased_count,
                suspect_count=suspect_count,
            )
            messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
            chunks: List[str] = []
            try:
                for ch in self.model_client.call_stream("", messages=messages, temperature=0.2):
                    chunks.append(ch)
                full_response = "".join(chunks).strip()
            except Exception as e:
                full_response = f"API调用出错: {str(e)}"

            # Parse LLM output (prefer strict JSON; fallback to loose section parsing)
            parsed_json = None
            m = re.search(r"\{[\s\S]*\}", full_response)
            if m:
                try:
                    parsed_json = json.loads(m.group(0))
                except Exception:
                    parsed_json = None

            if isinstance(parsed_json, dict):
                ultrasound_desc_llm = str(parsed_json.get("ultrasound_description", "") or "").strip()
                clinical_sugg_llm = str(parsed_json.get("clinical_suggestion", "") or "").strip()
            else:
                # Fallback: try to split by keywords; if still fails, treat entire output as suggestion
                desc_match = re.search(r"超声描述[:：]?\s*([\s\S]*?)(?=超声提示|$)", full_response)
                hint_match = re.search(r"超声提示[:：]?\s*([\s\S]*)$", full_response)
                ultrasound_desc_llm = (desc_match.group(1).strip() if desc_match else "").strip()
                clinical_sugg_llm = (hint_match.group(1).strip() if hint_match else full_response.strip())

            if abnormal_trigger:
                ultrasound_desc_llm = self._strip_normal_phrase(ultrasound_desc_llm)
                clinical_sugg_llm = self._strip_normal_phrase(clinical_sugg_llm)

        # === Build displayed analysis ===
        snippet = json.dumps(query, indent=2, ensure_ascii=False)

        blocks: List[str] = []
        blocks.append("### 用户结构化数据片段（原样引用）\n" + snippet)

        blocks.append("### 重点参考｜患病/可疑相似病例的超声提示总结（多病例聚合）\n" +
                      ("\n".join([f"- {s}" for s in hint_summary_bullets]) if hint_summary_bullets
                       else "（未检索到可用于总结的阳性提示要点）"))

        blocks.append("### 相似阳性案例的超声描述总结（多病例聚合）\n" +
                      ("\n".join([f"- {s}" for s in desc_summary_bullets]) if desc_summary_bullets
                       else "（未检索到可用于总结的阳性描述要点）"))

        if positive_case_types:
            blocks.append("### 阳性病例类型（病名/方向清单）\n" + "\n".join([f"- {s}" for s in positive_case_types]))

        if ultrasound_desc_llm:
            blocks.append("### 本例超声描述（模型生成，基于上述证据）\n" + ultrasound_desc_llm)

        ultrasound_description = "\n\n".join([b for b in blocks if b]).strip()

        # === Suggestions ===
        header = [
            "### 相似病例风险聚合（不做逐项阈值判读）",
            f"- 加权阳性占比：{wpos:.2f}（阈值 {self.risk_threshold:.2f}）",
            f"- 患病/可疑病例数：{diseased_count}/{suspect_count}",
        ]
        clinical_suggestion = "\n".join(header)

        if clinical_sugg_llm:
            # ensure the structured inline snippet appears in the suggestion as one whole
            if structured_inline and (structured_inline not in clinical_sugg_llm):
                clinical_sugg_llm = f"{structured_inline}。{clinical_sugg_llm}".strip()
            clinical_suggestion = (clinical_suggestion + "\n\n" + clinical_sugg_llm).strip()
        else:
            extra = (
                f"{structured_inline}。基于相似阳性/可疑病例证据总结（提示要点与描述要点），建议："
                "完善标准胎儿超声心动图分段扫查（四腔心、三血管-气管、左右室流出道、大动脉弓、静脉回流等），"
                "必要时在具备条件的中心进行复核/随访；若合并家族史、结构异常或筛查提示风险升高，可进行遗传学咨询与相应检测。"
            )
            if abnormal_trigger:
                extra += "（存在阳性/可疑相似病例证据，建议按阳性路径重点排查与复核。）"
            clinical_suggestion = (clinical_suggestion + "\n\n" + extra).strip()

        return {
            "ultrasound_description": ultrasound_description,
            "clinical_suggestion": clinical_suggestion,
            "full_response": full_response,
            "weighted_positive_ratio": wpos,
            "top_positive_terms": agg.get("top_terms", []) or [],
            "positive_examples": agg.get("positive_examples", []) or []
        }


    def _ai_parse_response(self, response: str) -> Dict[str, str]:
        if not self.model_client:
            return {}
        parse_prompt = f"""请将以下胎儿超声报告解析为"超声描述"和"超声提示"两部分：

{response}

请以JSON格式返回结果，格式如下：
{{
  "ultrasound_description": "这里是超声描述部分...",
  "clinical_suggestion": "这里是超声提示部分..."
}}

只返回JSON，不要有其他文字。"""
        try:
            parse_chunks = []
            for chunk in self.model_client.call_stream(parse_prompt, temperature=0.1):
                parse_chunks.append(chunk)
            parse_response = "".join(parse_chunks)
            json_match = re.search(r'\{[\s\S]*\}', parse_response)
            if json_match:
                return json.loads(json_match.group(0))
        except Exception as e:
            logger.warning(f"解析AI输出失败：{e}")
        return {}

    def _generate_suggestion_based_on_cases(self, cases: List[Dict]) -> str:
        if cases and '超声提示' in cases[0] and cases[0]['超声提示']:
            return f"超声提示：{cases[0]['超声提示']}"
        diagnoses = [c.get('diagnosis', '') for c in cases if 'diagnosis' in c and c['diagnosis']]
        if not diagnoses:
            return "超声提示：建议进一步完善超声心动图检查，明确心脏结构异常情况。"
        from collections import Counter
        common_diagnosis = Counter(diagnoses).most_common(1)[0][0]
        return f"超声提示：考虑{common_diagnosis}，建议完善超声心动图检查，必要时进行胎儿心脏MRI检查。"

    # ---------- Streaming with risk header ----------

    def analyze_with_rag(self, measurements: Dict[str, float], user_input: str) -> Iterator[str]:
        """
        Produce structured, evidence-only reasoning.
        FIX: Always surface disease risk candidates by concept_weights even if
        the weighted_positive_ratio does not pass the threshold.
        """
        similar_cases = self.find_similar_cases(measurements, k=10)
        agg = self._aggregate_positive_signals(similar_cases)
        yield "🔎 相似病例阳性聚合（先验提示）：\n"
        yield f"- 加权阳性占比：{agg['weighted_positive_ratio']:.2f}（阈值 {self.risk_threshold:.2f}）\n"
        yield f"- 患病/可疑病例数：{agg.get('diseased_count',0)}/{agg.get('suspect_count',0)}\n"

        # Always surface disease risk candidates
        if agg.get("concept_weights"):
            cw = agg["concept_weights"]
            top_c = sorted(cw.items(), key=lambda x: x[1], reverse=True)[: min(10, self.topn_terms)]
            if agg["weighted_positive_ratio"] >= self.risk_threshold:
                yield "### 疾病风险推断（基于邻域证据｜优先关注）\n"
            else:
                yield "### 疾病风险推断（证据有限，建议关注）\n"
            for name, w in top_c:
                yield f"- {name}（邻域加权证据 {w:.2f}）\n"

        if agg["top_terms"]:
            top_line = "；".join([f"{t}（权重{w:.2f}）" for t, w in agg["top_terms"]])
            yield f"- 可能阳性结果（Top-{len(agg['top_terms'])}）：{top_line}\n"
        if agg["top_case_positive_hint"]:
            yield f"- 与病例1相似度≈100%，优先参考阳性提示：{agg['top_case_positive_hint']}\n"
        if agg["positive_examples"]:
            yield "- 代表性阳性提示示例：\n"
            for s in agg["positive_examples"]:
                yield f"  • {s}\n"

        bullets = self.get_disease_hint_bullets(similar_cases, max_items=10)
        if bullets:
            yield "\n### 重点参考｜患病/可疑相似病例的超声提示（加权Top）\n"
            for b in bullets:
                yield f"- {b}\n"
            yield "\n"

        rel = self._mine_internal_relations(measurements, k=10)
        if rel["text"]:
            yield "### 数据内部关系挖掘（数据驱动）\n"
            yield rel["text"] + "\n\n"


        comp = self.analyze_composite_groups(measurements)
        if comp["text"]:
            yield "### 组合指标判读\n"
            yield comp["text"] + "\n\n"

        yield "### 结论（基于证据的可审计输出）\n"
        yield "以上结论严格基于：1) 用户提供的测量；2) 数据集中检索到的相似病例；3) 数据集统计派生的联合指标范围；4)根据提取出的证据映射结合AI模型进行推理 \n"








    def analyze_stream(self, measurements: Dict[str, float]) -> Iterator[str]:
        if not self.model_client:
            yield "错误：未配置大模型API密钥"
            return
        validated_measurements = self._validate_query(measurements)
        if not validated_measurements:
            yield "未提供任何有效的超声测量数据。请提供至少一项测量数据进行分析。"
            return
        prompt = self._build_prompt(validated_measurements)
        yield "开始胎儿心脏超声数据分析...\n"
        yield "="*40 + "\n"
        for chunk in self.model_client.call_stream(prompt):
            yield chunk
        yield "\n" + "="*40 + "\n"
        yield "分析完成，请结合临床判断"

    # ---------- Chat / Batch / Export ----------
    def chat(self, user_input: str) -> Iterator[str]:
        measurements = self.extract_measurements_from_text(user_input)
        if not measurements:
            yield "未能从您的描述中提取到任何超声测量数据。请提供具体的测量值，例如'卵圆孔是3.7，心轴：39°'。\n"
            yield "支持的格式包括：\n- 卵圆孔是3.7mm\n- 心轴：39°\n- 二尖瓣-E和三尖瓣-E都是37\n- 主动脉：88\n"
            return

        yield "✅ 从您的描述中提取到以下测量数据：\n"
        for feature, value in measurements.items():
            yield f"- {feature}: {value}\n"
        yield "\n"

        similar_cases = self.find_similar_cases(measurements)
        agg = self._aggregate_positive_signals(similar_cases)
        yield "🔎 相似病例阳性聚合（先验提示）：\n"
        yield f"- 加权阳性占比：{agg['weighted_positive_ratio']:.2f}（阈值 {self.risk_threshold:.2f}）\n"
        yield f"- 患病/可疑病例数：{agg.get('diseased_count',0)}/{agg.get('suspect_count',0)}\n"
        if agg["top_terms"]:
            top_line = "；".join([f"{t}（权重{w:.2f}）" for t, w in agg["top_terms"]])
            yield f"- 可能阳性结果（Top-{len(agg['top_terms'])}）：{top_line}\n"
        if agg["top_case_positive_hint"]:
            yield f"- 与病例1相似度≈100%，优先参考阳性提示：{agg['top_case_positive_hint']}\n"
        if agg["positive_examples"]:
            yield "- 代表性阳性提示示例：\n"
            for s in agg["positive_examples"]:
                yield f"  • {s}\n"

        bullets = self.get_disease_hint_bullets(similar_cases, max_items=10)
        if bullets:
            yield "\n### 重点参考｜患病/可疑相似病例的超声提示（加权Top）\n"
            for b in bullets:
                yield f"- {b}\n"
            yield "\n"

        for chunk in self.analyze_with_rag(measurements, user_input):
            yield chunk

    def analyze_user_input(self, user_input: str) -> Tuple[Dict[str, float], Dict[str, str]]:
        extracted_features = self.extract_measurements_from_text(user_input)
        if not extracted_features:
            response_chunks = []
            prompt = f"""作为胎儿心脏病学专家，请回答以下问题：
{user_input}

请注意，用户没有提供具体的超声测量数据，请给出一般性的专业建议。
不要假设用户有任何未明确提供的数据。"""
            try:
                for chunk in (self.model_client.call_stream(prompt, temperature=0.3) if self.model_client else []):
                    response_chunks.append(chunk)
                full_response = "".join(response_chunks) if response_chunks else "请完善超声测量数据后再咨询。"
                return {}, {"ultrasound_description": "", "clinical_suggestion": full_response}
            except Exception as e:
                return {}, {"ultrasound_description": "", "clinical_suggestion": f"处理您的问题时出现错误：{str(e)}"}
        report = self.generate_report(extracted_features, user_input)
        return extracted_features, report

    def get_data_sources_info(self) -> str:
        if self.df.empty:
            return "未加载任何数据"
        if '数据来源' in self.df.columns:
            sources = self.df['数据来源'].value_counts()
            info = "数据来源统计：\n"
            for source, count in sources.items():
                info += f"- {source}: {count}条记录\n"
            return info
        else:
            return f"总共加载了{len(self.df)}条记录"

    def get_available_features(self) -> List[str]:
        return ALL_POSSIBLE_FEATURES.copy()

    def demo_extraction(self, demo_text: str = None) -> None:
        if demo_text is None:
            demo_text = "卵圆孔是3.7，心轴：39°，二尖瓣-E和三尖瓣-E都是37，二尖瓣-A：53，三尖瓣-A：58，主动脉：88"
        print(f"演示文本: {demo_text}")
        print("-" * 50)
        print("🤖 AI增强提取结果:")
        ai_results = self.extract_measurements_from_text_with_ai(demo_text)
        for feature, value in ai_results.items():
            print(f"  - {feature}: {value}")
        print("\n📝 基础正则提取结果:")
        basic_results = self.extract_measurements_from_text_basic(demo_text)
        for feature, value in basic_results.items():
            print(f"  - {feature}: {value}")
        print("\n🔄 综合提取结果:")
        final_results = self.extract_measurements_from_text(demo_text)
        for feature, value in final_results.items():
            print(f"  - {feature}: {value}")

    def batch_analyze(self, input_texts: List[str]) -> List[Tuple[Dict[str, float], Dict[str, str]]]:
        results = []
        for i, text in enumerate(input_texts):
            logger.info(f"正在处理第 {i+1}/{len(input_texts)} 个文本...")
            try:
                features, report = self.analyze_user_input(text)
                results.append((features, report))
            except Exception as e:
                logger.error(f"处理文本 {i+1} 时出错: {e}")
                results.append(({}, {"ultrasound_description": "", "clinical_suggestion": f"处理出错: {str(e)}"}))
        return results

    def export_analysis_results(self, results: List[Tuple[Dict[str, float], Dict[str, str]]],
                               output_path: str = "analysis_results.xlsx") -> None:
        try:
            export_data = []
            for i, (features, report) in enumerate(results):
                row = {"序号": i+1}
                row.update(features)
                row["超声描述"] = report.get("ultrasound_description", "")
                row["超声提示"] = report.get("clinical_suggestion", "")
                export_data.append(row)
            df_export = pd.DataFrame(export_data)
            df_export.to_excel(output_path, index=False)
            print(f"分析结果已导出到: {output_path}")   
        except Exception as e:
            print(f"导出失败: {e}")

# ---------------- CLI ----------------
def main():
    import argparse
    parser = argparse.ArgumentParser(description="胎儿先心病诊断分析系统 - 语义阳性匹配（兼容非标准表述）")
    parser.add_argument("--api_key", help="Xhang API密钥（也可用环境变量 XHANG_API_KEY）")
    parser.add_argument("--config", help="配置文件路径（.yaml/.yml/.json）")
    parser.add_argument("--cache", action="store_true", help="启用Parquet缓存（优先级高于配置）")
    parser.add_argument("--cache_path", type=str, help="Parquet缓存路径（优先级高于配置）")
    parser.add_argument("--refresh_cache", action="store_true", help="忽略已有缓存，强制刷新")
    parser.add_argument("--demo", action="store_true", help="运行数据提取演示")
    parser.add_argument("--demo_text", type=str, help="自定义演示文本")
    args = parser.parse_args()

    try:
        api_key = args.api_key or os.getenv("XHANG_API_KEY")
        if not api_key:
            print("❌ 未提供 API Key。请使用 --api_key 或设置环境变量 XHANG_API_KEY")
            return

        print("正在初始化胎儿先心病诊断分析系统...")
        analyzer = FetalCHDAnalyzer(
            model_api_key=api_key,
            config_path=args.config,
            use_cache=args.cache,
            cache_path=args.cache_path,
            refresh_cache=args.refresh_cache,
        )

        if args.demo:
            print("\n" + "="*60)
            print("数据提取功能演示")
            print("="*60)
            analyzer.demo_extraction(args.demo_text)
            return

        print("\n" + "="*60)
        print("欢迎使用胎儿先心病结构化数据辅助诊断分析系统！")
        print("📝 示例：'卵圆孔是3.7，心轴：39°，二尖瓣-E和三尖瓣-E都是37，二尖瓣-A：53，三尖瓣-A：58，主动脉：88'")
        print("💡 输入 'help' 查看帮助，'demo' 看演示，'退出' 结束")
        print("-" * 60)

        while True:
            user_input = input("\n🩺 您的描述: ")
            if user_input.lower() in ["退出", "exit", "quit"]:
                print("👋 再见！")
                break
            elif user_input.lower() == "help":
                print("\n📖 帮助：输入带数值的超声描述；'demo' 看提取演示；'features' 查看指标；'info' 数据源统计")
                continue
            elif user_input.lower() == "demo":
                print("\n🔍 数据提取功能演示：")
                analyzer.demo_extraction()
                continue
            elif user_input.lower() == "features":
                features = analyzer.get_available_features()
                print(f"\n📋 系统支持的 {len(features)} 个指标：")
                for i, feature in enumerate(features, 1):
                    print(f"  {i:2d}. {feature}")
                    if i % 5 == 0:
                        print()
                continue
            elif user_input.lower() == "info":
                print(f"\n📊 {analyzer.get_data_sources_info()}")
                continue

            print("\n🔄 系统分析中...")
            print("=" * 50)
            try:
                kv = analyzer.extract_measurements_from_text(user_input)
                print(f"🔎 已提取数据: {kv}")
                report = analyzer.generate_report(kv, user_input)
                print(report.get("ultrasound_description", ""))
                print(report.get("clinical_suggestion", ""))
            except Exception as e:
                print(f"\n❌ 分析过程中出现错误: {e}")
                import traceback
                traceback.print_exc()
            print("\n" + "=" * 50)
            print("✅ 分析完成，请结合临床判断使用")
    except Exception as e:
        import traceback
        print(f"❌ 程序运行出错: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
