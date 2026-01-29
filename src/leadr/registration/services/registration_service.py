"""Registration service for orchestrating account creation and invite completion flows."""

import random
import string

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account
from leadr.accounts.domain.user import User, UserStatus
from leadr.accounts.services.account_service import AccountService
from leadr.accounts.services.user_service import UserService
from leadr.auth.services.api_key_service import APIKeyService
from leadr.common.domain.ids import AccountID, UserID
from leadr.common.utils.slug import generate_slug
from leadr.infra.email import EmailService
from leadr.registration.services.jam_code_service import JamCodeService
from leadr.registration.services.verification_service import VerificationService


class RegistrationService:
    """Service for orchestrating registration and invite completion flows.

    Handles two distinct flows:
    - Registration: Creates new account, user (as owner), and API key
    - Invite: Activates existing invited user and creates API key
    """

    def __init__(
        self,
        db: AsyncSession,
        account_service: AccountService,
        user_service: UserService,
        api_key_service: APIKeyService,
        verification_service: VerificationService,
        jam_code_service: JamCodeService,
        email_service: EmailService,
    ):
        """Initialize the registration service.

        Args:
            db: Database session.
            account_service: Service for account operations.
            user_service: Service for user operations.
            api_key_service: Service for API key operations.
            verification_service: Service for email verification.
            jam_code_service: Service for jam code validation.
            email_service: Service for sending emails.
        """
        self.db = db
        self.account_service = account_service
        self.user_service = user_service
        self.api_key_service = api_key_service
        self.verification_service = verification_service
        self.jam_code_service = jam_code_service
        self.email_service = email_service

    async def complete_registration(
        self,
        verification_token: str,
        account_name: str | None = None,
        account_slug: str | None = None,
        jam_code: str | None = None,
        display_name: str | None = None,
    ) -> tuple[Account, User, str]:
        """Complete the registration process and create account, user, and API key.

        For invite flow: If the verification token contains a user_id, this is an
        invite completion. The existing invited user is activated and an API key
        is created. Account creation is skipped.

        For registration flow: A new account, user, and API key are created.

        Args:
            verification_token: JWT token from email verification.
            account_name: Name for the new account (required for registration, ignored for invite).
            account_slug: Optional slug (will be auto-generated if not provided).
            jam_code: Optional jam code for promotional features (registration only).
            display_name: Optional display name (will use email prefix if not provided).

        Returns:
            Tuple of (Account, User, plain_api_key).

        Raises:
            ValueError: If verification token is invalid or jam code is invalid.
            ValueError: If account_name is missing for registration flow.
        """
        # Validate verification token and get email
        email = self.verification_service.validate_verification_token(verification_token)

        # Check if this is an invite flow
        invite_user_id = self.verification_service.get_invite_user_id(verification_token)

        if invite_user_id:
            # INVITE FLOW: Activate existing invited user
            return await self._complete_invite_registration(
                user_id=invite_user_id,
                display_name=display_name,
            )
        else:
            # REGISTRATION FLOW: Create new account and user
            if not account_name:
                raise ValueError("Account name is required for registration")

            return await self._complete_new_registration(
                email=email,
                account_name=account_name,
                account_slug=account_slug,
                jam_code=jam_code,
                display_name=display_name,
            )

    async def _complete_invite_registration(
        self,
        user_id: UserID,
        display_name: str | None = None,
    ) -> tuple[Account, User, str]:
        """Complete registration for an invited user.

        Args:
            user_id: ID of the invited user.
            display_name: Optional new display name for the user.

        Returns:
            Tuple of (Account, User, plain_api_key).

        Raises:
            ValueError: If user not found or not in INVITED status.
        """
        # Get the invited user
        user = await self.user_service.get_by_id_or_raise(user_id)

        if user.status != UserStatus.INVITED:
            raise ValueError("User is not in invited status")

        # Update display name if provided
        if display_name and display_name.strip():
            user.display_name = display_name

        # Activate the user
        user.activate()
        user = await self.user_service.repository.update(user)

        # Get the account
        account = await self.account_service.get_by_id_or_raise(AccountID(user.account_id.uuid))

        # Create API key for the user
        api_key, plain_api_key = await self.api_key_service.create_api_key(
            account_id=account.id,
            user_id=user.id,
            name=f"{user.display_name}'s Key",
        )

        await self.db.commit()

        # Send welcome email
        try:
            await self.email_service.send_welcome_email(
                to=user.email,
                user_name=user.display_name,
                account_name=account.name,
                account_slug=account.slug,
            )
        except Exception:  # noqa: S110
            pass

        return account, user, plain_api_key

    async def _complete_new_registration(
        self,
        email: str,
        account_name: str,
        account_slug: str | None = None,
        jam_code: str | None = None,
        display_name: str | None = None,
    ) -> tuple[Account, User, str]:
        """Complete registration for a new account.

        Args:
            email: Verified email address.
            account_name: Name for the new account.
            account_slug: Optional slug (will be auto-generated if not provided).
            jam_code: Optional jam code for promotional features.
            display_name: Optional display name (will use email prefix if not provided).

        Returns:
            Tuple of (Account, User, plain_api_key).

        Raises:
            ValueError: If jam code is invalid.
        """
        # Generate slug if not provided
        if not account_slug:
            account_slug = await self._generate_unique_slug(account_name)

        # Validate and redeem jam code if provided
        jam_code_entity = None
        jam_code_meta = {}
        if jam_code:
            jam_code_entity = await self.jam_code_service.validate_and_get_jam_code(jam_code)
            if not jam_code_entity:
                raise ValueError("Invalid or expired jam code")
            jam_code_meta = jam_code_entity.features

        # Create account
        account = await self.account_service.create_account(
            name=account_name,
            slug=account_slug,
        )

        # Determine display name: use provided or fall back to email prefix
        # Treat None, empty string, or whitespace-only as "not provided"
        user_display_name = (
            display_name if display_name and display_name.strip() else email.split("@")[0]
        )

        # Create user as account owner
        user = await self.user_service.create_user(
            account_id=account.id,
            email=email,
            display_name=user_display_name,
            is_owner=True,
        )

        # Create API key
        api_key, plain_api_key = await self.api_key_service.create_api_key(
            account_id=account.id,
            user_id=user.id,
            name="CLI API Key",
        )

        # Redeem jam code if provided
        if jam_code_entity:
            await self.jam_code_service.redeem_jam_code(
                jam_code=jam_code_entity,
                account_id=account.id,
                meta=jam_code_meta,
            )

        # Send welcome email (don't block on this)
        try:
            await self.email_service.send_welcome_email(
                to=email,
                user_name=user.display_name,
                account_name=account_name,
                account_slug=account_slug,
            )
        except Exception:  # noqa: S110
            # Log error but don't fail registration if email fails
            pass

        return account, user, plain_api_key

    async def _generate_unique_slug(self, account_name: str) -> str:
        """Generate a unique slug for an account.

        Args:
            account_name: Account name to base the slug on.

        Returns:
            A unique slug.
        """
        base_slug = generate_slug(account_name)
        slug = base_slug
        counter = 1

        # Keep trying until we find a unique slug
        while True:
            existing = await self.account_service.get_account_by_slug(slug)
            if not existing:
                return slug

            # Append counter and try again
            slug = f"{base_slug}-{counter}"
            counter += 1

            # Safety check to prevent infinite loop
            if counter > 1000:
                # Add random suffix
                random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))  # noqa: S311
                return f"{base_slug}-{random_suffix}"
