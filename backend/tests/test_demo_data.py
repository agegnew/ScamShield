from app.db import Base, engine, init_db
from app.demo_data import load_snapshot
from app.mock.data import build_cases
from app.repo import CaseRepo
from scripts import seed_demo


def test_snapshot_round_trip_rescores_and_skips_known_urls(session, tmp_path):
    repo = CaseRepo(session)
    repo.seed(build_cases())
    with_evidence = {c.candidate.url for c in repo.all() if c.evidence is not None}
    assert seed_demo.main(["export", str(tmp_path)]) == 0
    assert (tmp_path / "cases.json").exists()

    session.close()
    Base.metadata.drop_all(engine)
    init_db()
    assert load_snapshot(tmp_path) == len(with_evidence)
    assert load_snapshot(tmp_path) == 0  # loading twice adds nothing
    loaded = CaseRepo(session).all()
    assert {c.candidate.url for c in loaded} == with_evidence
    assert all(c.verdict.model_version.startswith("engine-1") for c in loaded)  # scored by the engine


def test_read_urls_with_sources_and_comments(tmp_path):
    path = tmp_path / "urls.txt"
    path.write_text("# demo\nhttps://moi-portal.com/  lookalike  # fake MOI\nhttps://www.tamm.abudhabi/\n\n", encoding="utf-8")
    assert [(u, s.value) for u, s in seed_demo.read_urls(path)] == [
        ("https://moi-portal.com/", "lookalike"),
        ("https://www.tamm.abudhabi/", "manual"),
    ]
