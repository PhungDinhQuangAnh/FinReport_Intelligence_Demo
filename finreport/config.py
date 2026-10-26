from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
METADATA = ROOT / "data" / "metadata"
SAMPLES = ROOT / "data" / "samples"
TEMPLATES = ROOT / "data" / "templates"
OUTPUTS = ROOT / "outputs"
KEY = ["company_id", "fiscal_year"]
TABLES = ["income_statement", "balance_sheet", "cashflow", "financial_notes"]
MODEL_NAME = "FINREPORT_INTELLIGENCE_Gold_equal14_v1.1"
MODEL_VERSION = "1.1.0"
PROJECT_LEVEL = "GOLD"

# Gold controls. These are transparent heuristics, not statistical probabilities.
GOLD_HIGH_THRESHOLD = 0.25
GOLD_CRITICAL_THRESHOLD = 0.68
ANOMALY_Z_THRESHOLD = 1.5
