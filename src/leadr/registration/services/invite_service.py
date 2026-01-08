"""Invite service for managing user invitations to accounts."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.user import User, UserStatus
from leadr.accounts.services.account_service import AccountService
from leadr.accounts.services.user_service import UserService
from leadr.common.domain.ids import AccountID
from leadr.infra.email import EmailService
from leadr.registration.services.verification_service import VerificationService

logger = logging.getLogger(__name__)


class InviteService:
    """Service for managing user invitations.

    Coordinates the invite flow:
    1. Create invited user with INVITED status
    2. Create invite verification code
    3. Send invite email
    """

    def __init__(
        self,
        db: AsyncSession,
        account_service: AccountService,
        user_service: UserService,
        verification_service: VerificationService,
        email_service: EmailService,
    ):
        """Initialize the invite service.

        Args:
            db: Database session.
            account_service: Account service for fetching account info.
            user_service: User service for creating users.
            verification_service: Verification service for creating invite codes.
            email_service: Email service for sending invite emails.
        """
        self.db = db
        self.account_service = account_service
        self.user_service = user_service
        self.verification_service = verification_service
        self.email_service = email_service

    async def send_invite(
        self,
        email: str,
        account_id: AccountID,
        display_name: str | None = None,
    ) -> User:
        """Invite a user to an account.

        Creates a user with INVITED status and sends an invite email with
        a verification code. If the user already exists with INVITED status,
        resends the invite (invalidates old code, creates new one).

        Args:
            email: Email address to invite.
            account_id: The account ID to invite the user to.
            display_name: Optional display name. Defaults to email prefix if not provided.

        Returns:
            The created or existing User entity with INVITED status.

        Raises:
            ValueError: If user already exists with non-INVITED status.
            ValueError: If account doesn't exist.
        """
        # Get account to verify it exists and for email template
        account = await self.account_service.get_by_id_or_raise(account_id)

        # Check if user already exists
        existing_user = await self.user_service.get_user_by_email(email)

        if existing_user:
            if existing_user.status != UserStatus.INVITED:
                raise ValueError(f"User with email {email} already exists and is active")

            # Resend invite for existing invited user
            user = existing_user
            logger.info("Resending invite to existing invited user: %s", email)
        else:
            # Create new user with INVITED status
            if display_name is None or not display_name.strip():
                display_name = email.split("@")[0]

            user = User(
                account_id=account_id,
                email=email,
                display_name=display_name,
                status=UserStatus.INVITED,
            )
            user = await self.user_service.repository.create(user)
            await self.db.commit()
            logger.info("Created invited user: %s", email)

        # Create invite verification code (invalidates old codes)
        verification_code = await self.verification_service.create_invite_code(
            email=email,
            user_id=user.id,
        )

        # Send invite email (don't fail if email fails)
        try:
            await self.email_service.send_invite_email(
                to=email,
                account_name=account.name,
                code=verification_code.code,
            )
            logger.info("Sent invite email to: %s", email)
        except Exception as e:
            logger.warning("Failed to send invite email to %s: %s", email, e)
            # Don't fail the invite if email sending fails
            # The user can request a resend

        return user
