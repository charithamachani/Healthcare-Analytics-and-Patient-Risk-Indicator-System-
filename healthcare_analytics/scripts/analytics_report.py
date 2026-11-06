"""Build the operational analytics report: charts + Markdown.  Run: python -m scripts.analytics_report"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")                                  # draw to files, no window needed
import matplotlib.pyplot as plt

from app import analytics
from app.config import default_database_url
from app.constants import DISCLAIMER, LIMITATIONS
from app.db import get_engine
from app.rules import COMPOSITE_CODE, describe_rules
from app.validation import MEASURE_SPECS

OUT = Path("reports")
FOOTER = "Synthetic data - educational only - not clinical"


def save(fig, name):
    fig.text(0.5, 0.005, FOOTER, ha="center", fontsize=8, color="gray")
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(OUT / name, dpi=130)
    plt.close(fig)


def md_table(df):
    head = "| " + " | ".join(map(str, df.columns)) + " |\n"
    sep = "|" + "---|" * len(df.columns) + "\n"
    body = "".join("| " + " | ".join(map(str, r)) + " |\n" for r in df.itertuples(index=False))
    return head + sep + body


def chart_departments(dept):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    outpatient = dept["visits"] - dept["admissions"]
    ax.bar(dept["department_name"], outpatient, label="Outpatient")
    ax.bar(dept["department_name"], dept["admissions"], bottom=outpatient, label="Admissions")
    ax.set(title="Visits by department (2025, synthetic)", ylabel="Number of visits")
    ax.legend()
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    save(fig, "visits_by_department.png")


def chart_monthly(monthly, by_dept):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    axes[0].plot(monthly["month"], monthly["visits"], marker="o", label="All visits")
    axes[0].plot(monthly["month"], monthly["admissions"], marker="s", label="Admissions")
    axes[0].set(title="Monthly visits and admissions", ylabel="Count")
    axes[0].legend()
    for dept in by_dept.columns:
        axes[1].plot(by_dept.index, by_dept[dept], marker=".", label=dept)
    axes[1].set(title="Monthly visits by department", ylabel="Count")
    axes[1].legend(fontsize=8)
    for ax in axes:
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    save(fig, "monthly_visit_trends.png")


def chart_measure_trends(trend):
    fig, axes = plt.subplots(2, 3, figsize=(14, 7))
    for ax, (mtype, spec) in zip(axes.ravel(), MEASURE_SPECS.items()):
        t = trend[trend["measure_type"] == mtype]
        ax.plot(t["month"], t["mean"], marker="o")
        ax.fill_between(t["month"], t["mean"] - t["std"], t["mean"] + t["std"], alpha=0.2)
        ax.set(title=f"{spec['label']} (monthly mean ± 1 SD)", ylabel=spec["unit"])
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    save(fig, "measurement_trends.png")


def chart_distributions(meas):
    fig, axes = plt.subplots(2, 3, figsize=(14, 7))
    for ax, (mtype, spec) in zip(axes.ravel(), MEASURE_SPECS.items()):
        ax.hist(meas.loc[meas["measure_type"] == mtype, "value"], bins=30, edgecolor="white")
        ax.set(title=spec["label"], xlabel=spec["unit"], ylabel="Readings")
    save(fig, "measurement_distributions.png")


def chart_indicators(summary):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    d = summary["flag_count_distribution"]
    axes[0].bar([str(x["flag_count"]) for x in d], [x["patients"] for x in d])
    axes[0].set(title="Patients by number of illustrative flags", xlabel="Flags fired", ylabel="Patients")
    rules = summary["patients_per_rule"]
    axes[1].barh(list(rules.keys()), list(rules.values()))
    axes[1].set(title="Patients per rule (illustrative)", xlabel="Patients")
    axes[1].invert_yaxis()
    save(fig, "indicator_summary.png")


def main():
    OUT.mkdir(exist_ok=True)
    f = analytics.load_frames(get_engine(default_database_url()))
    dept = analytics.visits_by_department(f["visits"], f["departments"])
    monthly = analytics.monthly_visits(f["visits"])
    by_dept = analytics.monthly_visits_by_department(f["visits"], f["departments"])
    meas_summary = analytics.measurement_summary(f["measurements"])
    trend = analytics.monthly_measurement_trend(f["measurements"])
    ind = analytics.indicator_summary(f["risk_indicators"])

    chart_departments(dept)
    chart_monthly(monthly, by_dept)
    chart_measure_trends(trend)
    chart_distributions(f["measurements"])
    chart_indicators(ind)

    rejected_path = Path("data/rejected_measurements.csv")
    quality = ""
    if rejected_path.exists():
        import pandas as pd
        rej = pd.read_csv(rejected_path)
        kinds = rej["reject_reason"].str.replace(r"[\d.-]+", "#", regex=True).value_counts()
        quality = (f"{len(rej)} raw readings were rejected during cleaning:\n\n"
                   + md_table(kinds.rename_axis("reason").reset_index(name="rows")))

    peak = monthly.loc[monthly["visits"].idxmax()]
    top = dept.iloc[0]
    dist = ind["flag_count_distribution"]
    lines = [
        "# Operational Analytics Report (synthetic data)\n",
        f"> **{DISCLAIMER}**\n",
        "## 1. Data overview\n",
        f"- Patients: {len(f['patients'])}\n- Visits: {len(f['visits'])}\n"
        f"- Valid measurements: {len(f['measurements'])}\n",
        "## 2. Data quality\n", quality or "No rejection log found.\n",
        "\n## 3. Department admissions and visits\n",
        f"The busiest department was **{top['department_name']}** with {top['visits']} visits. "
        f"The busiest month was **{peak['month']}** with {peak['visits']} visits.\n",
        md_table(dept), "![Visits by department](visits_by_department.png)\n",
        "\n### Monthly trend\n", md_table(monthly), "![Monthly trends](monthly_visit_trends.png)\n",
        "\n## 4. Measurement summaries and trends\n", md_table(meas_summary),
        "![Measurement trends](measurement_trends.png)\n",
        "![Measurement distributions](measurement_distributions.png)\n",
        "\n## 5. Illustrative rule-based indicators\n",
        "Rules (arbitrary sample thresholds, **not** clinical criteria):\n",
        md_table(__import__("pandas").DataFrame(describe_rules())),
        f"\nPatients evaluated: {ind['patients_evaluated']}. "
        f"Distribution of `{COMPOSITE_CODE}` (number of rules fired):\n",
        md_table(__import__("pandas").DataFrame(dist)),
        "![Indicator summary](indicator_summary.png)\n",
        "\nThese are counts and distributions only. No clinical validity is claimed.\n",
        "\n## 6. Limitations\n", "\n".join(f"{i}. {t}" for i, t in enumerate(LIMITATIONS, 1)) + "\n",
    ]
    (OUT / "operational_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("Report written to reports/operational_report.md (plus 5 PNG charts)")


if __name__ == "__main__":
    main()
