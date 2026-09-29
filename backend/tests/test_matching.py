from datetime import datetime, timedelta

from app.matching import is_coding_role, rank, rejection
from app.models import Job, Profile
from app.sources.base import annual_usd
from app.sources.remotive import usd_from_text

NOW = datetime(2026, 9, 29)


def job(title, description="", remote=True, locations=None, employment_type="Full-time", salary=0, days_old=3):
    return Job(
        source="test", external_id=title, url="", apply_url="", title=title, company="Acme",
        locations=locations or [], remote=remote, employment_type=employment_type, description=description,
        posted_at=NOW - timedelta(days=days_old), salary_text="", salary_max_usd=salary,
    )


def profile(**overrides):
    values = dict(
        titles=["Business Analyst", "QA Engineer"], skills=["UAT", "SQL", "JIRA", "LLM Evaluation"],
        extra_keywords=[], exclude_keywords=["contract", "intern"], preferred_locations=["India"],
        remote_only=False, min_salary=0, prefer_non_coding=False,
    )
    values.update(overrides)
    return Profile(**values)


def test_ranks_skill_and_title_overlap_first():
    strong = job("Business Analyst", "UAT, SQL and JIRA daily; LLM evaluation a plus")
    weak = job("Marketing Manager", "brand campaigns")
    ranked = rank([weak, strong], profile(), NOW)
    assert [m.job.title for m in ranked] == ["Business Analyst"]
    assert "UAT" in ranked[0].reason


def test_irrelevant_well_paid_job_is_dropped():
    radiologist = job("Remote Overnight Neuroradiologist", "healthcare documentation", salary=500_000)
    generic = job("Principal Engineer", "SQL")
    assert rank([radiologist, generic], profile(), NOW) == []


def test_excluded_keywords_drop_contract_and_intern_roles():
    assert rejection(job("QA Intern"), profile()) == "excluded keyword: intern"
    assert rejection(job("QA Analyst", employment_type="Contract"), profile()) == "excluded keyword: contract"
    assert rejection(job("QA Analyst"), profile()) is None


def test_remote_role_restricted_to_other_country_is_rejected():
    us_only = job("QA Analyst", locations=["United States"])
    anywhere = job("QA Analyst", locations=[])
    worldwide = job("QA Analyst", locations=["Worldwide"])
    india = job("QA Analyst", locations=["Remote, India"])
    assert rejection(us_only, profile()) == "location"
    assert rejection(anywhere, profile()) is None
    assert rejection(worldwide, profile()) is None
    assert rejection(india, profile()) is None


def test_remote_only_and_salary_floor():
    office = job("QA Analyst", remote=False, locations=["Chennai, India"])
    assert rejection(office, profile(remote_only=True)) == "not remote"
    assert rejection(job("QA Analyst", salary=12_000), profile(min_salary=15_000)) == "salary below minimum"
    # Unknown pay is not held against a posting.
    assert rejection(job("QA Analyst", salary=0), profile(min_salary=15_000)) is None


def test_non_coding_preference_reorders_roles():
    coder = job("QA Software Engineer", "SQL JIRA UAT")
    analyst = job("QA Analyst", "SQL JIRA UAT")
    neutral = {m.job.title: m.score for m in rank([coder, analyst], profile(), NOW)}
    preferred = rank([coder, analyst], profile(prefer_non_coding=True), NOW)
    by_title = {m.job.title: m.score for m in preferred}
    assert preferred[0].job.title == "QA Analyst"
    neutral_gap = neutral["QA Analyst"] - neutral["QA Software Engineer"]
    assert by_title["QA Analyst"] - by_title["QA Software Engineer"] == neutral_gap + 25
    assert "non-coding role" in preferred[0].reason


def test_is_coding_role():
    assert is_coding_role("Senior Python Developer")
    assert is_coding_role("SDET - QA Automation")
    assert not is_coding_role("QA Analyst (Banking)")
    assert not is_coding_role("LLM Evaluation Specialist")


def test_salary_normalisation():
    assert annual_usd(50, "USD", "hour") == 104_000
    assert annual_usd(1_300_000, "INR", "year") == round(1_300_000 / 83)
    assert annual_usd(100, "XYZ", "year") == 0
    assert usd_from_text("$60k - $80k") == 80_000
    assert usd_from_text("INR 12,00,000") == 0


def test_strong_currency_country_ranks_higher():
    home = job("QA Analyst", "SQL JIRA UAT", locations=["India"])
    gulf = job("QA Analyst ", "SQL JIRA UAT", locations=["Kuwait City, Kuwait"])
    ranked = rank([home, gulf], profile(preferred_locations=["India", "Kuwait"]), NOW)
    assert ranked[0].job.locations == ["Kuwait City, Kuwait"]
    assert "strong-currency country" in ranked[0].reason
    assert annual_usd(1000, "KWD", "month") == round(1000 * 3.24 * 12)


def test_india_only_roles_come_last_even_with_higher_score():
    india = job("Business Analyst", "UAT SQL JIRA LLM evaluation", locations=["Bengaluru, India"])
    anywhere = job("QA Analyst", "SQL", locations=[])
    uk = job("QA Analyst", "SQL", locations=["London, United Kingdom"])
    same_family = profile(titles=["Analyst"], preferred_locations=["India", "United Kingdom"])
    ranked = rank([india, anywhere, uk], same_family, NOW)
    assert [m.job.locations for m in ranked] == [["London, United Kingdom"], [], ["Bengaluru, India"]]


def test_title_order_in_profile_sets_role_priority():
    analyst = job("Business Analyst", "UAT SQL JIRA LLM evaluation")
    qa = job("QA Engineer", "SQL")
    ranked = rank([analyst, qa], profile(titles=["QA", "Business Analyst"]), NOW)
    assert [m.job.title for m in ranked] == ["QA Engineer", "Business Analyst"]


def test_selenium_java_automation_is_not_pushed_down_as_coding():
    automation = job("QA Automation Engineer", "Selenium with Java, TestNG, SQL, JIRA, UAT")
    developer = job("QA Software Engineer", "Go microservices, SQL, JIRA, UAT")
    ranked = rank([developer, automation], profile(titles=["QA"], prefer_non_coding=True), NOW)
    assert ranked[0].job.title == "QA Automation Engineer"
    assert not ranked[0].coding and ranked[1].coding
