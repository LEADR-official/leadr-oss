"""Verification service for generating and validating email verification codes."""

import random
from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.common.domain.ids import UserID
from leadr.config import settings
from leadr.infra.email import EmailService
from leadr.registration.domain.verification_code import VerificationCode, VerificationCodeType
from leadr.registration.services.repositories import VerificationCodeRepository


class VerificationService:
    """Service for managing email verification codes."""

    def __init__(self, db: AsyncSession, email_service: EmailService):
        """Initialize the verification service.

        Args:
            db: Database session.
            email_service: Email service for sending verification codes.
        """
        self.db = db
        self.email_service = email_service
        self.repository = VerificationCodeRepository(db)

    async def initiate_verification(self, email: str) -> None:
        """Generate and send a verification code to an email address.

        Invalidates any existing pending codes for the email before creating a new one.

        Args:
            email: Email address to send the verification code to.
        """
        # Invalidate existing pending codes
        await self.repository.invalidate_codes_for_email(email)

        # Generate new verification code
        code = self._generate_code()
        expires_at = datetime.now(UTC) + timedelta(
            seconds=settings.VERIFICATION_CODE_EXPIRY_SECONDS
        )

        # Create verification code entity
        verification_code = VerificationCode(
            email=email,
            code=code,
            expires_at=expires_at,
        )

        # Save to database
        await self.repository.create(verification_code)
        await self.db.commit()

        # Send verification email
        await self.email_service.send_verification_code(email, code)

    async def create_invite_code(self, email: str, user_id: UserID) -> VerificationCode:
        """Create an invite verification code for an existing user.

        Invalidates any existing pending invite codes for the email before creating a new one.

        Args:
            email: Email address to send the invite code to.
            user_id: The ID of the user being invited.

        Returns:
            The created verification code entity.
        """
        # Invalidate existing pending codes for this email
        await self.repository.invalidate_codes_for_email(email)

        # Generate new verification code with 24-hour expiry
        code = self._generate_code()
        expires_at = datetime.now(UTC) + timedelta(seconds=settings.INVITE_CODE_EXPIRY_SECONDS)

        # Create invite verification code entity
        verification_code = VerificationCode(
            email=email,
            code=code,
            code_type=VerificationCodeType.INVITE,
            user_id=user_id,
            expires_at=expires_at,
        )

        # Save to database
        await self.repository.create(verification_code)
        await self.db.commit()

        return verification_code

    async def verify_code(self, email: str, code: str) -> tuple[str, VerificationCodeType]:
        """Verify a code and return a short-lived verification token with its type.

        Args:
            email: Email address to verify.
            code: Verification code to check.

        Returns:
            A tuple of (JWT verification token, VerificationCodeType).
            For invite codes, the token includes user_id.

        Raises:
            ValueError: If the code is invalid, expired, or already used.
        """
        # Find the verification code
        verification_code = await self.repository.find_valid_code_by_email(email, code)

        if not verification_code:
            raise ValueError("Invalid or expired verification code")

        # Check if code is expired
        if verification_code.is_expired():
            raise ValueError("Verification code has expired")

        # Check if code is already used
        if verification_code.is_used():
            raise ValueError("Verification code has already been used")

        # Mark code as used
        verification_code.mark_as_used()
        await self.repository.update(verification_code)
        await self.db.commit()

        # Generate verification token with appropriate type
        if verification_code.is_invite:
            token = self._generate_verification_token(
                email,
                verification_type="invite",
                user_id=verification_code.user_id,
            )
            return token, VerificationCodeType.INVITE
        else:
            token = self._generate_verification_token(email, verification_type="registration")
            return token, VerificationCodeType.REGISTRATION

    def validate_verification_token(self, token: str) -> str:
        """Validate a verification token and return the email.

        Args:
            token: JWT verification token.

        Returns:
            The email address from the token.

        Raises:
            ValueError: If the token is invalid or expired.
        """
        try:
            payload = jwt.decode(
                token,
                settings.API_KEY_SECRET,
                algorithms=["HS256"],
            )

            # Accept both registration and invite token types
            token_type = payload.get("type")
            if token_type not in ("registration", "invite"):
                raise ValueError("Invalid token type")

            email = payload.get("email")
            if not email:
                raise ValueError("Missing email in token")

            return email

        except jwt.ExpiredSignatureError as e:
            raise ValueError("Verification token has expired") from e
        except jwt.InvalidTokenError as e:
            raise ValueError("Invalid verification token") from e

    def get_invite_user_id(self, token: str) -> UserID | None:
        """Extract the user_id from an invite verification token.

        Args:
            token: JWT verification token.

        Returns:
            The UserID if this is an invite token, None otherwise.

        Raises:
            ValueError: If the token is invalid or expired.
        """
        try:
            payload = jwt.decode(
                token,
                settings.API_KEY_SECRET,
                algorithms=["HS256"],
            )

            if payload.get("type") != "invite":
                return None

            user_id_str = payload.get("user_id")
            if not user_id_str:
                return None

            from uuid import UUID

            return UserID(UUID(user_id_str))

        except jwt.ExpiredSignatureError as e:
            raise ValueError("Verification token has expired") from e
        except jwt.InvalidTokenError as e:
            raise ValueError("Invalid verification token") from e

    def _generate_code(self) -> str:
        """Generate a random 6-character alphanumeric verification code.

        Returns:
            A 6-character uppercase alphanumeric code.
        """
        # Use uppercase letters and digits (no confusing characters like O, 0, I, 1)
        characters = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        return "".join(random.choice(characters) for _ in range(6))  # noqa: S311

    def _generate_verification_token(
        self,
        email: str,
        verification_type: str = "registration",
        user_id: UserID | None = None,
    ) -> str:
        """Generate a short-lived JWT verification token.

        Args:
            email: Email address to include in the token.
            verification_type: Type of token ("registration" or "invite").
            user_id: Optional user ID for invite tokens.

        Returns:
            A JWT token valid for the configured duration.
        """
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=settings.VERIFICATION_TOKEN_EXPIRY_SECONDS)

        payload: dict[str, str | float] = {
            "email": email,
            "type": verification_type,
            "iat": now.timestamp(),
            "exp": expires_at.timestamp(),
        }

        # Include user_id for invite tokens
        if user_id is not None:
            payload["user_id"] = str(user_id.uuid)

        token = jwt.encode(payload, settings.API_KEY_SECRET, algorithm="HS256")
        return token
