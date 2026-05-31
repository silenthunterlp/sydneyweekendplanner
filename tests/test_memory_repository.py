import pytest


@pytest.mark.asyncio
async def test_get_or_create_new_user(repo):
    prefs = await repo.get_or_create("web:alice", "web")
    assert prefs.user_id == "web:alice"
    assert prefs.channel == "web"
    assert prefs.onboarding_complete is False


@pytest.mark.asyncio
async def test_get_or_create_idempotent(repo):
    p1 = await repo.get_or_create("web:bob", "web")
    p2 = await repo.get_or_create("web:bob", "web")
    assert p1.id == p2.id


@pytest.mark.asyncio
async def test_update_preferences(repo):
    await repo.get_or_create("web:carol", "web")
    updated = await repo.update("web:carol", {
        "home_suburb": "Newtown",
        "budget_per_day_aud": 75,
        "interests": ["arts", "food"],
        "onboarding_complete": True,
    })
    assert updated.home_suburb == "Newtown"
    assert updated.budget_per_day_aud == 75
    assert updated.interests == ["arts", "food"]
    assert updated.onboarding_complete is True


@pytest.mark.asyncio
async def test_history_append_and_retrieve(repo):
    await repo.get_or_create("web:dave", "web")
    await repo.append_history("web:dave", "user", "Plan my weekend")
    await repo.append_history("web:dave", "assistant", "Sure! Let me check the weather.")

    history = await repo.get_recent_history("web:dave", limit=10)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_channel_isolation(repo):
    """Users on different channels with same base ID are separate."""
    p_web = await repo.get_or_create("web:123", "web")
    p_tg = await repo.get_or_create("telegram:123", "telegram")
    assert p_web.id != p_tg.id
