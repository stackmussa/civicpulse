from app.core.database import _engine_kwargs


def test_engine_kwargs_excludes_pool_size_for_sqlite() -> None:
    kwargs = _engine_kwargs("sqlite+aiosqlite:///:memory:")
    assert kwargs["pool_pre_ping"] is True
    assert "pool_size" not in kwargs
    assert "max_overflow" not in kwargs


def test_engine_kwargs_includes_pool_settings_for_postgres() -> None:
    kwargs = _engine_kwargs("postgresql://localhost/db")
    assert kwargs["pool_size"] == 10
    assert kwargs["max_overflow"] == 20
