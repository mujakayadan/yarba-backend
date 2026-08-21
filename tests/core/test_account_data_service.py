"""Account export and cancellable deletion lifecycle tests."""

from io import BytesIO
from zipfile import ZipFile

import pytest

from core.models.data_rights import DeletionStatus, ExportStatus
from core.models.user import User
from core.services.account_data_service import AccountDataService


class MemoryStorage:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    async def save_account_export(self, archive: bytes, request_id: str) -> str:
        key = f"account-exports/{request_id}.zip"
        self.files[key] = archive
        return key

    async def get_file(self, object_key: str) -> bytes:
        return self.files[object_key]

    async def delete_file(self, object_key: str) -> bool:
        return self.files.pop(object_key, None) is not None


@pytest.mark.asyncio
async def test_account_export_is_ready_and_downloadable(
    test_user: User,
) -> None:
    storage = MemoryStorage()
    service = AccountDataService(storage=storage)  # type: ignore[arg-type]

    export = await service.request_export(test_user)
    download_url = service.download_url(export, "https://api.yarba.app/api/v1")
    token = download_url.split("token=", 1)[1] if download_url else ""
    archive, filename = await service.get_download(str(export.id), token)

    assert export.status == ExportStatus.READY
    assert filename.startswith("yarba-export-")
    with ZipFile(BytesIO(archive)) as bundle:
        assert "account.json" in bundle.namelist()
        assert b"password_hash" not in bundle.read("account.json")


@pytest.mark.asyncio
async def test_account_deletion_can_be_cancelled_during_grace_period(
    test_user: User,
) -> None:
    service = AccountDataService(storage=MemoryStorage())  # type: ignore[arg-type]

    deletion = await service.request_deletion(test_user, current_password=None)
    persisted_user = await User.get(test_user.id)

    assert deletion.status == DeletionStatus.PENDING
    assert persisted_user is not None
    assert persisted_user.is_active is False

    cancelled = await service.cancel_deletion(persisted_user)
    reactivated_user = await User.get(test_user.id)

    assert cancelled.status == DeletionStatus.CANCELLED
    assert reactivated_user is not None
    assert reactivated_user.is_active is True
