"""Dual-domain evaluation and benchmarking engine for Milestone 1.4.

Executes a standardized benchmark suite across Factual, Procedural, Comparative,
and Unavailable-information categories in Cloud/DevOps and Healthcare domains.
Measures Top-1, Top-3, Top-5 retrieval accuracy and logs results to CSV.
"""

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.retrieval.search import SemanticSearchEngine

RESULTS_CSV_PATH = Path("evaluation/evaluation_results.csv")

# Standard 20-query dual-domain benchmark suite
BENCHMARK_QUERIES = [
    # Cloud/DevOps - Factual
    {
        "id": "Q-CLOUD-01",
        "domain": "cloud_devops",
        "category": "factual",
        "query": "What is the role of etcd in Kubernetes cluster architecture?",
        "expected_doc": "kubernetes_cluster_setup.txt",
        "expected_keywords": ["etcd", "key-value", "backing store"],
        "is_available": True,
    },
    {
        "id": "Q-CLOUD-02",
        "domain": "cloud_devops",
        "category": "factual",
        "query": "Which worker node component maintains network rules and pod communication?",
        "expected_doc": "kubernetes_cluster_setup.txt",
        "expected_keywords": ["kube-proxy", "network rules"],
        "is_available": True,
    },
    # Cloud/DevOps - Procedural
    {
        "id": "Q-CLOUD-03",
        "domain": "cloud_devops",
        "category": "procedural",
        "query": "What automated action occurs when a container image fails security vulnerability scan?",
        "expected_doc": "ci_cd_deployment_pipeline.docx",
        "expected_keywords": ["quarantine", "vulnerability", "cve"],
        "is_available": True,
    },
    {
        "id": "Q-CLOUD-04",
        "domain": "cloud_devops",
        "category": "procedural",
        "query": "What are the canary rollout verification criteria in deployment pipeline?",
        "expected_doc": "ci_cd_deployment_pipeline.docx",
        "expected_keywords": ["canary", "5xx error rate", "10%"],
        "is_available": True,
    },
    # Cloud/DevOps - Comparative
    {
        "id": "Q-CLOUD-05",
        "domain": "cloud_devops",
        "category": "comparative",
        "query": "Compare the MTTR between etcd network latency spike and containerd disk pressure incidents.",
        "expected_doc": "server_incident_metrics.csv",
        "expected_keywords": ["INC-102", "INC-103", "mttr"],
        "is_available": True,
    },
    {
        "id": "Q-CLOUD-06",
        "domain": "cloud_devops",
        "category": "comparative",
        "query": "Compare the responsibilities of kubelet versus kube-proxy on worker nodes.",
        "expected_doc": "kubernetes_cluster_setup.txt",
        "expected_keywords": ["kubelet", "kube-proxy"],
        "is_available": True,
    },
    # Cloud/DevOps - PDF Policy
    {
        "id": "Q-CLOUD-07",
        "domain": "cloud_devops",
        "category": "factual",
        "query": "What encryption protocol is required for inter-service communication under zero trust policy?",
        "expected_doc": "network_security_policy.pdf",
        "expected_keywords": ["mutual tls", "mtls", "encrypted"],
        "is_available": True,
    },
    # Cloud/DevOps - Unavailable / Out-of-Domain
    {
        "id": "Q-CLOUD-08",
        "domain": "cloud_devops",
        "category": "unavailable",
        "query": "How do you install Apache Cassandra database on bare-metal FreeBSD servers?",
        "expected_doc": None,
        "expected_keywords": [],
        "is_available": False,
    },
    {
        "id": "Q-CLOUD-09",
        "domain": "cloud_devops",
        "category": "unavailable",
        "query": "What are the rules and field positions of professional test cricket?",
        "expected_doc": None,
        "expected_keywords": [],
        "is_available": False,
    },
    {
        "id": "Q-CLOUD-10",
        "domain": "cloud_devops",
        "category": "unavailable",
        "query": "What is the historical timeline of mainframes developed by IBM in 1965?",
        "expected_doc": None,
        "expected_keywords": [],
        "is_available": False,
    },
    # Healthcare - Factual
    {
        "id": "Q-HEALTH-01",
        "domain": "healthcare",
        "category": "factual",
        "query": "How many healthy volunteers participate in Phase 1 clinical trial safety evaluations?",
        "expected_doc": "clinical_trial_protocol.txt",
        "expected_keywords": ["20 to 80", "healthy volunteers", "phase i"],
        "is_available": True,
    },
    {
        "id": "Q-HEALTH-02",
        "domain": "healthcare",
        "category": "factual",
        "query": "What is the primary concern of clinical investigations according to Declaration of Helsinki?",
        "expected_doc": "clinical_trial_protocol.txt",
        "expected_keywords": ["rights, safety", "well-being", "helsinki"],
        "is_available": True,
    },
    # Healthcare - Procedural
    {
        "id": "Q-HEALTH-03",
        "domain": "healthcare",
        "category": "procedural",
        "query": "What is the initial evaluation timeframe for ESI Level 2 Emergent triage patients?",
        "expected_doc": "hospital_patient_triage_guidelines.docx",
        "expected_keywords": ["within 10 minutes", "level 2", "emergent"],
        "is_available": True,
    },
    {
        "id": "Q-HEALTH-04",
        "domain": "healthcare",
        "category": "procedural",
        "query": "What are the mandatory disclosure requirements for informed consent before trial enrollment?",
        "expected_doc": "clinical_trial_protocol.txt",
        "expected_keywords": ["written disclosures", "risks", "voluntary withdrawal"],
        "is_available": True,
    },
    # Healthcare - Comparative
    {
        "id": "Q-HEALTH-05",
        "domain": "healthcare",
        "category": "comparative",
        "query": "Compare normal resting heart rate ranges for neonates versus adults.",
        "expected_doc": "vital_signs_reference_ranges.csv",
        "expected_keywords": ["neonate", "adult", "100", "180", "60"],
        "is_available": True,
    },
    {
        "id": "Q-HEALTH-06",
        "domain": "healthcare",
        "category": "comparative",
        "query": "Compare triage priority between severe cardiac arrest and a simple wrist laceration.",
        "expected_doc": "hospital_patient_triage_guidelines.docx",
        "expected_keywords": ["level 1", "level 4", "wrist laceration"],
        "is_available": True,
    },
    # Healthcare - PDF Schedule
    {
        "id": "Q-HEALTH-07",
        "domain": "healthcare",
        "category": "factual",
        "query": "Which vaccine is administered within twenty-four hours of birth in pediatric schedule?",
        "expected_doc": "pediatric_vaccination_schedule.pdf",
        "expected_keywords": ["hepatitis b", "birth", "twenty-four"],
        "is_available": True,
    },
    # Healthcare - Unavailable / Out-of-Domain
    {
        "id": "Q-HEALTH-08",
        "domain": "healthcare",
        "category": "unavailable",
        "query": "What is the exact dosage of chemotherapy drug Doxorubicin for feline leukemia virus?",
        "expected_doc": None,
        "expected_keywords": [],
        "is_available": False,
    },
    {
        "id": "Q-HEALTH-09",
        "domain": "healthcare",
        "category": "unavailable",
        "query": "How do you bake a sourdough bread loaf with Dutch oven technique?",
        "expected_doc": None,
        "expected_keywords": [],
        "is_available": False,
    },
    # Healthcare - Partial / Broad
    {
        "id": "Q-HEALTH-10",
        "domain": "healthcare",
        "category": "factual",
        "query": "What physiological vital signs and blood pressure parameters are monitored?",
        "expected_doc": "vital_signs_reference_ranges.csv",
        "expected_keywords": ["systolic", "diastolic", "heart rate"],
        "is_available": True,
    },
]


class DualDomainEvaluator:
    def __init__(
        self,
        db_path: Optional[str] = None,
        similarity_threshold: float = 0.35,
        output_csv_path: Path = RESULTS_CSV_PATH,
    ):
        self.search_engine = SemanticSearchEngine(db_path=db_path)
        self.similarity_threshold = similarity_threshold
        self.output_csv_path = output_csv_path

    def run_benchmark(self, queries: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute benchmark suite and calculate factual Top-1/3/5 accuracy metrics.
        
        Returns:
            Dict containing per-query results, metric aggregates, and CSV file path.
        """
        suite = queries or BENCHMARK_QUERIES
        self.output_csv_path.parent.mkdir(parents=True, exist_ok=True)

        results = []
        available_count = 0
        top_1_hits = 0
        top_3_hits = 0
        top_5_hits = 0

        unavailable_count = 0
        unavailable_correctly_rejected = 0

        for q in suite:
            query_id = q["id"]
            domain = q["domain"]
            category = q["category"]
            query_text = q["query"]
            expected_doc = q["expected_doc"]
            is_available = q["is_available"]

            search_res = self.search_engine.search(
                query_text=query_text,
                top_k=5,
                similarity_threshold=self.similarity_threshold,
                log_to_db=False,
            )

            max_score = search_res.max_similarity_score
            retrieved = search_res.retrieved_chunks

            # Check if expected document appears in Top-K
            top_1_match = False
            top_3_match = False
            top_5_match = False

            if is_available and expected_doc:
                available_count += 1
                doc_ranks = [c.document_name for c in retrieved]
                
                if doc_ranks and doc_ranks[0] == expected_doc:
                    top_1_match = True
                    top_1_hits += 1
                if any(d == expected_doc for d in doc_ranks[:3]):
                    top_3_match = True
                    top_3_hits += 1
                if any(d == expected_doc for d in doc_ranks[:5]):
                    top_5_match = True
                    top_5_hits += 1
            else:
                unavailable_count += 1
                # Successfully rejected if no chunks survived threshold
                if not search_res.has_sufficient_context or len(retrieved) == 0:
                    unavailable_correctly_rejected += 1

            actual_top_1_doc = retrieved[0].document_name if retrieved else "None"
            results.append(
                {
                    "query_id": query_id,
                    "domain": domain,
                    "category": category,
                    "query_text": query_text,
                    "expected_doc": expected_doc or "None (Unavailable)",
                    "actual_top_1_doc": actual_top_1_doc,
                    "max_similarity_score": max_score,
                    "threshold_applied": self.similarity_threshold,
                    "status": search_res.status,
                    "has_sufficient_context": search_res.has_sufficient_context,
                    "top_1_match": top_1_match if is_available else (not search_res.has_sufficient_context),
                    "top_3_match": top_3_match if is_available else (not search_res.has_sufficient_context),
                    "top_5_match": top_5_match if is_available else (not search_res.has_sufficient_context),
                }
            )

        # Accuracy calculations
        top_1_acc = (top_1_hits / available_count * 100.0) if available_count > 0 else 0.0
        top_3_acc = (top_3_hits / available_count * 100.0) if available_count > 0 else 0.0
        top_5_acc = (top_5_hits / available_count * 100.0) if available_count > 0 else 0.0
        rejection_acc = (
            (unavailable_correctly_rejected / unavailable_count * 100.0)
            if unavailable_count > 0
            else 0.0
        )

        # Write to CSV
        fieldnames = [
            "query_id",
            "domain",
            "category",
            "query_text",
            "expected_doc",
            "actual_top_1_doc",
            "max_similarity_score",
            "threshold_applied",
            "status",
            "has_sufficient_context",
            "top_1_match",
            "top_3_match",
            "top_5_match",
        ]
        with open(self.output_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

        summary = {
            "total_queries": len(suite),
            "relevant_queries": available_count,
            "unavailable_queries": unavailable_count,
            "top_1_accuracy": round(top_1_acc, 2),
            "top_3_accuracy": round(top_3_acc, 2),
            "top_5_accuracy": round(top_5_acc, 2),
            "unavailable_rejection_accuracy": round(rejection_acc, 2),
            "similarity_threshold": self.similarity_threshold,
            "results_csv": str(self.output_csv_path),
            "detailed_results": results,
        }
        return summary

