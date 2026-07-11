from app.control_map import map_controls
from app.models import RiskHit

def test_secret_maps_to_owasp_and_pdpl():
    ctrls = map_controls("RETIRE", [RiskHit(category="secret", match="AKIA...", severity="high")])
    joined = " ".join(ctrls)
    assert "OWASP LLM02" in joined
    assert "NIST" in joined

def test_pii_maps_to_privacy_frameworks():
    ctrls = map_controls("RETIRE", [RiskHit(category="pii", match="x@y.z", severity="medium")])
    joined = " ".join(ctrls)
    assert "EU AI Act" in joined
    assert "PDPL" in joined

def test_keep_with_no_risk_still_records_governance_control():
    ctrls = map_controls("KEEP", [])
    assert any("SR 26-2" in c or "NIST GOVERN" in c for c in ctrls)
