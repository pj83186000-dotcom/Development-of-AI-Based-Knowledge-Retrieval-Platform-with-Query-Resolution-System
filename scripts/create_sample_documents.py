"""Script to generate fictional educational sample documents across Cloud/DevOps and Healthcare domains in PDF, DOCX, TXT, and CSV formats."""

import os
from pathlib import Path
import docx
import pandas as pd


def create_pdf(output_path: Path, title: str, paragraphs: list) -> None:
    """Generate a clean standard single/multi-line PDF document with text."""
    stream_content = []
    stream_content.append("BT")
    stream_content.append("/F1 16 Tf")
    stream_content.append("50 750 Td")
    stream_content.append(f"({title}) Tj")
    stream_content.append("/F1 10 Tf")
    stream_content.append("0 -24 Td")
    
    for para in paragraphs:
        # Wrap words roughly to fit page width
        words = para.split()
        line = []
        for w in words:
            if len(" ".join(line + [w])) > 80:
                safe_str = " ".join(line).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
                stream_content.append(f"({safe_str}) Tj")
                stream_content.append("0 -14 Td")
                line = [w]
            else:
                line.append(w)
        if line:
            safe_str = " ".join(line).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            stream_content.append(f"({safe_str}) Tj")
            stream_content.append("0 -18 Td")
            
    stream_content.append("ET")
    stream_bytes = "\n".join(stream_content).encode("latin-1")
    
    obj4 = b"4 0 obj\n<< /Length " + str(len(stream_bytes)).encode("ascii") + b" >>\nstream\n" + stream_bytes + b"\nendstream\nendobj\n"
    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    obj5 = b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    
    header = b"%PDF-1.4\n"
    o1_pos = len(header)
    o2_pos = o1_pos + len(obj1)
    o3_pos = o2_pos + len(obj2)
    o4_pos = o3_pos + len(obj3)
    o5_pos = o4_pos + len(obj4)
    xref_pos = o5_pos + len(obj5)
    
    xref = (
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        + f"{o1_pos:010d} 00000 n \n".encode("ascii")
        + f"{o2_pos:010d} 00000 n \n".encode("ascii")
        + f"{o3_pos:010d} 00000 n \n".encode("ascii")
        + f"{o4_pos:010d} 00000 n \n".encode("ascii")
        + f"{o5_pos:010d} 00000 n \n".encode("ascii")
    )
    trailer = b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n" + str(xref_pos).encode("ascii") + b"\n%%EOF\n"
    
    data = header + obj1 + obj2 + obj3 + obj4 + obj5 + xref + trailer
    with open(output_path, "wb") as f:
        f.write(data)


def generate_cloud_devops_docs(base_dir: Path) -> None:
    target_dir = base_dir / "cloud_devops"
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. TXT Document
    txt_content = """# Kubernetes Cluster Architecture and Setup Guide

1. Overview of Kubernetes Architecture
Kubernetes is a portable, extensible open-source platform for managing containerized workloads and services. The system groups application containers into logical units called Pods for easy management and discovery. The architecture is split between a control plane and worker nodes.

2. Control Plane Components
The control plane makes global decisions about the cluster, such as workload scheduling, detecting node failures, and responding to cluster events:
- kube-apiserver: Exposes the Kubernetes API and serves as the front end for control plane communications.
- etcd: Consistent and highly-available key-value store used as Kubernetes backing store for all cluster state data.
- kube-scheduler: Watches for newly created Pods with no assigned node and selects an optimal node for them to run on.
- kube-controller-manager: Runs controller processes including node controller, job controller, and endpoint controller.

3. Worker Node Architecture
Worker node components run on every node, maintaining running pods and providing runtime environments:
- kubelet: An agent that runs on each node in the cluster, ensuring that containers are running in a Pod according to PodSpecs.
- kube-proxy: A network proxy that runs on each node, maintaining network rules to allow network communication to Pods from inside or outside the cluster.
- Container Runtime: Software responsible for running containers (e.g., containerd or CRI-O).
"""
    with open(target_dir / "kubernetes_cluster_setup.txt", "w", encoding="utf-8") as f:
        f.write(txt_content)
        
    # 2. DOCX Document
    doc = docx.Document()
    doc.add_heading("Continuous Integration and Deployment Pipeline Specification", level=1)
    doc.add_paragraph(
        "Modern cloud-native software delivery relies on automated CI/CD pipelines to validate, build, and deploy services with minimal manual intervention. The pipeline enforces rigorous code quality checks, static analysis, unit test coverage, and automated security scans before artifacts are promoted to staging or production environments."
    )
    doc.add_heading("Automated Verification Stages", level=2)
    doc.add_paragraph(
        "Each commit triggers an automated pipeline consisting of linting, unit testing, container image building, and container vulnerability scanning. Automated tests must achieve at least 85% branch coverage before deployment gates open. If any security scanner identifies a critical CVE vulnerability, the pipeline halts immediately and notifies the on-call engineer."
    )
    doc.add_heading("Deployment Verification Matrix", level=2)
    table = doc.add_table(rows=1, cols=4)
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Pipeline Stage"
    hdr_cells[1].text = "Target SLA"
    hdr_cells[2].text = "Validation Gate"
    hdr_cells[3].text = "Automated Action"
    
    stages = [
        ("Source Lint & Unit Tests", "3 minutes", "100% pass, 85% coverage", "Block merge on failure"),
        ("Container Image Build", "5 minutes", "Multi-stage Docker build", "Push to secure registry"),
        ("Security Vulnerability Scan", "2 minutes", "Zero critical/high CVEs", "Quarantine infected image"),
        ("Canary Rollout (10%)", "10 minutes", "HTTP 5xx error rate < 0.1%", "Promote to 100% or rollback"),
    ]
    for stage, sla, gate, action in stages:
        row_cells = table.add_row().cells
        row_cells[0].text = stage
        row_cells[1].text = sla
        row_cells[2].text = gate
        row_cells[3].text = action
        
    doc.save(target_dir / "ci_cd_deployment_pipeline.docx")
    
    # 3. CSV Document
    df = pd.DataFrame([
        {"incident_id": "INC-101", "node": "worker-pool-01", "severity": "P1", "component": "kube-proxy", "mttr_mins": 14, "root_cause": "OOM killer terminated network proxy pod"},
        {"incident_id": "INC-102", "node": "worker-pool-03", "severity": "P2", "component": "containerd", "mttr_mins": 25, "root_cause": "Disk pressure due to unrotated container logs"},
        {"incident_id": "INC-103", "node": "control-plane-01", "severity": "P1", "component": "etcd", "mttr_mins": 8, "root_cause": "Network latency spike between etcd quorum members"},
        {"incident_id": "INC-104", "node": "worker-pool-02", "severity": "P3", "component": "coredns", "mttr_mins": 19, "root_cause": "DNS upstream resolver connection timeout"},
        {"incident_id": "INC-105", "node": "ingress-gw-01", "severity": "P2", "component": "envoy-proxy", "mttr_mins": 12, "root_cause": "TLS certificate secret renewal lock contention"}
    ])
    df.to_csv(target_dir / "server_incident_metrics.csv", index=False)
    
    # 4. PDF Document
    create_pdf(
        target_dir / "network_security_policy.pdf",
        "Cloud Network Security and Zero-Trust Policy",
        [
            "This educational document establishes baseline network security rules for cloud cluster environments.",
            "All inter-service traffic must be encrypted in transit using Mutual TLS (mTLS) with strict certificate rotation.",
            "Default network policies require denying all ingress and egress communications unless explicitly whitelisted.",
            "Database nodes must reside in isolated private subnets accessible only by authenticated application pods.",
            "Administrative cluster access requires multifactor authentication and short-lived bastion host bastion session tokens."
        ]
    )


def generate_healthcare_docs(base_dir: Path) -> None:
    target_dir = base_dir / "healthcare"
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. TXT Document
    txt_content = """# Clinical Trial Protocol and Good Clinical Practice Guidelines

1. Scope and Ethical Principles
Clinical research must adhere to ethical standards established by the Declaration of Helsinki and the International Council for Harmonisation (ICH) Good Clinical Practice guidelines. The primary concern in all clinical investigations is protecting the rights, safety, and well-being of trial subjects.

2. Phases of Clinical Investigation
- Phase I (Safety and Pharmacokinetics): Involves small groups of healthy volunteers (20 to 80 participants) to evaluate drug safety, safe dosage ranges, and metabolic side effects.
- Phase II (Efficacy and Dose Ranging): Evaluates therapeutic efficacy in larger cohorts (100 to 300 patients) with the targeted disease state to identify optimal dosing regimens.
- Phase III (Confirmatory Trials): Comprehensive randomized multi-center trials involving 1,000 to 3,000 subjects to confirm effectiveness against standard of care and monitor adverse reactions.
- Phase IV (Post-Marketing Surveillance): Ongoing observational studies after regulatory approval to detect rare long-term safety signals across diverse populations.

3. Informed Consent Protocols
Prospective trial participants must receive comprehensive written disclosures detailing trial objectives, expected benefits, known risks, alternative treatments, and voluntary withdrawal rights prior to enrollment.
"""
    with open(target_dir / "clinical_trial_protocol.txt", "w", encoding="utf-8") as f:
        f.write(txt_content)
        
    # 2. DOCX Document
    doc = docx.Document()
    doc.add_heading("Emergency Department Patient Triage Guidelines", level=1)
    doc.add_paragraph(
        "Triage is an essential clinical assessment methodology utilized in emergency care to categorize patient urgency upon presentation. The primary objective is ensuring that critically ill or unstable patients receive immediate medical intervention while safely prioritizing lower acuity individuals."
    )
    doc.add_heading("Emergency Severity Index (ESI) Acuity Tiers", level=2)
    doc.add_paragraph(
        "The Emergency Severity Index stratifies patients into five distinct acuity tiers based on clinical acuity and anticipated resource utilization. Triage nurses assess chief complaints, physiological vital signs, and pain scores to assign the appropriate category."
    )
    doc.add_heading("Triage Acuity Classification Matrix", level=2)
    table = doc.add_table(rows=1, cols=4)
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Acuity Level"
    hdr_cells[1].text = "Clinical Definition"
    hdr_cells[2].text = "Initial Evaluation Time"
    hdr_cells[3].text = "Example Presentation"
    
    tiers = [
        ("Level 1: Resuscitation", "Immediate life-threatening instability", "Immediate (0 minutes)", "Cardiac arrest, severe respiratory arrest"),
        ("Level 2: Emergent", "High-risk, confused, or severe distress", "Within 10 minutes", "Chest pain with diaphoresis, acute stroke signs"),
        ("Level 3: Urgent", "Requires two or more healthcare resources", "Within 30 minutes", "Abdominal pain requiring labs and CT imaging"),
        ("Level 4: Less Urgent", "Requires one diagnostic resource", "Within 60 minutes", "Simple wrist laceration requiring single suture"),
        ("Level 5: Non-Urgent", "Requires zero diagnostic resources", "Within 120 minutes", "Prescription refill, minor rash without fever"),
    ]
    for tier, definition, eval_time, example in tiers:
        row_cells = table.add_row().cells
        row_cells[0].text = tier
        row_cells[1].text = definition
        row_cells[2].text = eval_time
        row_cells[3].text = example
        
    doc.save(target_dir / "hospital_patient_triage_guidelines.docx")
    
    # 3. CSV Document
    df = pd.DataFrame([
        {"age_group": "Neonate (0-28 days)", "hr_min_bpm": 100, "hr_max_bpm": 180, "systolic_min_mmhg": 60, "systolic_max_mmhg": 90, "diastolic_min_mmhg": 30, "diastolic_max_mmhg": 60, "resp_min": 30, "resp_max": 60},
        {"age_group": "Infant (1-12 months)", "hr_min_bpm": 80, "hr_max_bpm": 150, "systolic_min_mmhg": 70, "systolic_max_mmhg": 100, "diastolic_min_mmhg": 45, "diastolic_max_mmhg": 65, "resp_min": 25, "resp_max": 40},
        {"age_group": "Toddler (1-3 years)", "hr_min_bpm": 70, "hr_max_bpm": 130, "systolic_min_mmhg": 80, "systolic_max_mmhg": 110, "diastolic_min_mmhg": 50, "diastolic_max_mmhg": 70, "resp_min": 20, "resp_max": 30},
        {"age_group": "School Age (6-12 years)", "hr_min_bpm": 65, "hr_max_bpm": 110, "systolic_min_mmhg": 90, "systolic_max_mmhg": 120, "diastolic_min_mmhg": 60, "diastolic_max_mmhg": 80, "resp_min": 16, "resp_max": 24},
        {"age_group": "Adult (18+ years)", "hr_min_bpm": 60, "hr_max_bpm": 100, "systolic_min_mmhg": 90, "systolic_max_mmhg": 120, "diastolic_min_mmhg": 60, "diastolic_max_mmhg": 80, "resp_min": 12, "resp_max": 20}
    ])
    df.to_csv(target_dir / "vital_signs_reference_ranges.csv", index=False)
    
    # 4. PDF Document
    create_pdf(
        target_dir / "pediatric_vaccination_schedule.pdf",
        "Pediatric Immunization Reference Schedule",
        [
            "This educational reference provides standard pediatric immunization milestone schedules.",
            "Birth Milestone: Hepatitis B initial dose administered within twenty-four hours of birth.",
            "Two Months: DTaP, Inactivated Poliovirus (IPV), Haemophilus influenzae type b (Hib), and Pneumococcal conjugate.",
            "Six Months: Third dose series completion alongside annual seasonal influenza immunization initiation.",
            "Twelve Months: Measles, Mumps, Rubella (MMR) and Varicella initial live-attenuated vaccinations.",
            "All immunizations must be documented with vaccine manufacturer, lot number, and anatomical administration site."
        ]
    )


if __name__ == "__main__":
    base = Path("sample_documents")
    generate_cloud_devops_docs(base)
    generate_healthcare_docs(base)
    print("All sample documents successfully generated!")

