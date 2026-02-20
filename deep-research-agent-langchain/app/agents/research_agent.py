import json
from datetime import datetime
from typing import List, Dict, Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
try:
    # Prefer the classic package for memory in LangChain 1.x.
    from langchain_classic.memory import ConversationBufferMemory
except Exception:
    try:
        # Fallback to newer LangChain memory module when available.
        from langchain.memory import ConversationBufferMemory
    except Exception:
        try:
            # Fallback to community package if available.
            from langchain_community.memory import ConversationBufferMemory
        except Exception:
            # Minimal fallback memory to keep the agent running.
            class ConversationBufferMemory:
                def __init__(self, return_messages: bool = True) -> None:
                    self._items = []

                def save_context(self, inputs, outputs) -> None:
                    self._items.append(inputs.get("input", ""))

                def load_memory_variables(self, _):
                    return {"history": self._items}

from app.config import HF_TOKEN, HF_MODEL
from app.schemas.models import (
    TaskSpec,
    Plan,
    SubQuestion,
    Evidence,
    Claim,
    SubQuestionBriefing,
    Briefing,
    EvidenceConstraints,
)
from app.tools.search import search_web
from app.tools.fetch import fetch_page
from app.tools.files import ingest_files
from app.memory.store import build_vectorstore
from app.utils.logging import get_logger

logger = get_logger("deep_research_agent")


class DeepResearchAgent:
    def __init__(self) -> None:
        self.llm = ChatOpenAI(
            api_key=HF_TOKEN,
            base_url="https://router.huggingface.co/v1",
            model=HF_MODEL,
        )
        self.memory = ConversationBufferMemory(return_messages=True)

    def run(self, question: str, file_paths: List[str], constraints: Dict[str, Any] | None, mode: str = "briefing") -> str:
        task = TaskSpec(question=question, evidence_constraints=self._to_constraints(constraints))
        self.memory.save_context({"input": question}, {"output": ""})
        plan = self._plan(task)
        notes = self._execute(plan, task, file_paths)
        final = None
        for _ in range(plan.max_iterations):
            draft = self._synthesize(task, plan, notes)
            feedback = self._reflect(plan, draft)
            final, notes = self._revise(task, plan, notes, feedback)
            if not feedback.get("follow_up_queries"):
                break
        final = final or self._synthesize(task, plan, notes)
        if mode == "essay":
            return self._essay(task, plan, final)
        return self._format(final)

    def _plan(self, task: TaskSpec) -> Plan:
        prompt = self._read_prompt("plan")
        content = self._fill_prompt(prompt, question=task.question, history=self._memory_text())
        response = self.llm.invoke([HumanMessage(content=content)])
        data = self._parse_json(response.content)
        sub_questions = [SubQuestion(**item) for item in data.get("sub_questions", [])]
        if not sub_questions:
            sub_questions = [SubQuestion(text=task.question, priority=1)]
        return Plan(
            sub_questions=sub_questions,
            success_criteria=data.get("success_criteria", []),
            max_iterations=int(data.get("max_iterations", 2)),
            confidence_threshold=float(data.get("confidence_threshold", 0.65)),
            evidence_constraints=self._to_constraints(data.get("evidence_constraints")) or task.evidence_constraints,
        )

    def _execute(self, plan: Plan, task: TaskSpec, file_paths: List[str]) -> Dict[str, List[Evidence]]:
        notes: Dict[str, List[Evidence]] = {}
        for sub in sorted(plan.sub_questions, key=lambda s: s.priority):
            evidence = self._gather(sub, plan.evidence_constraints)
            notes[sub.text] = self._dedupe(evidence)
        # Optional file ingestion
        if file_paths:
            docs = ingest_files(file_paths)
            for doc in docs:
                ev = Evidence(
                    url=doc.get("title", "local_file"),
                    title=doc.get("title", "local_file"),
                    snippet=doc.get("content", "")[:200],
                    captured_at=datetime.utcnow().isoformat(),
                    source_type="local_file",
                    relevance=0.6,
                    freshness=0.5,
                    trust=0.7,
                    score=0.6,
                )
                notes.setdefault(task.question, []).append(ev)
        # Optional long-term memory
        try:
            all_text = [ev.snippet for evs in notes.values() for ev in evs]
            build_vectorstore(all_text)
        except Exception:
            pass
        return notes

    def _synthesize(self, task: TaskSpec, plan: Plan, notes: Dict[str, List[Evidence]]) -> Briefing:
        findings: List[SubQuestionBriefing] = []
        sources: List[Evidence] = []
        uncertainties: List[str] = []
        for sub in plan.sub_questions:
            evs = sorted(notes.get(sub.text, []), key=lambda e: e.score, reverse=True)[:5]
            sources.extend(evs)
            synth = self._llm_synthesize(sub.text, evs)
            claim = Claim(
                text=synth.get("claim", "Insufficient evidence."),
                support=evs,
                uncertainty=synth.get("uncertainty", ""),
                confidence=float(synth.get("confidence", 0.3)),
            )
            findings.append(SubQuestionBriefing(sub_question=sub.text, claim=claim))
            if claim.uncertainty:
                uncertainties.append(f"{sub.text}: {claim.uncertainty}")
        metrics = self._metrics(findings, plan)
        return Briefing(
            title=f"Briefing: {task.question}",
            overview=f"This briefing addresses: {task.question}",
            findings=findings,
            uncertainties=uncertainties,
            sources=self._dedupe(sources),
            metrics=metrics,
        )

    def _reflect(self, plan: Plan, briefing: Briefing) -> Dict[str, Any]:
        prompt = self._read_prompt("critic")
        content = self._fill_prompt(
            prompt,
            sub_questions=[s.text for s in plan.sub_questions],
            overview=briefing.overview,
            findings=[f.claim.text for f in briefing.findings],
            uncertainties=briefing.uncertainties,
            sources=[e.url for e in briefing.sources],
            constraints=plan.evidence_constraints,
        )
        response = self.llm.invoke([HumanMessage(content=content)])
        data = self._parse_json(response.content)
        if data.get("evidence_constraints"):
            logger.info("Inferred evidence constraints: %s", data["evidence_constraints"])
        return data

    def _revise(self, task: TaskSpec, plan: Plan, notes: Dict[str, List[Evidence]], feedback: Dict[str, Any]):
        followups = feedback.get("follow_up_queries", {})
        inferred = feedback.get("evidence_constraints", {})
        merged_constraints = self._merge_constraints(plan.evidence_constraints, inferred.get("global"))
        if merged_constraints:
            logger.info("Applying evidence constraints: %s", merged_constraints)
        for sub in plan.sub_questions:
            extra_queries = followups.get(sub.text, [])
            if not extra_queries:
                continue
            per_sub = inferred.get("by_sub_question", {}).get(sub.text)
            effective = self._merge_constraints(merged_constraints, per_sub)
            extra = self._gather(sub, effective, extra_queries)
            notes[sub.text] = self._dedupe(notes.get(sub.text, []) + extra)
        return self._synthesize(task, plan, notes), notes

    def _gather(self, sub: SubQuestion, constraints: EvidenceConstraints | None, queries: List[str] | None = None):
        evidence: List[Evidence] = []
        queries = queries or sub.query_variants or self._query_variants(sub)
        for q in queries:
            urls = search_web(q, constraints=constraints.model_dump() if constraints else None)
            for url in urls:
                meta = fetch_page(url)
                source_type = self._infer_source_type(url, meta.get("title", ""), meta.get("content", ""))
                if constraints and not self._passes_constraints(constraints, source_type, meta.get("content", ""), url):
                    logger.info("Ignored evidence due to constraints: %s", url)
                    continue
                evidence.append(self._build_evidence(url, meta, source_type, sub.text))
        return evidence

    def _build_evidence(self, url: str, meta: Dict[str, str], source_type: str, query: str) -> Evidence:
        content = meta.get("content", "")
        relevance = self._score_relevance(query, content)
        freshness = 0.6
        trust = 0.6
        score = round((relevance + freshness + trust) / 3.0, 3)
        return Evidence(
            url=url,
            title=meta.get("title", url),
            snippet=content[:200],
            captured_at=datetime.utcnow().isoformat(),
            source_type=source_type,
            relevance=relevance,
            freshness=freshness,
            trust=trust,
            score=score,
        )

    def _llm_synthesize(self, sub_question: str, evidence: List[Evidence]) -> Dict[str, Any]:
        prompt = self._read_prompt("synthesis")
        payload = [{"url": e.url, "title": e.title, "snippet": e.snippet} for e in evidence]
        content = self._fill_prompt(prompt, sub_question=sub_question, evidence=payload)
        response = self.llm.invoke([HumanMessage(content=content)])
        return self._parse_json(response.content)

    def _read_prompt(self, name: str) -> str:
        path = f"app/prompts/{name}.txt"
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _fill_prompt(self, template: str, **kwargs) -> str:
        # Safe replacement for prompt placeholders without formatting JSON braces.
        text = template
        for key, value in kwargs.items():
            text = text.replace("{" + key + "}", str(value))
        return text

    def _parse_json(self, text: str) -> Dict[str, Any]:
        try:
            return json.loads(text)
        except Exception:
            return {}

    def _dedupe(self, items: List[Evidence]) -> List[Evidence]:
        by_url = {}
        for item in items:
            existing = by_url.get(item.url)
            if existing is None or item.score > existing.score:
                by_url[item.url] = item
        return list(by_url.values())

    def _query_variants(self, sub: SubQuestion) -> List[str]:
        base = [sub.text, f"{sub.text} overview", f"{sub.text} survey"]
        for t in sub.tactics:
            base.append(f"{sub.text} {t}")
        return list(dict.fromkeys([q for q in base if q]))

    def _score_relevance(self, query: str, content: str) -> float:
        qt = set(query.lower().split())
        ct = set(content.lower().split()[:400])
        if not qt or not ct:
            return 0.1
        return round(len(qt.intersection(ct)) / max(len(qt), 1), 3)

    def _infer_source_type(self, url: str, title: str, content: str) -> str:
        low = f"{url} {title} {content[:500]}".lower()
        if "arxiv" in low or "biorxiv" in low or "medrxiv" in low:
            return "preprint"
        if "doi.org" in low or "journal" in low or "proceedings" in low:
            return "peer_reviewed"
        if "wikipedia.org" in low or "encyclopedia" in low:
            return "encyclopedia"
        if "news" in low or "press" in low:
            return "news"
        if "blog" in low or "medium.com" in low:
            return "blog"
        return "other"

    def _passes_constraints(self, constraints: EvidenceConstraints, source_type: str, content: str, url: str) -> bool:
        if constraints.source_types and source_type not in constraints.source_types:
            return False
        if constraints.time_range:
            years = []
            for token in (url + " " + content[:500]).split():
                if token.isdigit() and len(token) == 4:
                    years.append(int(token))
            if years:
                latest = max(years)
                start = constraints.time_range.get("start_year")
                end = constraints.time_range.get("end_year")
                if start and latest < start:
                    return False
                if end and latest > end:
                    return False
        return True

    def _metrics(self, findings: List[SubQuestionBriefing], plan: Plan) -> Dict[str, Any]:
        if not findings:
            return {"coverage": 0.0, "average_confidence": 0.0}
        confidences = [f.claim.confidence for f in findings]
        covered = [c for c in confidences if c >= plan.confidence_threshold]
        return {
            "coverage": round(len(covered) / max(len(confidences), 1), 3),
            "average_confidence": round(sum(confidences) / max(len(confidences), 1), 3),
        }

    def _format(self, briefing: Briefing) -> str:
        lines = [briefing.title, "", "Overview:", briefing.overview, "", "Key Findings:"]
        for item in briefing.findings:
            lines.append(f"- {item.sub_question}")
            lines.append(f"  Claim: {item.claim.text}")
            lines.append(f"  Confidence: {item.claim.confidence}")
            if item.claim.uncertainty:
                lines.append(f"  Uncertainty: {item.claim.uncertainty}")
            if item.claim.support:
                lines.append("  Evidence:")
                for ev in item.claim.support:
                    lines.append(f"  - {ev.title} | {ev.url} | {ev.source_type} | {ev.snippet}")
        lines.append("")
        lines.append("Sources:")
        seen = set()
        for ev in briefing.sources:
            if ev.url in seen:
                continue
            seen.add(ev.url)
            lines.append(f"- {ev.title} | {ev.url} | {ev.source_type} | {ev.snippet}")
        if briefing.metrics:
            lines.append("")
            lines.append("Metrics:")
            for k, v in briefing.metrics.items():
                lines.append(f"- {k}: {v}")
        return "\n".join(lines)

    def _essay(self, task: TaskSpec, plan: Plan, briefing: Briefing) -> str:
        prompt = self._read_prompt("essay")
        findings = [
            {
                "sub_question": f.sub_question,
                "claim": f.claim.text,
                "uncertainty": f.claim.uncertainty,
                "confidence": f.claim.confidence,
            }
            for f in briefing.findings
        ]
        evidence = [
            {"id": i + 1, "title": e.title, "url": e.url, "snippet": e.snippet}
            for i, e in enumerate(briefing.sources)
        ]
        content = self._fill_prompt(prompt, question=task.question, findings=findings, evidence=evidence)
        response = self.llm.invoke([HumanMessage(content=content)])
        return response.content

    def _memory_text(self) -> str:
        messages = self.memory.load_memory_variables({}).get("history", [])
        if not messages:
            return ""
        return " ".join([m.content for m in messages if hasattr(m, "content")])

    def _merge_constraints(self, base: EvidenceConstraints | None, override: Dict[str, Any] | None) -> EvidenceConstraints | None:
        if not base and not override:
            return None
        merged = base.model_dump() if base else {}
        if override:
            for k, v in override.items():
                if v is not None:
                    merged[k] = v
        return EvidenceConstraints(**merged)

    def _to_constraints(self, raw: Dict[str, Any] | None) -> EvidenceConstraints | None:
        if not raw:
            return None
        try:
            return EvidenceConstraints(**raw)
        except Exception:
            return None
