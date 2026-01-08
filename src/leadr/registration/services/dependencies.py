"""Dependency injection for registration services."""

from typing import Annotated

from fastapi import Depends

from leadr.accounts.services.dependencies import AccountServiceDep, UserServiceDep
from leadr.auth.services.dependencies import APIKeyServiceDep
from leadr.common.dependencies import DatabaseSession
from leadr.infra.email import EmailService, create_email_service
from leadr.registration.services.invite_service import InviteService
from leadr.registration.services.jam_code_service import JamCodeService
from leadr.registration.services.registration_service import RegistrationService
from leadr.registration.services.verification_service import VerificationService


async def get_email_service(db: DatabaseSession) -> EmailService:
    """Get EmailService dependency.

    Args:
        db: Database session.

    Returns:
        EmailService instance.
    """
    return create_email_service(db=db)


EmailServiceDep = Annotated[EmailService, Depends(get_email_service)]


async def get_verification_service(
    db: DatabaseSession,
    email_service: EmailServiceDep,
) -> VerificationService:
    """Get VerificationService dependency.

    Args:
        db: Database session.
        email_service: Email service.

    Returns:
        VerificationService instance.
    """
    return VerificationService(db, email_service)


VerificationServiceDep = Annotated[VerificationService, Depends(get_verification_service)]


async def get_jam_code_service(db: DatabaseSession) -> JamCodeService:
    """Get JamCodeService dependency.

    Args:
        db: Database session.

    Returns:
        JamCodeService instance.
    """
    return JamCodeService(db)


JamCodeServiceDep = Annotated[JamCodeService, Depends(get_jam_code_service)]


async def get_registration_service(
    db: DatabaseSession,
    account_service: AccountServiceDep,
    user_service: UserServiceDep,
    api_key_service: APIKeyServiceDep,
    verification_service: VerificationServiceDep,
    jam_code_service: JamCodeServiceDep,
    email_service: EmailServiceDep,
) -> RegistrationService:
    """Get RegistrationService dependency.

    Args:
        db: Database session.
        account_service: Account service.
        user_service: User service.
        api_key_service: API key service.
        verification_service: Verification service.
        jam_code_service: Jam code service.
        email_service: Email service.

    Returns:
        RegistrationService instance.
    """
    return RegistrationService(
        db,
        account_service,
        user_service,
        api_key_service,
        verification_service,
        jam_code_service,
        email_service,
    )


RegistrationServiceDep = Annotated[RegistrationService, Depends(get_registration_service)]


async def get_invite_service(
    db: DatabaseSession,
    account_service: AccountServiceDep,
    user_service: UserServiceDep,
    verification_service: VerificationServiceDep,
    email_service: EmailServiceDep,
) -> InviteService:
    """Get InviteService dependency.

    Args:
        db: Database session.
        account_service: Account service.
        user_service: User service.
        verification_service: Verification service.
        email_service: Email service.

    Returns:
        InviteService instance.
    """
    return InviteService(
        db,
        account_service,
        user_service,
        verification_service,
        email_service,
    )


InviteServiceDep = Annotated[InviteService, Depends(get_invite_service)]
