"""GitHub PR 연결 순수 로직 단위 테스트 (네트워크 불필요).

서버는 연결에 `repo_link_id`, 해제에 `pr_id`(PR 행 id)를 요구하는데 사용자는 둘 다
모른다. 이름("owner/repo")·PR 번호를 내부 id로 옮기는 이 해석 단계가 틀리면
**엉뚱한 레포에 PR을 붙이거나 남의 PR 연결을 끊는다** — 여기서 가드한다.
"""

import pytest

from gdc_mcp import server

# GET /api/integrations/github/repo-links/?project={id} 응답 모양
ACTIVE = {
    "id": 11,
    "full_name": "gemiso/gdc-service",
    "sync_enabled": True,
    "installation_active": True,
    "detached_at": None,
}
OTHER = {
    "id": 12,
    "full_name": "gemiso/gdc-web",
    "sync_enabled": True,
    "installation_active": True,
    "detached_at": None,
}
DETACHED = {**ACTIVE, "id": 13, "full_name": "gemiso/old", "detached_at": "2026-08-01T00:00:00Z"}
PAUSED = {**ACTIVE, "id": 14, "full_name": "gemiso/paused", "sync_enabled": False}
INACTIVE_APP = {**ACTIVE, "id": 15, "full_name": "gemiso/dead", "installation_active": False}


def test_pick_repo_link_단일이면_생략해도_자동선택():
    assert server._pick_repo_link([ACTIVE], None)["id"] == 11


def test_pick_repo_link_이름으로_선택():
    assert server._pick_repo_link([ACTIVE, OTHER], "gemiso/gdc-web")["id"] == 12


def test_pick_repo_link_대소문자_무시():
    assert server._pick_repo_link([ACTIVE, OTHER], "GEMISO/GDC-Web")["id"] == 12


def test_pick_repo_link_여러개인데_미지정이면_오류():
    with pytest.raises(ValueError) as e:
        server._pick_repo_link([ACTIVE, OTHER], None)
    assert "gemiso/gdc-web" in str(e.value)  # 후보를 안내한다


def test_pick_repo_link_없는_이름이면_후보_안내():
    with pytest.raises(ValueError) as e:
        server._pick_repo_link([ACTIVE], "gemiso/nope")
    assert "gemiso/gdc-service" in str(e.value)


@pytest.mark.parametrize("link", [DETACHED, PAUSED, INACTIVE_APP])
def test_pick_repo_link_쓸수없는_연결은_제외(link):
    """해제·일시중지·설치 비활성 연결에 붙이면 상태 갱신이 안 와 영원히 낡는다."""
    with pytest.raises(ValueError):
        server._pick_repo_link([link], None)
    # 살아 있는 연결과 섞여 있으면 자동 선택은 살아 있는 쪽이어야 한다
    assert server._pick_repo_link([ACTIVE, link], None)["id"] == 11


# 태스크 상세 github_pull_requests[] → _pr_summary 통과 후 모양
PR_A = {"id": 101, "number": 7, "repo_full_name": "gemiso/gdc-service", "source": "manual"}
PR_B = {"id": 102, "number": 7, "repo_full_name": "gemiso/gdc-web", "source": "auto"}
PR_C = {"id": 103, "number": 9, "repo_full_name": "gemiso/gdc-service", "source": "auto_issue"}


def test_find_linked_pr_번호로_매칭():
    assert server._find_linked_pr([PR_A, PR_C], 9, None)["id"] == 103


def test_find_linked_pr_같은_번호가_여러_레포면_오류():
    with pytest.raises(ValueError) as e:
        server._find_linked_pr([PR_A, PR_B], 7, None)
    assert "repo" in str(e.value)


def test_find_linked_pr_레포_지정으로_해소():
    assert server._find_linked_pr([PR_A, PR_B], 7, "gemiso/gdc-web")["id"] == 102


def test_find_linked_pr_연결되지_않은_번호면_오류():
    with pytest.raises(ValueError) as e:
        server._find_linked_pr([PR_A], 99, None)
    assert "#99" in str(e.value)


def test_find_linked_pr_연결이_없으면_오류():
    with pytest.raises(ValueError):
        server._find_linked_pr([], 7, None)


def test_pr_summary_서버_필드명을_유지한다():
    row = {
        "id": 101, "number": 7, "title": "fix: …", "url": "https://github.com/x/y/pull/7",
        "repo_full_name": "gemiso/gdc-service", "state": "merged",
        "merged_at": "2026-08-27T10:00:00Z", "base_branch": "develop", "source": "manual",
    }
    assert server._pr_summary(row) == row


def test_pr_summary_누락_필드는_None():
    assert server._pr_summary({"id": 1})["state"] is None


@pytest.mark.parametrize("source,expected", [("auto", True), ("auto_issue", True), ("manual", False)])
def test_자동연결_해제_안내문구는_source별로_갈린다(source, expected):
    assert (source in server._AUTO_UNLINK_NOTE) is expected
