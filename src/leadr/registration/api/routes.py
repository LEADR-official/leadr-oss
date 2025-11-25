"""Public registration API routes."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from leadr.auth.dependencies import AdminAuthContextDep
from leadr.config import settings
from leadr.registration.api.schemas import (
    CompleteRegistrationRequest,
    CompleteRegistrationResponse,
    CreateJamCodeRequest,
    InitiateRegistrationRequest,
    InitiateRegistrationResponse,
    JamCodeResponse,
    UpdateJamCodeRequest,
    VerifyCodeRequest,
    VerifyCodeResponse,
)
from leadr.registration.services.dependencies import (
    JamCodeServiceDep,
    RegistrationServiceDep,
    VerificationServiceDep,
)

public_router = APIRouter(prefix="/register")
router = APIRouter()


# Public Registration Endpoints (No Authentication Required)


@public_router.post("/initiate", status_code=status.HTTP_201_CREATED)
async def initiate_registration(
    request: InitiateRegistrationRequest,
    verification_service: VerificationServiceDep,
) -> InitiateRegistrationResponse:
    """Initiate registration by sending a verification code to the provided email.

    This endpoint is publicly accessible and requires no authentication.
    A 6-character verification code will be sent to the email address.
    """
    try:
        await verification_service.initiate_verification(request.email)
    except Exception:  # noqa: S110
        # Log error but return success to prevent email enumeration
        # In production, log this properly
        pass

    return InitiateRegistrationResponse(
        message="Verification code sent to email",
        code_expires_in=settings.VERIFICATION_CODE_EXPIRY_SECONDS,
    )


@public_router.post("/verify", status_code=status.HTTP_200_OK)
async def verify_code(
    request: VerifyCodeRequest,
    verification_service: VerificationServiceDep,
) -> VerifyCodeResponse:
    """Verify an email verification code and return a temporary token.

    This endpoint validates the verification code and returns a short-lived
    token that can be used to complete the registration process.
    """
    try:
        verification_token = await verification_service.verify_code(request.email, request.code)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None

    return VerifyCodeResponse(
        verification_token=verification_token,
        expires_in=settings.VERIFICATION_TOKEN_EXPIRY_SECONDS,
    )


@public_router.post("/complete", status_code=status.HTTP_201_CREATED)
async def complete_registration(
    request: CompleteRegistrationRequest,
    registration_service: RegistrationServiceDep,
) -> CompleteRegistrationResponse:
    """Complete registration by creating the account, user, and API key.

    This endpoint creates the full account structure:
    - Account with the specified name and slug
    - User associated with the verified email
    - API key for CLI authentication
    - Optional jam code redemption

    The API key is returned in plaintext and should be stored securely by the client.
    """
    try:
        account, user, api_key = await registration_service.complete_registration(
            verification_token=request.verification_token,
            account_name=request.account_name,
            account_slug=request.account_slug,
            jam_code=request.jam_code,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None

    return CompleteRegistrationResponse(
        account_id=account.id.uuid,
        account_slug=account.slug,
        api_key=api_key,
    )


@public_router.post("/resend-code", status_code=status.HTTP_200_OK)
async def resend_verification_code(
    request: InitiateRegistrationRequest,
    verification_service: VerificationServiceDep,
) -> InitiateRegistrationResponse:
    """Resend a verification code to the provided email.

    This endpoint invalidates any existing codes for the email and sends a new one.
    """
    try:
        await verification_service.initiate_verification(request.email)
    except Exception:  # noqa: S110
        # Log error but return success to prevent email enumeration
        pass

    return InitiateRegistrationResponse(
        message="Verification code sent to email",
        code_expires_in=settings.VERIFICATION_CODE_EXPIRY_SECONDS,
    )


# Admin Jam Code Management Endpoints (Superadmin Only)


@router.post("/jam-codes", status_code=status.HTTP_201_CREATED)
async def create_jam_code(
    request: CreateJamCodeRequest,
    jam_code_service: JamCodeServiceDep,
    auth: AdminAuthContextDep,
) -> JamCodeResponse:
    """Create a new jam code (superadmin only).

    Jam codes can be used for promotional campaigns, game jams, or referral tracking.
    They can optionally have usage limits, expiration dates, and custom features.
    """
    if not auth.is_superadmin:
        raise HTTPException(status_code=403, detail="Superadmin access required")
    try:
        jam_code = await jam_code_service.create_jam_code(
            code=request.code,
            description=request.description,
            features=request.features,
            max_uses=request.max_uses,
            expires_at=request.expires_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None

    return JamCodeResponse.from_domain(jam_code)


@router.get("/jam-codes")
async def list_jam_codes(
    jam_code_service: JamCodeServiceDep,
    auth: AdminAuthContextDep,
) -> list[JamCodeResponse]:
    """List all jam codes (superadmin only).

    Returns a list of all jam codes, including their usage statistics.
    """
    if not auth.is_superadmin:
        raise HTTPException(status_code=403, detail="Superadmin access required")
    jam_codes = await jam_code_service.list_jam_codes()
    return [JamCodeResponse.from_domain(code) for code in jam_codes]


@router.get("/jam-codes/{jam_code_id}")
async def get_jam_code(
    jam_code_id: UUID,
    jam_code_service: JamCodeServiceDep,
    auth: AdminAuthContextDep,
) -> JamCodeResponse:
    """Get a specific jam code by ID (superadmin only)."""
    if not auth.is_superadmin:
        raise HTTPException(status_code=403, detail="Superadmin access required")
    jam_code = await jam_code_service.get_jam_code_by_id(jam_code_id)
    if not jam_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jam code not found",
        )

    return JamCodeResponse.from_domain(jam_code)


@router.patch("/jam-codes/{jam_code_id}")
async def update_jam_code(
    jam_code_id: UUID,
    request: UpdateJamCodeRequest,
    jam_code_service: JamCodeServiceDep,
    auth: AdminAuthContextDep,
) -> JamCodeResponse:
    """Update a jam code (superadmin only).

    Can update description, features, max uses, active status, and expiration.
    """
    if not auth.is_superadmin:
        raise HTTPException(status_code=403, detail="Superadmin access required")
    try:
        jam_code = await jam_code_service.update_jam_code(
            jam_code_id=jam_code_id,
            description=request.description,
            features=request.features,
            max_uses=request.max_uses,
            active=request.active,
            expires_at=request.expires_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from None

    return JamCodeResponse.from_domain(jam_code)
